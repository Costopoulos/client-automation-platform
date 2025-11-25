from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from gspread.exceptions import APIError

from app.integrations.sheets import GoogleSheetsClient
from app.models.extraction import ExtractionRecord, RecordType


@pytest.fixture
def mock_credentials_file(tmp_path):
    """Create a temporary credentials file"""
    creds_file = tmp_path / "test-credentials.json"
    creds_file.write_text('{"type": "service_account", "project_id": "test"}')
    return str(creds_file)


@pytest.fixture
def mock_spreadsheet_id():
    """Return a test spreadsheet ID"""
    return "test-spreadsheet-id-123"


@pytest.fixture
def client_record():
    """Create a sample client extraction record"""
    return ExtractionRecord(
        id="test-client-1",
        type=RecordType.FORM,
        source_file="contact_form_1.html",
        date="2024-01-15",
        client_name="John Doe",
        email="john@example.com",
        phone="+30 210 1234567",
        company="Test Company",
        service_interest="Web Development",
        priority="High",
        message="Need a new website",
        confidence=0.95,
        extraction_timestamp=datetime(2024, 1, 15, 10, 30, 0),
    )


@pytest.fixture
def invoice_record():
    """Create a sample invoice extraction record"""
    return ExtractionRecord(
        id="test-invoice-1",
        type=RecordType.INVOICE,
        source_file="invoice_TF-2024-001.html",
        date="2024-01-15",
        client_name="Test Company",
        invoice_number="TF-2024-001",
        amount=1000.0,
        vat=240.0,
        total_amount=1240.0,
        confidence=0.98,
        extraction_timestamp=datetime(2024, 1, 15, 10, 30, 0),
    )


class TestGoogleSheetsClient:
    """Test GoogleSheetsClient class"""

    def test_init_with_valid_credentials(self, mock_credentials_file, mock_spreadsheet_id):
        """Test initialization with valid credentials file"""
        client = GoogleSheetsClient(mock_credentials_file, mock_spreadsheet_id)
        assert client.credentials_path == mock_credentials_file
        assert client.spreadsheet_id == mock_spreadsheet_id
        assert client._client is None
        assert client._spreadsheet is None

    def test_init_with_missing_credentials_file(self, mock_spreadsheet_id):
        """Test initialization with missing credentials file raises error"""
        with pytest.raises(FileNotFoundError):
            GoogleSheetsClient("nonexistent.json", mock_spreadsheet_id)

    @patch("app.integrations.sheets.ServiceAccountCredentials")
    @patch("app.integrations.sheets.gspread")
    def test_authenticate_success(
        self,
        mock_gspread,
        mock_creds,
        mock_credentials_file,
        mock_spreadsheet_id,
    ):
        """Test successful authentication"""
        # Setup mocks
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_spreadsheet.title = "Test Spreadsheet"
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_gspread.authorize.return_value = mock_client

        # Create client and authenticate
        client = GoogleSheetsClient(mock_credentials_file, mock_spreadsheet_id)
        client._authenticate()

        # Verify authentication was called
        mock_creds.from_json_keyfile_name.assert_called_once()
        mock_gspread.authorize.assert_called_once()
        mock_client.open_by_key.assert_called_once_with(mock_spreadsheet_id)

        assert client._client is not None
        assert client._spreadsheet is not None

    @patch("app.integrations.sheets.ServiceAccountCredentials")
    @patch("app.integrations.sheets.gspread")
    def test_authenticate_failure(
        self,
        mock_gspread,
        mock_creds,
        mock_credentials_file,
        mock_spreadsheet_id,
    ):
        """Test authentication failure raises ValueError"""
        # Setup mock to raise exception
        mock_gspread.authorize.side_effect = Exception("Auth failed")

        # Create client and attempt authentication
        client = GoogleSheetsClient(mock_credentials_file, mock_spreadsheet_id)

        with pytest.raises(ValueError, match="Failed to authenticate"):
            client._authenticate()

    @patch("app.integrations.sheets.ServiceAccountCredentials")
    @patch("app.integrations.sheets.gspread")
    def test_write_client_record_success(
        self,
        mock_gspread,
        mock_creds,
        mock_credentials_file,
        mock_spreadsheet_id,
        client_record,
    ):
        """Test successfully writing a client record"""
        # Setup mocks
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [["header"], ["row1"], ["row2"]]
        mock_spreadsheet = Mock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client = Mock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_gspread.authorize.return_value = mock_client

        # Create client and write record
        client = GoogleSheetsClient(mock_credentials_file, mock_spreadsheet_id)
        row_number = client.write_client_record(client_record)

        # Verify worksheet operations
        mock_spreadsheet.worksheet.assert_called_with("Clients")
        mock_worksheet.append_row.assert_called_once()
        assert row_number == 3  # Header + 2 existing rows

        # Verify row data format
        call_args = mock_worksheet.append_row.call_args
        row_data = call_args[0][0]
        assert row_data[0] == "FORM"  # Type
        assert row_data[3] == "John Doe"  # Client Name
        assert row_data[4] == "john@example.com"  # Email

    @patch("app.integrations.sheets.ServiceAccountCredentials")
    @patch("app.integrations.sheets.gspread")
    def test_write_invoice_record_success(
        self,
        mock_gspread,
        mock_creds,
        mock_credentials_file,
        mock_spreadsheet_id,
        invoice_record,
    ):
        """Test successfully writing an invoice record"""
        # Setup mocks
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [["header"], ["row1"]]
        mock_spreadsheet = Mock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client = Mock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_gspread.authorize.return_value = mock_client

        # Create client and write record
        client = GoogleSheetsClient(mock_credentials_file, mock_spreadsheet_id)
        row_number = client.write_invoice_record(invoice_record)

        # Verify worksheet operations
        mock_spreadsheet.worksheet.assert_called_with("Invoices")
        mock_worksheet.append_row.assert_called_once()
        assert row_number == 2  # Header + 1 existing row

        # Verify row data format
        call_args = mock_worksheet.append_row.call_args
        row_data = call_args[0][0]
        assert row_data[0] == "INVOICE"  # Type
        assert row_data[3] == "Test Company"  # Client Name
        assert row_data[7] == "TF-2024-001"  # Invoice Number

    def test_write_client_record_wrong_type(
        self, mock_credentials_file, mock_spreadsheet_id, invoice_record
    ):
        """Test writing invoice record to client sheet raises error"""
        client = GoogleSheetsClient(mock_credentials_file, mock_spreadsheet_id)

        with pytest.raises(ValueError, match="Cannot write record type INVOICE to Clients sheet"):
            client.write_client_record(invoice_record)

    def test_write_invoice_record_wrong_type(
        self, mock_credentials_file, mock_spreadsheet_id, client_record
    ):
        """Test writing client record to invoice sheet raises error"""
        client = GoogleSheetsClient(mock_credentials_file, mock_spreadsheet_id)

        with pytest.raises(ValueError, match="Cannot write record type FORM to Invoices sheet"):
            client.write_invoice_record(client_record)
