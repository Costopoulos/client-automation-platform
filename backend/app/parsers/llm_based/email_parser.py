from pathlib import Path
from typing import Dict, List

from app.models.extraction import RecordType, ValidationWarning
from app.parsers.base import BaseParser
from app.parsers.llm_based.extractor import AIExtractor
from app.parsers.utils import is_valid_email, is_valid_greek_phone


class LLMEmailParser(BaseParser):
    """LLM-powered parser for email files with intelligent extraction"""

    def __init__(self):
        """Initialize with AI extractor"""
        self.extractor = AIExtractor()
        self.schema = {
            "client_name": "Full name of the client or sender",
            "email": "Email address",
            "phone": "Phone number (Greek format)",
            "company": "Company or organization name",
            "service_interest": "Main service, product, or subject of interest",
            "message": "Brief 1-2 sentence summary of the main request or message content",
            "date": "Email date",
        }

    def parse(self, filepath: Path) -> Dict:
        """
        Parse email file using LLM extraction with message summarization

        Args:
            filepath: Path to EML email file

        Returns:
            Dictionary with extracted and summarized fields
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Use LLM to extract structured data with summarization
        extracted_data, confidence = self.extractor.extract_structured_data(
            content, self.schema, RecordType.EMAIL
        )

        # Remove field_confidences from the result (internal metadata)
        field_confidences = extracted_data.pop("field_confidences", {})

        # Add confidence as metadata
        extracted_data["_confidence"] = confidence
        extracted_data["_field_confidences"] = field_confidences

        return extracted_data

    def validate(self, data: Dict) -> List[ValidationWarning]:
        """
        Validate extracted email data

        Args:
            data: Dictionary of extracted data

        Returns:
            List of validation warnings
        """
        warnings = []

        # Validate email format
        if data.get("email"):
            if not is_valid_email(data["email"]):
                warnings.append(
                    ValidationWarning(
                        field="email",
                        message=f"Invalid email format: {data['email']}",
                        severity="error",
                    )
                )

        # Validate phone format if present
        if data.get("phone"):
            if not is_valid_greek_phone(data["phone"]):
                warnings.append(
                    ValidationWarning(
                        field="phone",
                        message=f"Invalid Greek phone format: {data['phone']}",
                        severity="warning",
                    )
                )

        # Check for missing critical fields
        if not data.get("email"):
            warnings.append(
                ValidationWarning(
                    field="email",
                    message="Email address not found in message",
                    severity="error",
                )
            )

        if not data.get("client_name"):
            warnings.append(
                ValidationWarning(
                    field="client_name",
                    message="Client name not found in message",
                    severity="warning",
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
