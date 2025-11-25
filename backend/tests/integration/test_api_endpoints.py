"""
Integration tests for API endpoints

These tests verify that the FastAPI endpoints correctly integrate with
the underlying services (queue manager, extraction service, sheets client).

Note: These tests run against the actual services (Redis, etc.) so they
require the full environment to be running.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    """
    Create a test client for the FastAPI app

    The context manager ensures lifespan events are triggered,
    which initializes all the services.
    """
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoint:
    """Tests for the /api/health endpoint"""

    def test_health_check_success(self, client):
        """Test health check returns healthy status"""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        assert "stats" in data
        assert "pending_count" in data["stats"]


class TestPendingEndpoints:
    """Tests for pending queue endpoints"""

    def test_get_pending_returns_list(self, client):
        """Test GET /api/pending returns a list of records"""
        response = client.get("/api/pending")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_pending_count(self, client):
        """Test GET /api/pending/count returns count and has_new flag"""
        response = client.get("/api/pending/count")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "has_new" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["has_new"], bool)
        # has_new should be True when count > 0, False when count == 0
        assert data["has_new"] == (data["count"] > 0)

    def test_clear_pending_queue(self, client):
        """Test DELETE /api/pending/clear clears the queue"""
        response = client.delete("/api/pending/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "records_cleared" in data
        assert isinstance(data["records_cleared"], int)


class TestScanEndpoint:
    """Tests for the /api/scan endpoint"""

    def test_scan_returns_scan_result(self, client):
        """Test POST /api/scan returns scan result with counts"""
        # First clear to ensure clean state
        client.delete("/api/pending/clear")

        response = client.post("/api/scan")

        assert response.status_code == 200
        data = response.json()
        assert "processed_count" in data
        assert "new_items_count" in data
        assert "failed_count" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)
        assert isinstance(data["processed_count"], int)
        assert isinstance(data["new_items_count"], int)
        assert isinstance(data["failed_count"], int)


class TestRecordOperations:
    """Tests for record-specific operations (edit, approve, reject, source)"""

    def test_get_source_invalid_record_id(self, client):
        """Test GET /api/source/{record_id} returns 404 for invalid ID"""
        response = client.get("/api/source/invalid-id-12345")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_edit_record_invalid_id(self, client):
        """Test PATCH /api/edit/{record_id} returns 404 for invalid ID"""
        response = client.patch("/api/edit/invalid-id-12345", json={"client_name": "Updated Name"})

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_approve_record_invalid_id(self, client):
        """Test POST /api/approve/{record_id} returns 404 for invalid ID"""
        response = client.post("/api/approve/invalid-id-12345")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_reject_record_invalid_id(self, client):
        """Test POST /api/reject/{record_id} returns 404 for invalid ID"""
        response = client.post("/api/reject/invalid-id-12345")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestEndToEndWorkflow:
    """End-to-end workflow tests"""

    def test_complete_workflow(self, client):
        """
        Test complete workflow: clear → scan → get pending → edit → reject

        This test verifies the full user workflow without actually writing to Google Sheets.
        """
        # Step 1: Clear the queue
        response = client.delete("/api/pending/clear")
        assert response.status_code == 200

        # Step 2: Verify queue is empty
        response = client.get("/api/pending/count")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["has_new"] is False

        # Step 3: Scan for files
        response = client.post("/api/scan")
        assert response.status_code == 200
        scan_result = response.json()
        assert scan_result["new_items_count"] > 0

        # Step 4: Verify queue has items
        response = client.get("/api/pending/count")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] > 0
        assert data["has_new"] is True

        # Step 5: Get pending records
        response = client.get("/api/pending")
        assert response.status_code == 200
        records = response.json()
        assert len(records) > 0

        # Step 6: Get a record ID and test operations
        record_id = records[0]["id"]
        original_count = len(records)

        # Test get source
        response = client.get(f"/api/source/{record_id}")
        assert response.status_code == 200
        source_data = response.json()
        assert "content" in source_data
        assert "type" in source_data
        assert "filename" in source_data
        assert len(source_data["content"]) > 0

        # Test edit
        response = client.patch(f"/api/edit/{record_id}", json={"client_name": "Edited Name"})
        assert response.status_code == 200
        updated_record = response.json()
        assert updated_record["client_name"] == "Edited Name"
        assert updated_record["id"] == record_id

        # Test reject (don't test approve to avoid writing to Google Sheets)
        response = client.post(f"/api/reject/{record_id}")
        assert response.status_code == 200
        reject_result = response.json()
        assert reject_result["success"] is True

        # Verify record was removed
        response = client.get("/api/pending/count")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == original_count - 1


class TestErrorHandling:
    """Tests for error handling across endpoints"""

    def test_edit_with_invalid_json(self, client):
        """Test PATCH /api/edit with invalid JSON returns 422"""
        response = client.patch(
            "/api/edit/some-id",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Should return 422 for invalid JSON
        assert response.status_code == 422


class TestValidation:
    """Tests for request validation"""

    def test_pending_count_has_new_logic(self, client):
        """Test that has_new is correctly calculated based on count"""
        # Clear queue
        client.delete("/api/pending/clear")

        # Check has_new is False when empty
        response = client.get("/api/pending/count")
        assert response.status_code == 200
        data = response.json()
        if data["count"] == 0:
            assert data["has_new"] is False

        # Scan to add items
        client.post("/api/scan")

        # Check has_new is True when items exist
        response = client.get("/api/pending/count")
        assert response.status_code == 200
        data = response.json()
        if data["count"] > 0:
            assert data["has_new"] is True
