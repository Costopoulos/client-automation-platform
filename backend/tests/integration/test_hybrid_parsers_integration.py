from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.parsers.hybrid import HybridEmailParser, HybridFormParser, HybridInvoiceParser

# Mark all tests in this file as integration tests that require API access
pytestmark = pytest.mark.integration


class TestHybridFormParser:
    """Tests for hybrid form parser"""

    def test_uses_llm_when_confidence_high(self):
        """Test that LLM is used when confidence is above threshold"""
        parser = HybridFormParser()
        filepath = Path("dummy_data/forms/contact_form_1.html")

        data = parser.parse(filepath)

        # Should use LLM (default threshold is 0.7)
        assert data["_extraction_method"] == "llm"
        assert data["_confidence"] >= 0.7
        assert data["client_name"] == "Νίκος Παπαδόπουλος"
        assert data["email"] == "nikos.papadopoulos@example.gr"

    def test_falls_back_to_rules_when_llm_disabled(self):
        """Test fallback to rule-based when LLM is disabled"""
        with patch("app.parsers.hybrid.form_parser.get_settings") as mock_settings:
            settings = Mock()
            settings.use_llm_extraction = False
            settings.llm_confidence_threshold = 0.7
            settings.llm_fallback_to_rules = True
            mock_settings.return_value = settings

            parser = HybridFormParser()
            filepath = Path("dummy_data/forms/contact_form_1.html")

            data = parser.parse(filepath)

            # Should use rule-based
            assert data["_extraction_method"] == "rule-based"
            assert data["_confidence"] is None
            assert data["client_name"] == "Νίκος Παπαδόπουλος"

    def test_falls_back_when_llm_fails(self):
        """Test fallback when LLM extraction raises exception"""
        with patch("app.parsers.hybrid.form_parser.LLMFormParser") as mock_llm:
            mock_llm.return_value.parse.side_effect = Exception("API Error")

            parser = HybridFormParser()
            filepath = Path("dummy_data/forms/contact_form_1.html")

            data = parser.parse(filepath)

            # Should fall back to rule-based
            assert data["_extraction_method"] == "rule-based"
            assert data["client_name"] == "Νίκος Παπαδόπουλος"

    def test_falls_back_when_confidence_too_low(self):
        """Test fallback when LLM confidence is below threshold"""
        # Mock the LLM parser to return low confidence
        with patch("app.parsers.hybrid.form_parser.LLMFormParser") as mock_llm:
            mock_llm.return_value.parse.return_value = {
                "client_name": "Test User",
                "email": "test@example.com",
                "_confidence": 0.5,  # Low confidence
                "_extraction_method": "llm",
            }

            parser = HybridFormParser()
            filepath = Path("dummy_data/forms/contact_form_1.html")

            data = parser.parse(filepath)

            # Should fall back to rule-based due to low confidence
            assert data["_extraction_method"] == "rule-based"
            assert data["client_name"] == "Νίκος Παπαδόπουλος"

    def test_validation_uses_correct_validator(self):
        """Test that validation uses the appropriate validator"""
        parser = HybridFormParser()
        filepath = Path("dummy_data/forms/contact_form_1.html")

        data = parser.parse(filepath)
        warnings = parser.validate(data)

        # Should validate successfully
        assert isinstance(warnings, list)


class TestHybridEmailParser:
    """Tests for hybrid email parser"""

    def test_uses_llm_when_confidence_high(self):
        """Test that LLM is used when confidence is above threshold"""
        parser = HybridEmailParser()
        filepath = Path("dummy_data/emails/email_01.eml")

        data = parser.parse(filepath)

        # Should use LLM
        assert data["_extraction_method"] == "llm"
        assert data["_confidence"] >= 0.7
        assert data["client_name"] == "Σπύρος Μιχαήλ"
        assert data["email"] == "spyros.michail@techcorp.gr"

    def test_falls_back_to_rules_when_llm_disabled(self):
        """Test fallback to rule-based when LLM is disabled"""
        with patch("app.parsers.hybrid.email_parser.get_settings") as mock_settings:
            settings = Mock()
            settings.use_llm_extraction = False
            settings.llm_confidence_threshold = 0.7
            settings.llm_fallback_to_rules = True
            mock_settings.return_value = settings

            parser = HybridEmailParser()
            filepath = Path("dummy_data/emails/email_01.eml")

            data = parser.parse(filepath)

            # Should use rule-based
            assert data["_extraction_method"] == "rule-based"
            assert data["client_name"] == "Σπύρος Μιχαήλ"

    def test_validation_uses_correct_validator(self):
        """Test that validation uses the appropriate validator"""
        parser = HybridEmailParser()
        filepath = Path("dummy_data/emails/email_01.eml")

        data = parser.parse(filepath)
        warnings = parser.validate(data)

        # Should validate successfully
        assert isinstance(warnings, list)

    def test_email_with_invoice_data_llm(self):
        """Test that LLM extracts invoice fields from emails containing invoice data"""
        parser = HybridEmailParser()
        filepath = Path("dummy_data/emails/email_03.eml")

        data = parser.parse(filepath)

        # Should use LLM
        assert data["_extraction_method"] == "llm"
        assert data["_confidence"] >= 0.7

        # Should extract client fields
        assert data["client_name"] is not None
        assert data["email"] is not None

        # Should extract invoice fields
        assert data["invoice_number"] == "TF-2024-001"
        assert data["amount"] == 850.0
        assert data["vat"] == 204.0
        assert data["total_amount"] == 1054.0

    def test_client_email_has_no_invoice_fields(self):
        """Test that regular client emails don't have invoice fields populated"""
        parser = HybridEmailParser()
        filepath = Path("dummy_data/emails/email_01.eml")

        data = parser.parse(filepath)

        # Should have client fields
        assert data["client_name"] is not None
        assert data["email"] is not None

        # Should NOT have invoice fields
        assert data.get("invoice_number") is None
        assert data.get("amount") is None
        assert data.get("vat") is None
        assert data.get("total_amount") is None


class TestHybridInvoiceParser:
    """Tests for hybrid invoice parser"""

    def test_uses_llm_when_confidence_high(self):
        """Test that LLM is used when confidence is above threshold"""
        parser = HybridInvoiceParser()
        filepath = Path("dummy_data/invoices/invoice_TF-2024-001.html")

        data = parser.parse(filepath)

        # Should use LLM
        assert data["_extraction_method"] == "llm"
        assert data["_confidence"] >= 0.7
        assert data["invoice_number"] == "TF-2024-001"
        assert data["client_name"] == "Office Solutions Ltd"

    def test_falls_back_to_rules_when_llm_disabled(self):
        """Test fallback to rule-based when LLM is disabled"""
        with patch("app.parsers.hybrid.invoice_parser.get_settings") as mock_settings:
            settings = Mock()
            settings.use_llm_extraction = False
            settings.llm_confidence_threshold = 0.7
            settings.llm_fallback_to_rules = True
            mock_settings.return_value = settings

            parser = HybridInvoiceParser()
            filepath = Path("dummy_data/invoices/invoice_TF-2024-001.html")

            data = parser.parse(filepath)

            # Should use rule-based
            assert data["_extraction_method"] == "rule-based"
            assert data["invoice_number"] == "TF-2024-001"

    def test_validation_uses_correct_validator(self):
        """Test that validation uses the appropriate validator"""
        parser = HybridInvoiceParser()
        filepath = Path("dummy_data/invoices/invoice_TF-2024-001.html")

        data = parser.parse(filepath)
        warnings = parser.validate(data)

        # Should validate successfully
        assert isinstance(warnings, list)


class TestHybridParserIntegration:
    """Integration tests for all hybrid parsers"""

    def test_all_forms_parse_with_hybrid(self):
        """Test that all forms parse successfully with hybrid parser"""
        parser = HybridFormParser()
        forms_dir = Path("dummy_data/forms")

        llm_count = 0
        rule_count = 0

        for form_file in forms_dir.glob("*.html"):
            data = parser.parse(form_file)
            assert data is not None
            assert "_extraction_method" in data

            if data["_extraction_method"] == "llm":
                llm_count += 1
            elif data["_extraction_method"] == "rule-based":
                rule_count += 1

        print("\n=== Form Parsing Methods ===")
        print(f"LLM: {llm_count}, Rule-based: {rule_count}")

        # Most should use LLM (high quality data)
        assert llm_count > 0

    def test_all_emails_parse_with_hybrid(self):
        """Test that all emails parse successfully with hybrid parser"""
        parser = HybridEmailParser()
        emails_dir = Path("dummy_data/emails")

        llm_count = 0
        rule_count = 0

        for email_file in emails_dir.glob("*.eml"):
            data = parser.parse(email_file)
            assert data is not None
            assert "_extraction_method" in data

            if data["_extraction_method"] == "llm":
                llm_count += 1
            elif data["_extraction_method"] == "rule-based":
                rule_count += 1

        print("\n=== Email Parsing Methods ===")
        print(f"LLM: {llm_count}, Rule-based: {rule_count}")

        # Most should use LLM
        assert llm_count > 0

    def test_all_invoices_parse_with_hybrid(self):
        """Test that all invoices parse successfully with hybrid parser"""
        parser = HybridInvoiceParser()
        invoices_dir = Path("dummy_data/invoices")

        llm_count = 0
        rule_count = 0

        for invoice_file in invoices_dir.glob("*.html"):
            data = parser.parse(invoice_file)
            assert data is not None
            assert "_extraction_method" in data

            if data["_extraction_method"] == "llm":
                llm_count += 1
            elif data["_extraction_method"] == "rule-based":
                rule_count += 1

        print("\n=== Invoice Parsing Methods ===")
        print(f"LLM: {llm_count}, Rule-based: {rule_count}")

        # Most should use LLM
        assert llm_count > 0

    def test_hybrid_performance_comparison(self):
        """Compare extraction quality between LLM and rule-based"""
        import time

        filepath = Path("dummy_data/forms/contact_form_1.html")

        # Test LLM
        parser_llm = HybridFormParser()
        start = time.time()
        data_llm = parser_llm.parse(filepath)
        time_llm = (time.time() - start) * 1000

        # Test rule-based
        with patch("app.parsers.hybrid.form_parser.get_settings") as mock_settings:
            settings = Mock()
            settings.use_llm_extraction = False
            settings.llm_confidence_threshold = 0.7
            settings.llm_fallback_to_rules = True
            mock_settings.return_value = settings

            parser_rule = HybridFormParser()
            start = time.time()
            data_rule = parser_rule.parse(filepath)
            time_rule = (time.time() - start) * 1000

        print("\n=== Performance Comparison ===")
        print(f"LLM: {time_llm:.2f}ms, confidence={data_llm.get('_confidence')}")
        print(f"Rule-based: {time_rule:.2f}ms")
        print(f"\nLLM Message: {data_llm.get('message')}")
        print(f"Rule Message: {data_rule.get('message')}")

        # Both should extract core fields correctly
        assert data_llm["client_name"] == data_rule["client_name"]
        assert data_llm["email"] == data_rule["email"]

        # LLM should have summarized message
        if data_llm.get("message") and data_rule.get("message"):
            assert len(data_llm["message"]) <= len(data_rule["message"])
