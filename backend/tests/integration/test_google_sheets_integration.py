from datetime import datetime

import pytest

from app.config import get_settings
from app.integrations.sheets import GoogleSheetsClient
from app.models.extraction import ExtractionRecord, RecordType


@pytest.fixture
def sheets_client():
    """Create a real Google Sheets client using environment configuration"""
    settings = get_settings()
    return GoogleSheetsClient(
        credentials_path=settings.google_credentials_path,
        spreadsheet_id=settings.google_spreadsheet_id,
    )


@pytest.fixture
def test_client_record():
    """Create a test client extraction record"""
    return ExtractionRecord(
        id="integration-test-client",
        type=RecordType.FORM,
        source_file="test_contact_form.html",
        date="2024-01-15",
        client_name="Integration Test Client",
        email="test@integration.com",
        phone="+30 210 9999999",
        company="Test Integration Company",
        service_interest="Integration Testing",
        priority="High",
        message="This is an integration test record",
        confidence=0.99,
        extraction_timestamp=datetime(2024, 1, 15, 12, 0, 0),
    )


@pytest.fixture
def test_invoice_record():
    """Create a test invoice extraction record"""
    return ExtractionRecord(
        id="integration-test-invoice",
        type=RecordType.INVOICE,
        source_file="test_invoice_TF-2024-999.html",
        date="2024-01-15",
        client_name="Test Integration Company",
        invoice_number="TF-2024-999",
        amount=999.99,
        vat=239.99,
        total_amount=1239.98,
        confidence=0.99,
        extraction_timestamp=datetime(2024, 1, 15, 12, 0, 0),
    )


@pytest.mark.integration
class TestGoogleSheetsIntegration:
    """Integration tests that write to real Google Sheets"""

    def test_write_client_record_to_real_sheet(self, sheets_client, test_client_record):
        """Test writing a client record to the real Google Sheets"""
        # Write the record
        row_number = sheets_client.write_client_record(test_client_record)

        # Verify we got a row number back
        assert row_number > 0
        assert isinstance(row_number, int)

        print(f"\nSuccessfully wrote client record to row {row_number}")
        print(f"  Record ID: {test_client_record.id}")
        print(f"  Client: {test_client_record.client_name}")
        print(f"  Email: {test_client_record.email}")

    def test_write_invoice_record_to_real_sheet(self, sheets_client, test_invoice_record):
        """Test writing an invoice record to the real Google Sheets"""
        # Write the record
        row_number = sheets_client.write_invoice_record(test_invoice_record)

        # Verify we got a row number back
        assert row_number > 0
        assert isinstance(row_number, int)

        print(f"\nSuccessfully wrote invoice record to row {row_number}")
        print(f"  Record ID: {test_invoice_record.id}")
        print(f"  Invoice: {test_invoice_record.invoice_number}")
        print(f"  Total: €{test_invoice_record.total_amount}")

    def test_write_email_type_client_record(self, sheets_client):
        """Test writing an EMAIL type record to Clients sheet"""
        email_record = ExtractionRecord(
            id="integration-test-email",
            type=RecordType.EMAIL,
            source_file="test_email.eml",
            date="2024-01-15",
            client_name="Email Test Client",
            email="email-test@integration.com",
            phone="+30 210 8888888",
            company="Email Test Company",
            service_interest="Email Inquiry",
            message="This is a test email inquiry",
            confidence=0.95,
            extraction_timestamp=datetime(2024, 1, 15, 12, 30, 0),
        )

        # Write the record
        row_number = sheets_client.write_client_record(email_record)

        # Verify
        assert row_number > 0
        print(f"\nSuccessfully wrote EMAIL record to Clients sheet at row {row_number}")

    def test_authentication_and_spreadsheet_access(self, sheets_client):
        """Test that authentication works and we can access the spreadsheet"""
        # This will trigger authentication
        spreadsheet = sheets_client._get_spreadsheet()

        # Verify we got a spreadsheet object
        assert spreadsheet is not None
        assert spreadsheet.title is not None

        print("\nSuccessfully authenticated and accessed spreadsheet")
        print(f"  Spreadsheet: {spreadsheet.title}")
        print(f"  ID: {sheets_client.spreadsheet_id}")

    def test_write_record_with_missing_optional_fields(self, sheets_client):
        """Test writing a record with some optional fields missing"""
        minimal_record = ExtractionRecord(
            id="integration-test-minimal",
            type=RecordType.FORM,
            source_file="test_minimal_form.html",
            client_name="Minimal Test Client",
            email="minimal@test.com",
            confidence=0.85,
            extraction_timestamp=datetime.utcnow(),
        )

        # Write the record
        row_number = sheets_client.write_client_record(minimal_record)

        # Verify
        assert row_number > 0
        print(f"\nSuccessfully wrote minimal record to row {row_number}")
        print("Only required fields populated")

    def test_write_invoice_with_decimal_amounts(self, sheets_client):
        """Test writing invoice with various decimal amounts"""
        decimal_invoice = ExtractionRecord(
            id="integration-test-decimal",
            type=RecordType.INVOICE,
            source_file="test_decimal_invoice.html",
            date="2024-01-15",
            client_name="Decimal Test Company",
            invoice_number="TF-2024-888",
            amount=1234.56,
            vat=296.29,
            total_amount=1530.85,
            confidence=0.98,
            extraction_timestamp=datetime.utcnow(),
        )

        # Write the record
        row_number = sheets_client.write_invoice_record(decimal_invoice)

        # Verify
        assert row_number > 0
        print(f"\nSuccessfully wrote invoice with decimal amounts to row {row_number}")
        print(f"  Amount: €{decimal_invoice.amount:.2f}")
        print(f"  VAT: €{decimal_invoice.vat:.2f}")
        print(f"  Total: €{decimal_invoice.total_amount:.2f}")


@pytest.mark.integration
def test_error_handling_wrong_record_type(sheets_client, test_invoice_record):
    """Test that writing wrong record type to sheet raises error"""
    with pytest.raises(ValueError, match="Cannot write record type INVOICE"):
        sheets_client.write_client_record(test_invoice_record)

    print("\nCorrectly rejected INVOICE record for Clients sheet")


@pytest.mark.integration
def test_error_handling_wrong_record_type_invoice(sheets_client, test_client_record):
    """Test that writing wrong record type to invoice sheet raises error"""
    with pytest.raises(ValueError, match="Cannot write record to Invoices sheet"):
        sheets_client.write_invoice_record(test_client_record)

    print("\nCorrectly rejected FORM record for Invoices sheet")
