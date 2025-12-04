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

    # Sheet headers
    CLIENTS_HEADERS = [
        "Type",
        "Source",
        "Date",
        "Client Name",
        "Email",
        "Phone",
        "Company",
        "Service Interest",
        "Priority",
        "Message",
        "Extraction Timestamp",
        "Confidence",
    ]

    INVOICES_HEADERS = [
        "Type",
        "Source",
        "Date",
        "Client Name",
        "Amount",
        "VAT",
        "Total Amount",
        "Invoice Number",
        "Extraction Timestamp",
        "Confidence",
    ]

    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds

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
            raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")

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

    def _ensure_sheet_exists(self, sheet_name: str, headers: List[str]) -> None:
        """
        Ensure a sheet exists in the spreadsheet, create it if it doesn't

        Args:
            sheet_name: Name of the sheet to ensure exists
            headers: List of header column names to add if sheet is created

        Raises:
            Exception: If sheet creation fails
        """
        try:
            spreadsheet = self._get_spreadsheet()

            # Try to get the worksheet
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                logger.info(
                    "sheet_already_exists",
                    sheet_name=sheet_name,
                )

                # Check if headers need to be added (if first row is empty)
                try:
                    first_row = worksheet.row_values(1)
                    if not first_row or all(not cell.strip() for cell in first_row):
                        # Sheet exists but has no headers, add them
                        worksheet.update(
                            values=[headers], range_name="A1", value_input_option="USER_ENTERED"
                        )
                        logger.info(
                            "headers_added_to_existing_sheet",
                            sheet_name=sheet_name,
                        )
                except Exception:
                    # If we can't read the first row, assume it's empty and add headers
                    worksheet.update(
                        values=[headers], range_name="A1", value_input_option="USER_ENTERED"
                    )
                    logger.info(
                        "headers_added_to_sheet",
                        sheet_name=sheet_name,
                    )

            except gspread.exceptions.WorksheetNotFound:
                # Sheet doesn't exist, create it
                worksheet = spreadsheet.add_worksheet(
                    title=sheet_name, rows=1000, cols=len(headers)
                )
                # Add headers
                worksheet.update(
                    values=[headers], range_name="A1", value_input_option="USER_ENTERED"
                )
                logger.info(
                    "sheet_created_with_headers",
                    sheet_name=sheet_name,
                    columns=len(headers),
                )

        except Exception as e:
            logger.error(
                "sheet_creation_failed",
                sheet_name=sheet_name,
                error=str(e),
            )
            raise

    def _retry_with_backoff(self, operation: Callable, operation_name: str) -> any:
        """
        Retry operation with exponential backoff

        Args:
            operation: Callable to execute
            operation_name: Name of operation for logging

        Returns:
            Result of operation

        Raises:
            Exception: If all retries fail
        """
        last_exception = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                result = operation()
                if attempt > 1:
                    logger.info(
                        "operation_succeeded_after_retry",
                        operation=operation_name,
                        attempt=attempt,
                    )
                return result

            except APIError as e:
                last_exception = e
                # Check if it's a rate limit error (429) or server error (5xx)
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < self.MAX_RETRIES:
                        # Exponential backoff: base_delay * 2^(attempt-1)
                        backoff = self.BASE_DELAY * (2 ** (attempt - 1))
                        logger.warning(
                            "api_error_retrying",
                            operation=operation_name,
                            attempt=attempt,
                            status_code=e.response.status_code,
                            backoff_seconds=backoff,
                        )
                        time.sleep(backoff)
                        continue
                # For other API errors, don't retry
                logger.error(
                    "api_error_not_retryable",
                    operation=operation_name,
                    status_code=e.response.status_code,
                    error=str(e),
                )
                raise

            except GSpreadException as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    # Exponential backoff: base_delay * 2^(attempt-1)
                    backoff = self.BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "gspread_error_retrying",
                        operation=operation_name,
                        attempt=attempt,
                        error=str(e),
                        backoff_seconds=backoff,
                    )
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(
                        "gspread_error_max_retries",
                        operation=operation_name,
                        attempt=attempt,
                        error=str(e),
                    )
                    raise

            except Exception as e:
                # For unexpected errors, log and raise immediately
                logger.error(
                    "unexpected_error",
                    operation=operation_name,
                    attempt=attempt,
                    error=str(e),
                )
                raise

        # If we get here, all retries failed
        logger.error(
            "operation_failed_all_retries",
            operation=operation_name,
            max_retries=self.MAX_RETRIES,
            last_error=str(last_exception),
        )
        raise last_exception

    def _write_to_sheet(self, sheet_name: str, row_data: List[str], record_id: str) -> int:
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

        return self._retry_with_backoff(write_operation, f"write_to_{sheet_name}_{record_id}")

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

        # Ensure sheet exists before writing
        self._ensure_sheet_exists(self.CLIENTS_SHEET, self.CLIENTS_HEADERS)

        # Prepare row data
        # Note: Prefix phone with ' to force text format in Google Sheets, because the default becomes a number otherwise
        phone_value = f"'{record.phone}" if record.phone else ""

        row_data = [
            record.type.value,  # Type
            record.source_file,  # Source
            record.date or "",  # Date
            record.client_name or "",  # Client Name
            record.email or "",  # Email
            phone_value,  # Phone (prefixed with ' for text format)
            record.company or "",  # Company
            record.service_interest or "",  # Service Interest
            record.priority or "",  # Priority
            record.message or "",  # Message
            record.extraction_timestamp.isoformat(),  # Extraction Timestamp
            f"{record.confidence:.2f}" if record.confidence is not None else "",  # Confidence
        ]

        try:
            row_number = self._write_to_sheet(self.CLIENTS_SHEET, row_data, record.id)

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
            ValueError: If record doesn't have invoice data
            Exception: If write operation fails after retries
        """
        # Accept INVOICE type OR any record with invoice_number (e.g., emails containing invoices)
        if record.type != RecordType.INVOICE and not record.invoice_number:
            raise ValueError(
                f"Cannot write record to Invoices sheet. Record must be type INVOICE "
                f"or contain invoice_number. Got type {record.type.value} with no invoice_number."
            )

        # Ensure sheet exists before writing
        self._ensure_sheet_exists(self.INVOICES_SHEET, self.INVOICES_HEADERS)

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
            row_number = self._write_to_sheet(self.INVOICES_SHEET, row_data, record.id)

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
