import re
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Dict, List

from app.models.extraction import ValidationWarning
from app.parsers.base import BaseParser
from app.parsers.utils import is_valid_email, is_valid_greek_phone, normalize_date


class EmailParser(BaseParser):
    """Parser for EML email files using Python email library"""

    def parse(self, filepath: Path) -> Dict:
        """
        Parse EML email file and extract headers and body content

        Args:
            filepath: Path to EML file

        Returns:
            Dictionary with extracted fields including headers and body content
        """
        with open(filepath, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        # Extract headers
        from_header = msg.get("From", "")
        subject = msg.get("Subject", "")
        date = msg.get("Date", "")

        # Extract body content
        body = self._extract_body(msg)

        # Parse sender information from From header
        sender_name, sender_email = self._parse_from_header(from_header)

        # Extract structured information from body
        extracted_info = self._extract_info_from_body(body)

        # Combine all extracted data
        data = {
            "client_name": extracted_info.get("name") or sender_name,
            "email": extracted_info.get("email") or sender_email,
            "phone": extracted_info.get("phone"),
            "company": extracted_info.get("company"),
            "service_interest": subject,  # Use subject as service interest
            "message": body,
            "date": date,
            "priority": None,  # Can be inferred from subject keywords if needed
        }

        # Clean up the data
        data = {k: v.strip() if isinstance(v, str) and v else v for k, v in data.items()}

        # Normalize date to YYYY-MM-DD format
        if data.get("date"):
            data["date"] = normalize_date(data["date"])

        return data

    def _extract_body(self, msg) -> str:
        """
        Extract text body from email message

        Args:
            msg: Email message object

        Returns:
            Email body text
        """
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    except Exception:
                        continue
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except Exception:
                body = str(msg.get_payload())

        return body.strip()

    def _parse_from_header(self, from_header: str) -> tuple:
        """
        Parse name and email from From header

        Args:
            from_header: From header string (e.g., "John Doe <john@example.com>")

        Returns:
            Tuple of (name, email)
        """
        # Pattern: Name <email@domain.com>
        match = re.search(r"(.+?)\s*<(.+?)>", from_header)
        if match:
            name = match.group(1).strip()
            email_addr = match.group(2).strip()
            return name, email_addr

        # If no angle brackets, assume it's just an email
        if "@" in from_header:
            return "", from_header.strip()

        return from_header.strip(), ""

    def _extract_info_from_body(self, body: str) -> Dict:
        """
        Extract structured information from email body using pattern matching

        Looks for patterns like:
        - Όνομα: Giannis Mixalis
        - Email: giannis@example.com
        - Τηλέφωνο: 210-1234567
        - Εταιρεία: Company Name

        Args:
            body: Email body text

        Returns:
            Dictionary with extracted information
        """
        info = {}

        # Pattern for name (Greek and English labels)
        name_patterns = [
            r"(?:Όνομα|Name|Ονοματεπώνυμο):\s*(.+?)(?:\n|$)",
            r"(?:Είμαι ο|Είμαι η)\s+(.+?)(?:\s+από|\s+και|$)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
            if match:
                info["name"] = match.group(1).strip()
                break

        # Pattern for email
        email_pattern = r"(?:Email|E-mail):\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
        match = re.search(email_pattern, body, re.IGNORECASE)
        if match:
            info["email"] = match.group(1).strip()

        # Pattern for phone (Greek and English labels)
        phone_patterns = [
            r"(?:Τηλέφωνο|Τηλ|Phone|Tel):\s*([\d\s\-\+\(\)]+?)(?:\n|$)",
            r"(?:Κινητό|Mobile):\s*([\d\s\-\+\(\)]+?)(?:\n|$)",
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
            if match:
                info["phone"] = match.group(1).strip()
                break

        # Pattern for company (Greek and English labels)
        company_patterns = [
            r"(?:Εταιρεία|Εταιρία|Company|Organization):\s*(.+?)(?:\n|$)",
            r"από την\s+(.+?)(?:\s+και|\s+θα|$)",
        ]
        for pattern in company_patterns:
            match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
            if match:
                info["company"] = match.group(1).strip()
                break

        return info

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

        return warnings
