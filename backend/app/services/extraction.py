import asyncio
import traceback
from pathlib import Path
from typing import List, Optional

import structlog

from app.config import get_settings
from app.models.extraction import ExtractionRecord, RecordType, ScanResult
from app.parsers.base import BaseParser
from app.parsers.hybrid.email_parser import HybridEmailParser
from app.parsers.hybrid.form_parser import HybridFormParser
from app.parsers.hybrid.invoice_parser import HybridInvoiceParser
from app.pending_queue.manager import PendingQueueManager

logger = structlog.get_logger()


class ExtractionService:
    """
    Orchestrates file discovery, extraction, and queue management

    This service is responsible for:
    - Scanning source directories for new unprocessed files
    - Routing files to appropriate parsers based on type
    - Calculating confidence scores combining AI and validation
    - Managing timeouts to prevent hanging
    - Handling errors gracefully to continue processing
    """

    # File timeout in seconds
    FILE_TIMEOUT = 30

    def __init__(self, queue_manager: PendingQueueManager):
        """
        Initialize extraction service

        Args:
            queue_manager: Pending queue manager for storing extraction records
        """
        self.queue_manager = queue_manager
        self.settings = get_settings()

        # Initialize parsers
        self.form_parser = HybridFormParser()
        self.email_parser = HybridEmailParser()
        self.invoice_parser = HybridInvoiceParser()

        logger.info(
            "extraction_service_initialized",
            forms_dir=self.settings.forms_dir,
            emails_dir=self.settings.emails_dir,
            invoices_dir=self.settings.invoices_dir,
        )

    async def scan_and_extract(self) -> ScanResult:
        """
        Scan source directories and extract from new unprocessed files

        This method:
        1. Discovers all files in source directories
        2. Filters out already processed files
        3. Processes each new file with timeout protection
        4. Continues processing even if individual files fail
        5. Returns summary of results

        Returns:
            ScanResult with counts and any errors encountered
        """
        logger.info("scan_started")

        # Discover files from all source directories
        files_to_process = await self._discover_files()

        logger.info(
            "files_discovered",
            total_files=len(files_to_process),
        )

        # Track results
        processed_count = 0
        new_items_count = 0
        failed_count = 0
        errors = []

        # Process each file
        for filepath in files_to_process:
            try:
                # Extract from file with timeout protection
                record = await self._extract_with_timeout(filepath)

                if record:
                    # Add to pending queue
                    await self.queue_manager.add(record)
                    new_items_count += 1

                    # Mark file as processed
                    await self.queue_manager.mark_file_processed(str(filepath))

                    logger.info(
                        "file_processed_successfully",
                        filepath=str(filepath),
                        record_type=record.type,
                        confidence=record.confidence,
                        warnings_count=len(record.warnings),
                    )

                processed_count += 1

            except asyncio.TimeoutError:
                # Timeout occurred - log and continue
                error_msg = f"Timeout processing {filepath} (exceeded {self.FILE_TIMEOUT}s)"
                logger.error(
                    "file_processing_timeout",
                    filepath=str(filepath),
                    timeout_seconds=self.FILE_TIMEOUT,
                )
                errors.append(error_msg)
                failed_count += 1

            except Exception as e:
                # Other error - log with full context and continue
                error_msg = f"Error processing {filepath}: {str(e)}"
                logger.error(
                    "file_processing_error",
                    filepath=str(filepath),
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc(),
                )
                errors.append(error_msg)
                failed_count += 1

        result = ScanResult(
            processed_count=processed_count,
            new_items_count=new_items_count,
            failed_count=failed_count,
            errors=errors,
        )

        logger.info(
            "scan_completed",
            processed=processed_count,
            new_items=new_items_count,
            failed=failed_count,
            error_count=len(errors),
        )

        return result

    async def _discover_files(self) -> List[Path]:
        """
        Discover all files in source directories that haven't been processed

        Returns:
            List of file paths to process
        """
        files_to_process = []

        # Scan forms directory
        forms_dir = Path(self.settings.forms_dir)
        if forms_dir.exists():
            for filepath in forms_dir.glob("*.html"):
                if not await self.queue_manager.is_file_processed(str(filepath)):
                    files_to_process.append(filepath)

        # Scan emails directory
        emails_dir = Path(self.settings.emails_dir)
        if emails_dir.exists():
            for filepath in emails_dir.glob("*.eml"):
                if not await self.queue_manager.is_file_processed(str(filepath)):
                    files_to_process.append(filepath)

        # Scan invoices directory
        invoices_dir = Path(self.settings.invoices_dir)
        if invoices_dir.exists():
            for filepath in invoices_dir.glob("*.html"):
                if not await self.queue_manager.is_file_processed(str(filepath)):
                    files_to_process.append(filepath)

        return files_to_process

    async def _extract_with_timeout(self, filepath: Path) -> Optional[ExtractionRecord]:
        """
        Extract from file with timeout protection

        Args:
            filepath: Path to file to extract from

        Returns:
            ExtractionRecord if successful, None if timeout or error

        Raises:
            asyncio.TimeoutError: If extraction exceeds timeout
            Exception: If extraction fails
        """
        # Run extraction with timeout
        try:
            record = await asyncio.wait_for(
                self.extract_from_file(filepath),
                timeout=self.FILE_TIMEOUT,
            )
            return record
        except asyncio.TimeoutError:
            logger.error(
                "extraction_timeout",
                filepath=str(filepath),
                timeout_seconds=self.FILE_TIMEOUT,
            )
            raise

    async def extract_from_file(self, filepath: Path) -> ExtractionRecord:
        """
        Extract data from a single file

        This method:
        1. Determines file type and routes to appropriate parser
        2. Extracts data using the parser
        3. Validates the extracted data
        4. Calculates confidence score
        5. Creates an ExtractionRecord

        Args:
            filepath: Path to file to extract from

        Returns:
            ExtractionRecord with extracted data and metadata

        Raises:
            ValueError: If file type cannot be determined
            Exception: If extraction fails
        """
        logger.info("extraction_started", filepath=str(filepath))

        # Determine file type and get appropriate parser
        record_type, parser = self._route_to_parser(filepath)

        # Parse the file
        extracted_data = await asyncio.to_thread(parser.parse, filepath)

        # Validate the extracted data
        warnings = parser.validate(extracted_data)

        # Extract metadata from parser result
        extraction_method = extracted_data.pop("_extraction_method", "unknown")
        ai_confidence = extracted_data.pop("_confidence", None)
        field_confidences = extracted_data.pop("field_confidences", None)

        # Calculate overall confidence
        confidence = self._calculate_confidence(
            extracted_data=extracted_data,
            ai_confidence=ai_confidence,
            warnings=warnings,
            record_type=record_type,
        )

        # Create extraction record
        record = ExtractionRecord(
            type=record_type,
            source_file=str(filepath),
            confidence=confidence,
            warnings=warnings,
            extraction_method=extraction_method,
            field_confidences=field_confidences,
            raw_extraction=extracted_data.copy(),
            **extracted_data,  # Unpack extracted fields
        )

        logger.info(
            "extraction_completed",
            filepath=str(filepath),
            record_type=record_type,
            extraction_method=extraction_method,
            confidence=confidence,
            warnings_count=len(warnings),
        )

        return record

    def _route_to_parser(self, filepath: Path) -> tuple[RecordType, BaseParser]:
        """
        Determine appropriate parser based on file type and location

        Args:
            filepath: Path to file

        Returns:
            Tuple of (RecordType, Parser instance)

        Raises:
            ValueError: If file type cannot be determined
        """
        filepath_str = str(filepath)

        # Check if file is in forms directory
        if "/forms/" in filepath_str and filepath.suffix == ".html":
            return RecordType.FORM, self.form_parser

        # Check if file is in emails directory
        if "/emails/" in filepath_str and filepath.suffix == ".eml":
            return RecordType.EMAIL, self.email_parser

        # Check if file is in invoices directory
        if "/invoices/" in filepath_str and filepath.suffix == ".html":
            return RecordType.INVOICE, self.invoice_parser

        # Cannot determine type
        raise ValueError(f"Cannot determine file type for: {filepath}")

    def _calculate_confidence(
        self,
        extracted_data: dict,
        ai_confidence: Optional[float],
        warnings: list,
        record_type: RecordType,
    ) -> float:
        """
        Calculate overall confidence score combining AI confidence and validation results

        Confidence calculation strategy:
        1. Start with AI confidence if available (0.0-1.0)
        2. Adjust based on validation warnings:
           - Each error reduces confidence by 0.15
           - Each warning reduces confidence by 0.05
        3. Consider field completeness for required fields
        4. Ensure final confidence is in range [0.0, 1.0]

        Args:
            extracted_data: Dictionary of extracted field values
            ai_confidence: Confidence from AI extraction (if used)
            warnings: List of validation warnings
            record_type: Type of record being processed

        Returns:
            Overall confidence score (0.0-1.0)
        """
        # Start with AI confidence or default
        if ai_confidence is not None:
            confidence = ai_confidence
        else:
            # For rule-based extraction, calculate based on field completeness
            confidence = self._calculate_completeness_confidence(extracted_data, record_type)

        # Adjust for validation warnings
        error_count = sum(1 for w in warnings if w.severity == "error")
        warning_count = sum(1 for w in warnings if w.severity == "warning")

        # Reduce confidence based on issues
        confidence -= error_count * 0.15  # Errors have bigger impact
        confidence -= warning_count * 0.05  # Warnings have smaller impact

        # Ensure confidence is in valid range
        confidence = max(0.0, min(1.0, confidence))

        return round(confidence, 3)

    def _calculate_completeness_confidence(
        self,
        extracted_data: dict,
        record_type: RecordType,
    ) -> float:
        """
        Calculate confidence based on field completeness

        Args:
            extracted_data: Dictionary of extracted field values
            record_type: Type of record

        Returns:
            Confidence score based on completeness (0.0-1.0)
        """
        # Define required fields for each record type
        required_fields = {
            RecordType.FORM: ["client_name", "email"],
            RecordType.EMAIL: ["client_name", "email", "message"],
            RecordType.INVOICE: ["invoice_number", "amount", "vat", "total_amount"],
        }

        fields = required_fields.get(record_type, [])
        if not fields:
            return 0.5  # Default for unknown types

        # Count non-null required fields
        present_count = sum(
            1 for field in fields if extracted_data.get(field) is not None and extracted_data.get(field) != ""
        )

        # Calculate completeness ratio
        completeness = present_count / len(fields) if fields else 0.0

        return round(completeness, 3)
