from pathlib import Path

from app.parsers import RuleBasedEmailParser, RuleBasedFormParser, RuleBasedInvoiceParser


class TestRuleBasedFormParser:
    """Tests for rule-based form parser"""

    def test_parse_contact_form_1(self):
        """Test parsing contact form 1"""
        parser = RuleBasedFormParser()
        filepath = Path("dummy_data/forms/contact_form_1.html")

        data = parser.parse(filepath)

        assert data["client_name"] == "Νίκος Παπαδόπουλος"
        assert data["email"] == "nikos.papadopoulos@example.gr"
        assert data["phone"] == "210-1234567"
        assert data["company"] == "Digital Marketing Pro"
        assert data["service_interest"] == "Ανάπτυξη Website"
        assert data["priority"] == "Υψηλή"
        assert data["message"] is not None
        assert len(data["message"]) > 0

    def test_validate_valid_form_data(self):
        """Test validation with valid form data"""
        parser = RuleBasedFormParser()
        data = {
            "client_name": "John Doe",
            "email": "john@example.com",
            "phone": "210-1234567",
            "company": "Test Company",
        }

        warnings = parser.validate(data)

        assert len(warnings) == 0

    def test_validate_invalid_email(self):
        """Test validation with invalid email"""
        parser = RuleBasedFormParser()
        data = {
            "client_name": "John Doe",
            "email": "invalid-email",
            "phone": "210-1234567",
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "email" for w in warnings)
        assert any(w.severity == "error" for w in warnings)

    def test_validate_invalid_phone(self):
        """Test validation with invalid phone number"""
        parser = RuleBasedFormParser()
        data = {
            "client_name": "John Doe",
            "email": "john@example.com",
            "phone": "123",  # Invalid phone
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "phone" for w in warnings)

    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields"""
        parser = RuleBasedFormParser()
        data = {
            "company": "Test Company",
        }

        warnings = parser.validate(data)

        assert len(warnings) >= 2  # Missing client_name and email
        assert any(w.field == "client_name" for w in warnings)
        assert any(w.field == "email" for w in warnings)


class TestRuleBasedEmailParser:
    """Tests for rule-based email parser"""

    def test_parse_email_01(self):
        """Test parsing email 01"""
        parser = RuleBasedEmailParser()
        filepath = Path("dummy_data/emails/email_01.eml")

        data = parser.parse(filepath)

        assert data["client_name"] == "Σπύρος Μιχαήλ"
        assert data["email"] == "spyros.michail@techcorp.gr"
        assert data["phone"] == "210-3344556"
        assert data["company"] == "TechCorp AE"
        assert data["service_interest"] == "Αίτημα για Σύστημα CRM"
        assert data["message"] is not None
        assert len(data["message"]) > 0

    def test_validate_valid_email_data(self):
        """Test validation with valid email data"""
        parser = RuleBasedEmailParser()
        data = {
            "client_name": "John Doe",
            "email": "john@example.com",
            "phone": "6912345678",
            "company": "Test Company",
        }

        warnings = parser.validate(data)

        assert len(warnings) == 0

    def test_validate_missing_email(self):
        """Test validation with missing email"""
        parser = RuleBasedEmailParser()
        data = {
            "client_name": "John Doe",
            "phone": "210-1234567",
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "email" for w in warnings)
        assert any(w.severity == "error" for w in warnings)

    def test_validate_invalid_email_format(self):
        """Test validation with invalid email format"""
        parser = RuleBasedEmailParser()
        data = {
            "client_name": "John Doe",
            "email": "not-an-email",
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "email" for w in warnings)


class TestRuleBasedInvoiceParser:
    """Tests for rule-based invoice parser"""

    def test_parse_invoice_001(self):
        """Test parsing invoice TF-2024-001"""
        parser = RuleBasedInvoiceParser()
        filepath = Path("dummy_data/invoices/invoice_TF-2024-001.html")

        data = parser.parse(filepath)

        assert data["invoice_number"] == "TF-2024-001"
        assert data["date"] == "2024-01-21"  # Date is normalized to ISO format
        assert data["client_name"] == "Office Solutions Ltd"
        assert data["amount"] == 850.0
        assert data["vat"] == 204.0
        assert data["total_amount"] == 1054.0

    def test_validate_valid_invoice_data(self):
        """Test validation with valid invoice data"""
        parser = RuleBasedInvoiceParser()
        data = {
            "invoice_number": "TF-2024-001",
            "date": "21/01/2024",
            "client_name": "Test Client",
            "amount": 1000.0,
            "vat": 240.0,
            "total_amount": 1240.0,
        }

        warnings = parser.validate(data)

        assert len(warnings) == 0

    def test_validate_incorrect_vat_calculation(self):
        """Test validation with incorrect VAT calculation"""
        parser = RuleBasedInvoiceParser()
        data = {
            "invoice_number": "TF-2024-001",
            "date": "21/01/2024",
            "client_name": "Test Client",
            "amount": 1000.0,
            "vat": 200.0,  # Should be 240.0 (24%)
            "total_amount": 1200.0,
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "vat" for w in warnings)
        assert any("24%" in w.message for w in warnings)

    def test_validate_incorrect_total_calculation(self):
        """Test validation with incorrect total calculation"""
        parser = RuleBasedInvoiceParser()
        data = {
            "invoice_number": "TF-2024-001",
            "date": "21/01/2024",
            "client_name": "Test Client",
            "amount": 1000.0,
            "vat": 240.0,
            "total_amount": 1300.0,  # Should be 1240.0
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "total_amount" for w in warnings)

    def test_validate_missing_invoice_number(self):
        """Test validation with missing invoice number"""
        parser = RuleBasedInvoiceParser()
        data = {
            "date": "21/01/2024",
            "client_name": "Test Client",
            "amount": 1000.0,
            "vat": 240.0,
            "total_amount": 1240.0,
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "invoice_number" for w in warnings)

    def test_validate_invalid_invoice_number_format(self):
        """Test validation with invalid invoice number format"""
        parser = RuleBasedInvoiceParser()
        data = {
            "invoice_number": "INVALID-123",
            "date": "21/01/2024",
            "client_name": "Test Client",
            "amount": 1000.0,
            "vat": 240.0,
            "total_amount": 1240.0,
        }

        warnings = parser.validate(data)

        assert len(warnings) > 0
        assert any(w.field == "invoice_number" for w in warnings)

    def test_validate_missing_financial_data(self):
        """Test validation with missing financial data"""
        parser = RuleBasedInvoiceParser()
        data = {
            "invoice_number": "TF-2024-001",
            "date": "21/01/2024",
            "client_name": "Test Client",
        }

        warnings = parser.validate(data)

        assert len(warnings) >= 3  # Missing amount, vat, total_amount
        assert any(w.field == "amount" for w in warnings)
        assert any(w.field == "vat" for w in warnings)
        assert any(w.field == "total_amount" for w in warnings)


class TestRuleBasedParserIntegration:
    """Integration tests for all rule-based parsers"""

    def test_all_forms_parse_without_errors(self):
        """Test that all form files can be parsed without errors"""
        parser = RuleBasedFormParser()
        forms_dir = Path("dummy_data/forms")

        for form_file in forms_dir.glob("*.html"):
            data = parser.parse(form_file)
            assert data is not None
            assert isinstance(data, dict)

    def test_all_emails_parse_without_errors(self):
        """Test that all email files can be parsed without errors"""
        parser = RuleBasedEmailParser()
        emails_dir = Path("dummy_data/emails")

        for email_file in emails_dir.glob("*.eml"):
            data = parser.parse(email_file)
            assert data is not None
            assert isinstance(data, dict)

    def test_all_invoices_parse_without_errors(self):
        """Test that all invoice files can be parsed without errors"""
        parser = RuleBasedInvoiceParser()
        invoices_dir = Path("dummy_data/invoices")

        for invoice_file in invoices_dir.glob("*.html"):
            data = parser.parse(invoice_file)
            assert data is not None
            assert isinstance(data, dict)
