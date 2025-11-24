from pathlib import Path
from typing import Dict, List

from app.models.extraction import RecordType, ValidationWarning
from app.parsers.base import BaseParser
from app.parsers.llm_based.extractor import AIExtractor
from app.parsers.utils import is_valid_email, is_valid_greek_phone


class LLMFormParser(BaseParser):
    """LLM-powered parser for HTML contact forms with intelligent extraction"""

    def __init__(self):
        """Initialize with AI extractor"""
        self.extractor = AIExtractor()
        self.schema = {
            "client_name": "Full name of the client",
            "email": "Email address",
            "phone": "Phone number (Greek format)",
            "company": "Company or organization name",
            "service_interest": "Service or product of interest",
            "priority": "Priority level (high, medium, low)",
            "message": "Brief 1-2 sentence summary of the main request or message content",
            "date": "Submission date",
        }

    def parse(self, filepath: Path) -> Dict:
        """
        Parse HTML form using LLM extraction with message summarization

        Args:
            filepath: Path to HTML form file

        Returns:
            Dictionary with extracted and summarized fields
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Use LLM to extract structured data with summarization
        extracted_data, confidence = self.extractor.extract_structured_data(
            content, self.schema, RecordType.FORM
        )

        # Remove field_confidences from the result (internal metadata)
        field_confidences = extracted_data.pop("field_confidences", {})

        # Add confidence as metadata
        extracted_data["_confidence"] = confidence
        extracted_data["_field_confidences"] = field_confidences

        return extracted_data

    def validate(self, data: Dict) -> List[ValidationWarning]:
        """
        Validate extracted form data

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

        # Validate phone format
        if data.get("phone"):
            if not is_valid_greek_phone(data["phone"]):
                warnings.append(
                    ValidationWarning(
                        field="phone",
                        message=f"Invalid Greek phone format: {data['phone']}",
                        severity="warning",
                    )
                )

        # Check for missing required fields
        required_fields = ["client_name", "email"]
        for field in required_fields:
            if not data.get(field):
                warnings.append(
                    ValidationWarning(
                        field=field,
                        message=f"Required field '{field}' is missing",
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
