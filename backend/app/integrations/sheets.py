import time
from pathlib import Path
from typing import Callable, List, Optional

import gspread
import structlog
from gspread.exceptions import APIError, GSpreadException
from oauth2client.service_account import ServiceAccountCredentials

from app.models.extraction import ExtractionRecord, RecordType

logger = structlog.get_logger()


class GoogleSheetsClient:
    """Client for writing approved extraction records to Google Sheets"""

    # Google Sheets API scopes
    SCOPES = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Sheet names
    CLIENTS_SHEET = "Clients"
    INVOICES_SHEET = "Invoices"


    def __init__(self, credentials_path: str, spreadsheet_id: str):
        """
        Initialize Google Sheets client with service account credentials

        Args:
            credentials_path: Path to service account JSON credentials file
            spreadsheet_id: Google Sheets spreadsheet ID

        Raises:
            FileNotFoundError: If credentials file doesn't exist
            ValueError: If credentials are invalid
        """
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None

        # Validate credentials file exists
        if not Path(credentials_path).exists():
            raise FileNotFoundError(
                f"Google credentials file not found: {credentials_path}"
            )

        logger.info(
            "google_sheets_client_initialized",
            credentials_path=credentials_path,
            spreadsheet_id=spreadsheet_id,
        )

    def _authenticate(self) -> None:
        """
        Authenticate with Google Sheets API using service account

        Raises:
            ValueError: If authentication fails
        """
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_path, self.SCOPES
            )
            self._client = gspread.authorize(credentials)
            self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)

            logger.info(
                "google_sheets_authenticated",
                spreadsheet_id=self.spreadsheet_id,
                spreadsheet_title=self._spreadsheet.title,
            )
        except Exception as e:
            logger.error(
                "google_sheets_authentication_failed",
                error=str(e),
                credentials_path=self.credentials_path,
            )
            raise ValueError(f"Failed to authenticate with Google Sheets: {e}")

    def _get_client(self) -> gspread.Client:
        """Get authenticated client, authenticating if necessary"""
        if self._client is None:
            self._authenticate()
        return self._client

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """Get spreadsheet, authenticating if necessary"""
        if self._spreadsheet is None:
            self._authenticate()
        return self._spreadsheet


    def _write_to_sheet(
        self, sheet_name: str, row_data: List[str], record_id: str
    ) -> int:
        """
        Write row data to specified sheet with retry logic

        Args:
            sheet_name: Name of the sheet to write to
            row_data: List of values to write as a row
            record_id: ID of the record being written (for logging)

        Returns:
            Row number where data was written

        Raises:
            Exception: If write operation fails after retries
        """

        def write_operation():
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")
            # Return the row number (current row count)
            return len(worksheet.get_all_values())

    def write_client_record(self, record: ExtractionRecord) -> int:
        """
        Write client data to Clients sheet

        Args:
            record: Extraction record with client data

        Returns:
            Row number where data was written

        Raises:
            ValueError: If record type is not FORM or EMAIL
            Exception: If write operation fails after retries
        """
        if record.type not in [RecordType.FORM, RecordType.EMAIL]:
            raise ValueError(
                f"Cannot write record type {record.type.value} to Clients sheet. "
                f"Expected FORM or EMAIL."
            )

        # Prepare row data
        row_data = [
            record.type.value,  # Type
            record.source_file,  # Source
            record.date or "",  # Date
            record.client_name or "",  # Client Name
            record.email or "",  # Email
            record.phone or "",  # Phone
            record.company or "",  # Company
            record.service_interest or "",  # Service Interest
            record.priority or "",  # Priority
            record.message or "",  # Message
            record.extraction_timestamp.isoformat(),  # Extraction Timestamp
            f"{record.confidence:.2f}" if record.confidence is not None else "",  # Confidence
        ]

        try:
            row_number = self._write_to_sheet(
                self.CLIENTS_SHEET, row_data, record.id
            )

            logger.info(
                "client_record_written",
                record_id=record.id,
                record_type=record.type.value,
                row_number=row_number,
                source_file=record.source_file,
            )

            return row_number

        except Exception as e:
            logger.error(
                "client_record_write_failed",
                record_id=record.id,
                error=str(e),
            )
            raise

    def write_invoice_record(self, record: ExtractionRecord) -> int:
        """
        Write invoice data to Invoices sheet

        Args:
            record: Extraction record with invoice data

        Returns:
            Row number where data was written

        Raises:
            ValueError: If record type is not INVOICE
            Exception: If write operation fails after retries
        """
        if record.type != RecordType.INVOICE:
            raise ValueError(
                f"Cannot write record type {record.type.value} to Invoices sheet. "
                f"Expected INVOICE."
            )

        # Prepare row data
        row_data = [
            record.type.value,  # Type
            record.source_file,  # Source
            record.date or "",  # Date
            record.client_name or "",  # Client Name
            f"{record.amount:.2f}" if record.amount is not None else "",  # Amount
            f"{record.vat:.2f}" if record.vat is not None else "",  # VAT
            f"{record.total_amount:.2f}" if record.total_amount is not None else "",  # Total Amount
            record.invoice_number or "",  # Invoice Number
            record.extraction_timestamp.isoformat(),  # Extraction Timestamp
            f"{record.confidence:.2f}" if record.confidence is not None else "",  # Confidence
        ]

        try:
            row_number = self._write_to_sheet(
                self.INVOICES_SHEET, row_data, record.id
            )

            logger.info(
                "invoice_record_written",
                record_id=record.id,
                record_type=record.type.value,
                row_number=row_number,
                source_file=record.source_file,
                invoice_number=record.invoice_number,
            )

            return row_number

        except Exception as e:
            logger.error(
                "invoice_record_write_failed",
                record_id=record.id,
                error=str(e),
            )
            raise
