import re
from datetime import datetime
from typing import Optional


def is_valid_email(email: str) -> bool:
    """
    Validate email format using regex

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_greek_phone(phone: str) -> bool:
    """
    Validate Greek phone number format

    Accepts formats like:
    - 210-1234567
    - 2101234567
    - +30 210 1234567
    - 6912345678 (mobile)

    Args:
        phone: Phone number to validate

    Returns:
        True if valid, False otherwise
    """
    # Remove spaces, dashes, and parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)

    # Remove +30 country code if present
    if cleaned.startswith("+30"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("0030"):
        cleaned = cleaned[4:]

    # Greek landline: 10 digits starting with 2
    # Greek mobile: 10 digits starting with 6
    pattern = r"^[26]\d{9}$"
    return bool(re.match(pattern, cleaned))


def normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize various date formats to YYYY-MM-DD

    Handles formats like:
    - 2024-01-15T14:30
    - 21/01/2024
    - Sat, 20 Jan 2024 10:30:00 +0200
    - 15-01-2024

    Args:
        date_str: Date string in various formats

    Returns:
        Date in YYYY-MM-DD format or None if parsing fails
    """
    if not date_str:
        return None

    # Try different date formats
    formats = [
        "%Y-%m-%dT%H:%M",  # 2024-01-15T14:30
        "%Y-%m-%d",  # 2024-01-15
        "%d/%m/%Y",  # 21/01/2024
        "%d-%m-%Y",  # 21-01-2024
        "%Y/%m/%d",  # 2024/01/21
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try parsing email date format (RFC 2822)
    # Example: Sat, 20 Jan 2024 10:30:00 +0200
    try:
        # Remove timezone info for simpler parsing
        date_part = re.sub(r"\s*[+-]\d{4}$", "", date_str)
        dt = datetime.strptime(date_part, "%a, %d %b %Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    # If all parsing fails, return None
    return None
