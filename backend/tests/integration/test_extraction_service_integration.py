"""
Integration tests for ExtractionService

These tests verify the complete extraction workflow including:
- File discovery
- Routing to appropriate parsers
- Confidence calculation
- Queue management
- Error handling
- Timeout handling
"""

from pathlib import Path
from unittest.mock import patch

import pytest
import redis.asyncio as redis

from app.models.extraction import RecordType
from app.pending_queue.manager import PendingQueueManager
from app.services.extraction import ExtractionService

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
async def redis_client():
    """Create a Redis client for testing"""
    client = redis.from_url("redis://redis:6379/1", decode_responses=True)
    yield client
    # Cleanup
    await client.flushdb()
    await client.aclose()


@pytest.fixture
async def queue_manager(redis_client):
    """Create a queue manager for testing"""
    manager = PendingQueueManager(redis_client)
    # Clear any existing data
    await manager.clear()
    await manager.clear_processed_files()
    return manager


@pytest.fixture
def extraction_service(queue_manager):
    """Create an extraction service for testing"""
    return ExtractionService(queue_manager)


class TestExtractionServiceFileDiscovery:
    """Tests for file discovery functionality"""

    @pytest.mark.asyncio
    async def test_discovers_unprocessed_files(self, extraction_service):
        """Test that service discovers unprocessed files"""
        files = await extraction_service._discover_files()

        # Should find files in all three directories
        assert len(files) > 0

        # Check that we have files from each directory
        forms = [f for f in files if "/forms/" in str(f)]
        emails = [f for f in files if "/emails/" in str(f)]
        invoices = [f for f in files if "/invoices/" in str(f)]

        assert len(forms) > 0, "Should find form files"
        assert len(emails) > 0, "Should find email files"
        assert len(invoices) > 0, "Should find invoice files"

    @pytest.mark.asyncio
    async def test_skips_processed_files(self, extraction_service, queue_manager):
        """Test that already processed files are skipped"""
        # Mark a file as processed
        test_file = Path("dummy_data/forms/contact_form_1.html")
        await queue_manager.mark_file_processed(str(test_file))

        # Discover files
        files = await extraction_service._discover_files()

        # The marked file should not be in the list
        assert test_file not in files


class TestExtractionServiceRouting:
    """Tests for file routing to appropriate parsers"""

    def test_routes_form_files_correctly(self, extraction_service):
        """Test that form files are routed to form parser"""
        filepath = Path("dummy_data/forms/contact_form_1.html")
        record_type, parser = extraction_service._route_to_parser(filepath)

        assert record_type == RecordType.FORM
        assert parser == extraction_service.form_parser

    def test_routes_email_files_correctly(self, extraction_service):
        """Test that email files are routed to email parser"""
        filepath = Path("dummy_data/emails/email_01.eml")
        record_type, parser = extraction_service._route_to_parser(filepath)

        assert record_type == RecordType.EMAIL
        assert parser == extraction_service.email_parser

    def test_routes_invoice_files_correctly(self, extraction_service):
        """Test that invoice files are routed to invoice parser"""
        filepath = Path("dummy_data/invoices/invoice_TF-2024-001.html")
        record_type, parser = extraction_service._route_to_parser(filepath)

        assert record_type == RecordType.INVOICE
        assert parser == extraction_service.invoice_parser

    def test_raises_error_for_unknown_file_type(self, extraction_service):
        """Test that unknown file types raise an error"""
        filepath = Path("dummy_data/unknown/file.txt")

        with pytest.raises(ValueError, match="Cannot determine file type"):
            extraction_service._route_to_parser(filepath)


class TestExtractionServiceConfidenceCalculation:
    """Tests for confidence score calculation"""

    def test_calculates_confidence_with_ai(self, extraction_service):
        """Test confidence calculation when AI confidence is available"""
        extracted_data = {
            "client_name": "Test User",
            "email": "test@example.com",
        }
        ai_confidence = 0.9
        warnings = []

        confidence = extraction_service._calculate_confidence(
            extracted_data=extracted_data,
            ai_confidence=ai_confidence,
            warnings=warnings,
            record_type=RecordType.FORM,
        )

        # Should use AI confidence
        assert confidence == 0.9

    def test_reduces_confidence_for_errors(self, extraction_service):
        """Test that errors reduce confidence score"""
        from app.models.extraction import ValidationWarning

        extracted_data = {
            "client_name": "Test User",
            "email": "invalid-email",
        }
        ai_confidence = 0.9
        warnings = [ValidationWarning(field="email", message="Invalid email", severity="error")]

        confidence = extraction_service._calculate_confidence(
            extracted_data=extracted_data,
            ai_confidence=ai_confidence,
            warnings=warnings,
            record_type=RecordType.FORM,
        )

        # Should reduce confidence by 0.15 for error
        assert confidence == 0.75  # 0.9 - 0.15

    def test_reduces_confidence_for_warnings(self, extraction_service):
        """Test that warnings reduce confidence score"""
        from app.models.extraction import ValidationWarning

        extracted_data = {
            "client_name": "Test User",
            "email": "test@example.com",
            "phone": "invalid",
        }
        ai_confidence = 0.9
        warnings = [ValidationWarning(field="phone", message="Invalid phone", severity="warning")]

        confidence = extraction_service._calculate_confidence(
            extracted_data=extracted_data,
            ai_confidence=ai_confidence,
            warnings=warnings,
            record_type=RecordType.FORM,
        )

        # Should reduce confidence by 0.05 for warning
        assert confidence == 0.85  # 0.9 - 0.05

    def test_calculates_completeness_confidence(self, extraction_service):
        """Test confidence calculation based on field completeness"""
        # All required fields present
        extracted_data = {
            "client_name": "Test User",
            "email": "test@example.com",
        }

        confidence = extraction_service._calculate_completeness_confidence(
            extracted_data=extracted_data,
            record_type=RecordType.FORM,
        )

        # Should be 1.0 (all required fields present)
        assert confidence == 1.0

        # Missing one required field
        extracted_data = {
            "client_name": "Test User",
            "email": None,
        }

        confidence = extraction_service._calculate_completeness_confidence(
            extracted_data=extracted_data,
            record_type=RecordType.FORM,
        )

        # Should be 0.5 (1 out of 2 required fields)
        assert confidence == 0.5

    def test_confidence_stays_in_valid_range(self, extraction_service):
        """Test that confidence never goes below 0 or above 1"""
        from app.models.extraction import ValidationWarning

        extracted_data = {"client_name": "Test"}
        ai_confidence = 0.1
        warnings = [
            ValidationWarning(field="f1", message="Error", severity="error"),
            ValidationWarning(field="f2", message="Error", severity="error"),
            ValidationWarning(field="f3", message="Error", severity="error"),
        ]

        confidence = extraction_service._calculate_confidence(
            extracted_data=extracted_data,
            ai_confidence=ai_confidence,
            warnings=warnings,
            record_type=RecordType.FORM,
        )

        # Should not go below 0
        assert confidence >= 0.0
        assert confidence <= 1.0


class TestExtractionServiceExtraction:
    """Tests for single file extraction"""

    @pytest.mark.asyncio
    async def test_extracts_form_successfully(self, extraction_service):
        """Test successful extraction from a form file"""
        filepath = Path("dummy_data/forms/contact_form_1.html")

        record = await extraction_service.extract_from_file(filepath)

        assert record is not None
        assert record.type == RecordType.FORM
        assert record.client_name == "Νίκος Παπαδόπουλος"
        assert record.email == "nikos.papadopoulos@example.gr"
        assert record.confidence is not None
        assert 0.0 <= record.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_extracts_email_successfully(self, extraction_service):
        """Test successful extraction from an email file"""
        filepath = Path("dummy_data/emails/email_01.eml")

        record = await extraction_service.extract_from_file(filepath)

        assert record is not None
        assert record.type == RecordType.EMAIL
        assert record.client_name == "Σπύρος Μιχαήλ"
        assert record.email == "spyros.michail@techcorp.gr"
        assert record.confidence is not None

    @pytest.mark.asyncio
    async def test_extracts_invoice_successfully(self, extraction_service):
        """Test successful extraction from an invoice file"""
        filepath = Path("dummy_data/invoices/invoice_TF-2024-001.html")

        record = await extraction_service.extract_from_file(filepath)

        assert record is not None
        assert record.type == RecordType.INVOICE
        assert record.invoice_number == "TF-2024-001"
        assert record.amount is not None
        assert record.confidence is not None


class TestExtractionServiceScanAndExtract:
    """Tests for the complete scan and extract workflow"""

    @pytest.mark.asyncio
    async def test_scan_processes_multiple_files(self, extraction_service, queue_manager):
        """Test that scan processes multiple files and adds them to queue"""
        # Clear queue first
        await queue_manager.clear()
        await queue_manager.clear_processed_files()

        # Mock _discover_files to return only 3 test files (one of each type)
        test_files = [
            Path("dummy_data/forms/contact_form_1.html"),
            Path("dummy_data/emails/email_01.eml"),
            Path("dummy_data/invoices/invoice_TF-2024-001.html"),
        ]

        with patch.object(extraction_service, "_discover_files", return_value=test_files):
            result = await extraction_service.scan_and_extract()

        # Should have processed 3 files
        assert result.processed_count == 3
        assert result.new_items_count == 3
        assert result.failed_count == 0

        # Check that records were added to queue
        records = await queue_manager.list_all()
        assert len(records) == 3

        # Check that files were marked as processed
        test_file = Path("dummy_data/forms/contact_form_1.html")
        is_processed = await queue_manager.is_file_processed(str(test_file))
        assert is_processed

    @pytest.mark.asyncio
    async def test_scan_skips_already_processed_files(self, extraction_service, queue_manager):
        """Test that scan skips files that were already processed"""
        # Clear queue first
        await queue_manager.clear()
        await queue_manager.clear_processed_files()

        # Mark some files as already processed
        test_file1 = Path("dummy_data/forms/contact_form_1.html")
        test_file2 = Path("dummy_data/emails/email_01.eml")
        await queue_manager.mark_file_processed(str(test_file1))
        await queue_manager.mark_file_processed(str(test_file2))

        # Discover files - should not include the processed ones
        discovered = await extraction_service._discover_files()

        # The marked files should not be in the discovered list
        assert test_file1 not in discovered
        assert test_file2 not in discovered

        # But other files should still be there
        assert len(discovered) > 0

    @pytest.mark.asyncio
    async def test_scan_continues_on_individual_file_errors(
        self, extraction_service, queue_manager
    ):
        """Test that scan continues processing even if individual files fail"""
        # Clear queue
        await queue_manager.clear()
        await queue_manager.clear_processed_files()

        # Use only 3 test files
        test_files = [
            Path("dummy_data/forms/contact_form_1.html"),  # This will fail
            Path("dummy_data/forms/contact_form_2.html"),  # This will succeed
            Path("dummy_data/emails/email_01.eml"),  # This will succeed
        ]

        # Mock one parser to fail
        original_parse = extraction_service.form_parser.parse

        def failing_parse(filepath):
            if "contact_form_1" in str(filepath):
                raise Exception("Simulated parsing error")
            return original_parse(filepath)

        with patch.object(extraction_service, "_discover_files", return_value=test_files):
            with patch.object(extraction_service.form_parser, "parse", side_effect=failing_parse):
                result = await extraction_service.scan_and_extract()

                # Should have 1 failure and 2 successes
                assert result.failed_count == 1
                assert result.new_items_count == 2
                assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_scan_handles_timeout(self, extraction_service, queue_manager):
        """Test that scan handles file timeout gracefully"""
        # Clear queue
        await queue_manager.clear()
        await queue_manager.clear_processed_files()

        # Use only 2 test files
        test_files = [
            Path("dummy_data/forms/contact_form_1.html"),  # This will timeout
            Path("dummy_data/emails/email_01.eml"),  # This will succeed
        ]

        # Mock extract_from_file to timeout on one file
        original_extract = extraction_service.extract_from_file

        async def slow_extract(filepath):
            if "contact_form_1" in str(filepath):
                import asyncio

                await asyncio.sleep(35)  # Exceed timeout
            return await original_extract(filepath)

        with patch.object(extraction_service, "_discover_files", return_value=test_files):
            with patch.object(extraction_service, "extract_from_file", side_effect=slow_extract):
                result = await extraction_service.scan_and_extract()

                # Should have 1 timeout and 1 success
                assert result.failed_count == 1
                assert result.new_items_count == 1
                assert any("Timeout" in error for error in result.errors)


class TestExtractionServiceErrorHandling:
    """Tests for error handling and resilience"""

    @pytest.mark.asyncio
    async def test_handles_invalid_file_gracefully(self, extraction_service):
        """Test that invalid files are handled gracefully"""
        filepath = Path("dummy_data/forms/nonexistent.html")

        with pytest.raises(FileNotFoundError):
            await extraction_service.extract_from_file(filepath)

    @pytest.mark.asyncio
    async def test_logs_errors_with_context(self, extraction_service, queue_manager):
        """Test that errors are logged with full context"""
        # Clear queue
        await queue_manager.clear()
        await queue_manager.clear_processed_files()

        # Use only 1 test file
        test_files = [Path("dummy_data/forms/contact_form_1.html")]

        # Mock parser to raise an error
        with patch.object(extraction_service, "_discover_files", return_value=test_files):
            with patch.object(
                extraction_service.form_parser,
                "parse",
                side_effect=Exception("Test error"),
            ):
                result = await extraction_service.scan_and_extract()

                # Should have errors logged
                assert result.failed_count == 1
                assert len(result.errors) == 1
                assert any("Test error" in error for error in result.errors)
