from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.api.routes.queue_manager")
def test_health_endpoint(mock_queue_manager):
    # Mock the queue manager health check
    mock_queue_manager.health_check = AsyncMock(return_value=True)
    mock_queue_manager.get_count = AsyncMock(return_value=0)

    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
