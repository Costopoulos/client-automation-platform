import re
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from app.models.extraction import ValidationWarning
from app.parsers.base import BaseParser
from app.parsers.utils import normalize_date


class InvoiceParser(BaseParser):
    """Parser for HTML invoices using BeautifulSoup4"""

    def parse(self, filepath: Path) -> Dict:
        """
        Parse HTML invoice and extract financial data

        Args:
            filepath: Path to HTML invoice file

        Returns:
            Dictionary with extracted fields: invoice_number, date, client_name,
            amount, vat, total_amount
        """
        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract invoice number
        invoice_number = self._extract_invoice_number(soup)

        # Extract date
        date = self._extract_date(soup)

        # Extract client name
        client_name = self._extract_client_name(soup)

        # Extract financial amounts
        amount, vat, total_amount = self._extract_amounts(soup)

        data = {
            "invoice_number": invoice_number,
            "date": normalize_date(date) if date else None,
            "client_name": client_name,
            "amount": amount,
            "vat": vat,
            "total_amount": total_amount,
        }

        return data

    def _extract_invoice_number(self, soup: BeautifulSoup) -> str:
        """
        Extract invoice number from HTML

        Looks for patterns like "TF-2024-001" or "Αριθμός: TF-2024-001"

        Args:
            soup: BeautifulSoup object

        Returns:
            Invoice number or empty string
        """
        # Search in text content
        text = soup.get_text()

        # Pattern for invoice number (TF-YYYY-NNN)
        pattern = r"TF-\d{4}-\d{3,}"
        match = re.search(pattern, text)
        if match:
            return match.group(0)

        # Try to find in specific elements
        for tag in soup.find_all(["div", "span", "strong", "td"]):
            text = tag.get_text(strip=True)
            if "Αριθμός:" in text or "Number:" in text:
                match = re.search(pattern, text)
                if match:
                    return match.group(0)

        return ""

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """
        Extract invoice date from HTML

        Args:
            soup: BeautifulSoup object

        Returns:
            Date string or empty string
        """
        # Look for date patterns
        text = soup.get_text()

        # Pattern for Greek date format (DD/MM/YYYY)
        date_pattern = r"\d{1,2}/\d{1,2}/\d{4}"
        match = re.search(date_pattern, text)
        if match:
            return match.group(0)

        # Try to find in specific elements with date labels
        for tag in soup.find_all(["div", "span", "strong", "td"]):
            text = tag.get_text(strip=True)
            if "Ημερομηνία:" in text or "Date:" in text:
                match = re.search(date_pattern, text)
                if match:
                    return match.group(0)

        return ""

    def _extract_client_name(self, soup: BeautifulSoup) -> str:
        """
        Extract client name from invoice

        Args:
            soup: BeautifulSoup object

        Returns:
            Client name or empty string
        """
        # Look for client/customer section
        text = soup.get_text()

        # Find section with "Πελάτης:" or "Customer:"
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "Πελάτης:" in line or "Customer:" in line:
                # The next non-empty line is likely the client name
                for j in range(i + 1, min(i + 5, len(lines))):
                    candidate = lines[j].strip()
                    if (
                        candidate
                        and not candidate.startswith("Βας.")
                        and not candidate.startswith("ΑΦΜ")
                    ):
                        return candidate

        return ""

    def _extract_amounts(self, soup: BeautifulSoup) -> tuple:
        """
        Extract financial amounts (base amount, VAT, total)

        Args:
            soup: BeautifulSoup object

        Returns:
            Tuple of (amount, vat, total_amount) as floats
        """
        amount = None
        vat = None
        total_amount = None

        # Look for summary table or section - check both table rows and div text
        # First try to find in table structure
        for row in soup.find_all("tr"):
            row_text = row.get_text()

            # Extract base amount (Καθαρή Αξία)
            if "Καθαρή Αξία" in row_text or "Subtotal" in row_text or "Net Amount" in row_text:
                amount = self._extract_currency_value(row_text)

            # Extract VAT (ΦΠΑ)
            if "ΦΠΑ" in row_text and "Καθαρή" not in row_text:
                vat = self._extract_currency_value(row_text)

            # Extract total (ΣΥΝΟΛΟ)
            if "ΣΥΝΟΛΟ" in row_text or "TOTAL" in row_text.upper():
                total_amount = self._extract_currency_value(row_text)

        # If not found in tables, try text-based extraction
        if amount is None or vat is None or total_amount is None:
            text = soup.get_text()
            lines = text.split("\n")

            for line in lines:
                line = line.strip()

                # Extract base amount (Καθαρή Αξία)
                if amount is None and (
                    "Καθαρή Αξία" in line or "Subtotal" in line or "Net Amount" in line
                ):
                    amount = self._extract_currency_value(line)

                # Extract VAT (ΦΠΑ)
                if vat is None and "ΦΠΑ" in line:
                    vat = self._extract_currency_value(line)

                # Extract total (ΣΥΝΟΛΟ)
                if total_amount is None and ("ΣΥΝΟΛΟ" in line or "Total" in line.upper()):
                    total_amount = self._extract_currency_value(line)

        return amount, vat, total_amount

    def _extract_currency_value(self, text: str) -> Optional[float]:
        """
        Extract currency value from text

        Handles formats like:
        - €1,054.00
        - 1.054,00€
        - 1054.00
        - €850.00

        Args:
            text: Text containing currency value

        Returns:
            Float value or None
        """
        # Remove currency symbols, spaces, and strong tags
        cleaned = text.replace("€", "").replace(" ", "").replace("*", "")

        # Pattern for numbers with optional thousands separator and decimal
        # Handles both 1,054.00 and 1.054,00 formats
        patterns = [
            r"(\d{1,3}(?:,\d{3})+\.\d{2})",  # 1,054.00 format (with thousands separator)
            r"(\d{1,3}(?:\.\d{3})+,\d{2})",  # 1.054,00 format (with thousands separator)
            r"(\d+\.\d{2})",  # Simple decimal format like 850.00
            r"(\d+,\d{2})",  # Simple comma format like 850,00
        ]

        for pattern in patterns:
            match = re.search(pattern, cleaned)
            if match:
                value_str = match.group(1)
                # Normalize to standard format
                if "," in value_str and "." in value_str:
                    # Determine which is thousands separator
                    if value_str.index(",") < value_str.index("."):
                        # 1,054.00 format
                        value_str = value_str.replace(",", "")
                    else:
                        # 1.054,00 format
                        value_str = value_str.replace(".", "").replace(",", ".")
                elif "," in value_str:
                    # Only comma - assume it's decimal separator
                    value_str = value_str.replace(",", ".")

                try:
                    return float(value_str)
                except ValueError:
                    continue

        return None

    def validate(self, data: Dict) -> List[ValidationWarning]:
        """
        Validate extracted invoice data

        Args:
            data: Dictionary of extracted data

        Returns:
            List of validation warnings
        """
        warnings = []

        # Validate invoice number format
        if data.get("invoice_number"):
            if not re.match(r"TF-\d{4}-\d{3,}", data["invoice_number"]):
                warnings.append(
                    ValidationWarning(
                        field="invoice_number",
                        message=f"Invoice number format doesn't match expected pattern TF-YYYY-NNN: {data['invoice_number']}",
                        severity="warning",
                    )
                )
        else:
            warnings.append(
                ValidationWarning(
                    field="invoice_number",
                    message="Invoice number not found",
                    severity="error",
                )
            )

        # Validate financial calculations
        amount = data.get("amount")
        vat = data.get("vat")
        total_amount = data.get("total_amount")

        if amount is not None and vat is not None and total_amount is not None:
            # Check if VAT is 24% of amount
            expected_vat = round(amount * 0.24, 2)
            if abs(vat - expected_vat) > 0.02:  # Allow 2 cent tolerance for rounding
                warnings.append(
                    ValidationWarning(
                        field="vat",
                        message=f"VAT amount {vat}€ doesn't equal 24% of base amount {amount}€ (expected {expected_vat}€)",
                        severity="error",
                    )
                )

            # Check if total equals amount + VAT
            expected_total = round(amount + vat, 2)
            if abs(total_amount - expected_total) > 0.02:  # Allow 2 cent tolerance
                warnings.append(
                    ValidationWarning(
                        field="total_amount",
                        message=f"Total amount {total_amount}€ doesn't equal base + VAT (expected {expected_total}€)",
                        severity="error",
                    )
                )
        else:
            # Missing financial data
            if amount is None:
                warnings.append(
                    ValidationWarning(
                        field="amount",
                        message="Base amount not found",
                        severity="error",
                    )
                )
            if vat is None:
                warnings.append(
                    ValidationWarning(
                        field="vat",
                        message="VAT amount not found",
                        severity="error",
                    )
                )
            if total_amount is None:
                warnings.append(
                    ValidationWarning(
                        field="total_amount",
                        message="Total amount not found",
                        severity="error",
                    )
                )

        # Check for missing client name
        if not data.get("client_name"):
            warnings.append(
                ValidationWarning(
                    field="client_name",
                    message="Client name not found",
                    severity="warning",
                )
            )

        # Check for missing date
        if not data.get("date"):
            warnings.append(
                ValidationWarning(
                    field="date",
                    message="Invoice date not found",
                    severity="warning",
                )
            )

        return warnings
