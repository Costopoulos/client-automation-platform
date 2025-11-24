from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup

from app.models.extraction import ValidationWarning
from app.parsers.base import BaseParser
from app.parsers.utils import is_valid_email, is_valid_greek_phone, normalize_date


class RuleBasedFormParser(BaseParser):
    """Rule-based parser for HTML contact forms using BeautifulSoup4"""

    def parse(self, filepath: Path) -> Dict:
        """
        Parse HTML contact form and extract client contact fields

        Args:
            filepath: Path to HTML form file

        Returns:
            Dictionary with extracted fields: client_name, email, phone,
            company, service_interest, message, date, priority
        """
        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract data from form inputs
        data = {
            "client_name": self._extract_field(soup, ["full_name", "name", "client_name"]),
            "email": self._extract_field(soup, ["email", "email_address"]),
            "phone": self._extract_field(soup, ["phone", "telephone", "tel"]),
            "company": self._extract_field(soup, ["company", "organization", "business"]),
            "service_interest": self._extract_field(
                soup, ["service", "service_interest", "interest"]
            ),
            "message": self._extract_textarea(soup, ["message", "comments", "description"]),
            "date": self._extract_field(
                soup, ["submission_date", "date", "created_at", "timestamp"]
            ),
            "priority": self._extract_field(soup, ["priority", "urgency"]),
        }

        # Clean up the data
        data = {k: v.strip() if v else None for k, v in data.items()}

        # Normalize date to YYYY-MM-DD format
        if data.get("date"):
            data["date"] = normalize_date(data["date"])

        return data

    def _extract_field(self, soup: BeautifulSoup, field_names: List[str]) -> str:
        """
        Extract field value from input or select elements

        Args:
            soup: BeautifulSoup object
            field_names: List of possible field names to search for

        Returns:
            Extracted value or empty string
        """
        for name in field_names:
            # Try input fields
            input_elem = soup.find("input", {"name": name})
            if input_elem and input_elem.get("value"):
                return input_elem.get("value")

            # Try select fields (get selected option)
            select_elem = soup.find("select", {"name": name})
            if select_elem:
                selected = select_elem.find("option", {"selected": True})
                if selected:
                    # Return the text content or value
                    return selected.get_text(strip=True) or selected.get("value", "")

        return ""

    def _extract_textarea(self, soup: BeautifulSoup, field_names: List[str]) -> str:
        """
        Extract value from textarea elements

        Args:
            soup: BeautifulSoup object
            field_names: List of possible field names to search for

        Returns:
            Extracted text or empty string
        """
        for name in field_names:
            textarea = soup.find("textarea", {"name": name})
            if textarea:
                return textarea.get_text(strip=True)

        return ""

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

        # Validate phone format (Greek phone numbers)
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

        return warnings


# Keep backward compatibility alias
FormParser = RuleBasedFormParser
