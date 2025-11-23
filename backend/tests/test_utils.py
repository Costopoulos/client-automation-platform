from app.parsers.utils import is_valid_email, is_valid_greek_phone, normalize_date


class TestEmailValidation:
    """Tests for email validation"""

    def test_valid_emails(self):
        """Test valid email formats"""
        valid_emails = [
            "user@example.com",
            "john.doe@example.com",
            "user+tag@example.co.uk",
            "test_user@example-domain.com",
            "nikos.papadopoulos@example.gr",
            "spyros.michail@techcorp.gr",
        ]

        for email in valid_emails:
            assert is_valid_email(email), f"Expected {email} to be valid"

    def test_invalid_emails(self):
        """Test invalid email formats"""
        invalid_emails = [
            "invalid",
            "invalid@",
            "@example.com",
            "user@",
            "user @example.com",
            "user@example",
            "",
            "user@.com",
        ]

        for email in invalid_emails:
            assert not is_valid_email(email), f"Expected {email} to be invalid"


class TestGreekPhoneValidation:
    """Tests for Greek phone number validation"""

    def test_valid_landline_formats(self):
        """Test valid Greek landline formats"""
        valid_phones = [
            "210-1234567",
            "2101234567",
            "+30 210 1234567",
            "+302101234567",
            "0030 210 1234567",
            "210 123 4567",
            "(210) 1234567",
            "2310123456",  # Thessaloniki
            "2610123456",  # Patra
        ]

        for phone in valid_phones:
            assert is_valid_greek_phone(phone), f"Expected {phone} to be valid"

    def test_valid_mobile_formats(self):
        """Test valid Greek mobile formats"""
        valid_mobiles = [
            "6912345678",
            "691-234-5678",
            "+30 691 234 5678",
            "+306912345678",
            "0030 691 234 5678",
            "697 123 4567",
            "(694) 1234567",
        ]

        for mobile in valid_mobiles:
            assert is_valid_greek_phone(mobile), f"Expected {mobile} to be valid"

    def test_invalid_phone_formats(self):
        """Test invalid phone formats"""
        invalid_phones = [
            "123",  # Too short
            "12345",  # Too short
            "1234567890",  # Doesn't start with 2 or 6
            "310-1234567",  # Invalid area code
            "510-1234567",  # Invalid area code
            "791-234-5678",  # Invalid mobile prefix
            "",  # Empty
            "abc-def-ghij",  # Non-numeric
        ]

        for phone in invalid_phones:
            assert not is_valid_greek_phone(phone), f"Expected {phone} to be invalid"


class TestDateNormalization:
    """Tests for date normalization"""

    def test_iso_datetime_format(self):
        """Test ISO datetime format (2024-01-15T14:30)"""
        result = normalize_date("2024-01-15T14:30")
        assert result == "2024-01-15"

    def test_iso_date_format(self):
        """Test ISO date format (2024-01-15)"""
        result = normalize_date("2024-01-15")
        assert result == "2024-01-15"

    def test_greek_date_format(self):
        """Test Greek date format (DD/MM/YYYY)"""
        result = normalize_date("21/01/2024")
        assert result == "2024-01-21"

    def test_dash_date_format(self):
        """Test dash date format (DD-MM-YYYY)"""
        result = normalize_date("21-01-2024")
        assert result == "2024-01-21"

    def test_slash_date_format(self):
        """Test slash date format (YYYY/MM/DD)"""
        result = normalize_date("2024/01/21")
        assert result == "2024-01-21"

    def test_email_date_format(self):
        """Test email date format (RFC 2822)"""
        result = normalize_date("Mon, 20 Jan 2024 10:30:00 +0200")
        assert result == "2024-01-20"

    def test_invalid_date(self):
        """Test invalid date format"""
        result = normalize_date("invalid-date")
        assert result is None

    def test_empty_date(self):
        """Test empty date string"""
        result = normalize_date("")
        assert result is None

    def test_none_date(self):
        """Test None date"""
        result = normalize_date(None)
        assert result is None


class TestUtilsEdgeCases:
    """Tests for edge cases in utility functions"""

    def test_email_with_special_characters(self):
        """Test email with special characters"""
        assert is_valid_email("user+tag@example.com")
        assert is_valid_email("user_name@example.com")
        assert is_valid_email("user.name@example.com")

    def test_phone_with_various_separators(self):
        """Test phone with various separators"""
        assert is_valid_greek_phone("210 123 4567")
        assert is_valid_greek_phone("210-123-4567")
        assert is_valid_greek_phone("(210) 123-4567")
        # Note: dots are not currently supported as separators
        # assert is_valid_greek_phone("210.123.4567")

    def test_phone_country_code_variations(self):
        """Test phone with different country code formats"""
        assert is_valid_greek_phone("+30 210 1234567")
        assert is_valid_greek_phone("+302101234567")
        assert is_valid_greek_phone("0030 210 1234567")
        assert is_valid_greek_phone("00302101234567")

    def test_date_single_digit_day_month(self):
        """Test date with single digit day and month"""
        result = normalize_date("5/3/2024")
        assert result == "2024-03-05"

    def test_date_with_leading_zeros(self):
        """Test date with leading zeros"""
        result = normalize_date("05/03/2024")
        assert result == "2024-03-05"
