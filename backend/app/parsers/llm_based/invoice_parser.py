from pathlib import Path
from typing import Dict, List

from app.models.extraction import RecordType, ValidationWarning
from app.parsers.base import BaseParser
from app.parsers.llm_based.extractor import AIExtractor


class LLMInvoiceParser(BaseParser):
    """LLM-powered parser for invoice files with intelligent extraction"""

    def __init__(self):
        """Initialize with AI extractor"""
        self.extractor = AIExtractor()
        self.schema = {
            "invoice_number": "Invoice number in format TF-YYYY-NNN",
            "date": "Invoice date",
            "client_name": "Client or customer name",
            "amount": "Base amount before VAT (as a number)",
            "vat": "VAT amount (as a number)",
            "total_amount": "Total amount including VAT (as a number)",
        }

    def parse(self, filepath: Path) -> Dict:
        """
        Parse invoice file using LLM extraction

        Args:
            filepath: Path to HTML invoice file

        Returns:
            Dictionary with extracted financial fields
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Use LLM to extract structured data
        extracted_data, confidence = self.extractor.extract_structured_data(
            content, self.schema, RecordType.INVOICE
        )

        # Remove field_confidences from the result (internal metadata)
        field_confidences = extracted_data.pop("field_confidences", {})

        # Convert string amounts to floats if needed
        for field in ["amount", "vat", "total_amount"]:
            if field in extracted_data and extracted_data[field] is not None:
                try:
                    extracted_data[field] = float(extracted_data[field])
                except (ValueError, TypeError):
                    pass  # Keep as is if conversion fails

        # Add confidence as metadata
        extracted_data["_confidence"] = confidence
        extracted_data["_field_confidences"] = field_confidences

        return extracted_data

    def validate(self, data: Dict) -> List[ValidationWarning]:
        """
        Validate extracted invoice data

        Args:
            data: Dictionary of extracted data

        Returns:
            List of validation warnings
        """
        warnings = []

        # Check for missing required fields
        required_fields = ["invoice_number", "client_name", "amount", "vat", "total_amount"]
        for field in required_fields:
            if not data.get(field):
                warnings.append(
                    ValidationWarning(
                        field=field,
                        message=f"Required field '{field}' is missing",
                        severity="error",
                    )
                )

        # Validate invoice number format (TF-YYYY-NNN)
        invoice_num = data.get("invoice_number")
        if invoice_num:
            import re
            if not re.match(r"TF-\d{4}-\d{3}", invoice_num):
                warnings.append(
                    ValidationWarning(
                        field="invoice_number",
                        message=f"Invalid invoice number format: {invoice_num}. Expected TF-YYYY-NNN",
                        severity="warning",
                    )
                )

        # Validate VAT calculation (should be 24% of amount)
        amount = data.get("amount")
        vat = data.get("vat")
        if amount is not None and vat is not None:
            expected_vat = round(amount * 0.24, 2)
            if abs(vat - expected_vat) > 0.01:  # Allow small rounding differences
                warnings.append(
                    ValidationWarning(
                        field="vat",
                        message=f"VAT calculation error: expected {expected_vat} (24% of {amount}), got {vat}",
                        severity="error",
                    )
                )

        # Validate total calculation (should be amount + vat)
        total = data.get("total_amount")
        if amount is not None and vat is not None and total is not None:
            expected_total = round(amount + vat, 2)
            if abs(total - expected_total) > 0.01:  # Allow small rounding differences
                warnings.append(
                    ValidationWarning(
                        field="total_amount",
                        message=f"Total calculation error: expected {expected_total} ({amount} + {vat}), got {total}",
                        severity="error",
                    )
                )

        # Check confidence score
        confidence = data.get("_confidence", 1.0)
        if confidence < 0.7:
            warnings.append(
                ValidationWarning(
                    field="overall",
                    message=f"Low extraction confidence: {confidence:.2f}",
                    severity="warning",
                )
            )

        return warnings
