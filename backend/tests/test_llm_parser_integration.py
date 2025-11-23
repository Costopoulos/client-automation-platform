from pathlib import Path

import pytest

from app.models.extraction import RecordType
from app.parsers.llm_based.extractor import AIExtractor

# Mark all tests in this file as integration tests that require API access
pytestmark = pytest.mark.integration


@pytest.fixture
def ai_extractor():
    """Create AIExtractor instance for testing"""
    return AIExtractor()


class TestLLMFormExtraction:
    """Integration tests for LLM-based form extraction"""

    def test_extract_contact_form_1(self, ai_extractor):
        """Test LLM extraction on contact form 1"""
        filepath = Path("dummy_data/forms/contact_form_1.html")
        content = filepath.read_text(encoding="utf-8")

        schema = {
            "client_name": "Full name of the client",
            "email": "Email address",
            "phone": "Phone number",
            "company": "Company name",
            "service_interest": "Service of interest",
            "priority": "Priority level",
            "message": "Message content",
        }

        data, confidence = ai_extractor.extract_structured_data(content, schema, RecordType.FORM)

        # Verify extracted data
        assert data["client_name"] == "Νίκος Παπαδόπουλος"
        assert data["email"] == "nikos.papadopoulos@example.gr"
        assert data["phone"] == "210-1234567"
        assert data["company"] == "Digital Marketing Pro"
        assert data["service_interest"] == "Ανάπτυξη Website"
        assert data["priority"] == "Υψηλή"
        assert data["message"] is not None
        assert len(data["message"]) > 0

        # Verify confidence
        assert confidence >= 0.7, f"Confidence too low: {confidence}"
        assert "field_confidences" in data

    def test_extract_all_forms(self, ai_extractor):
        """Test LLM extraction on all form files"""
        forms_dir = Path("dummy_data/forms")
        schema = {
            "client_name": "Full name of the client",
            "email": "Email address",
            "phone": "Phone number",
            "company": "Company name",
            "service_interest": "Service of interest",
            "priority": "Priority level",
            "message": "Message content",
        }

        results = []
        for form_file in sorted(forms_dir.glob("*.html")):
            content = form_file.read_text(encoding="utf-8")
            data, confidence = ai_extractor.extract_structured_data(
                content, schema, RecordType.FORM
            )

            results.append(
                {
                    "file": form_file.name,
                    "data": data,
                    "confidence": confidence,
                }
            )

            # Basic assertions for all forms
            assert data is not None
            assert isinstance(data, dict)
            assert confidence >= 0.5, f"Low confidence for {form_file.name}: {confidence}"

            # Verify required fields are present
            assert "client_name" in data
            assert "email" in data
            assert "field_confidences" in data

        # Should have processed all 5 forms
        assert len(results) == 5

        # Print summary for manual review
        print("\n=== Form Extraction Results ===")
        for result in results:
            print(f"\n{result['file']}: confidence={result['confidence']:.2f}")
            print(f"  Name: {result['data'].get('client_name')}")
            print(f"  Email: {result['data'].get('email')}")
            print(f"  Company: {result['data'].get('company')}")


class TestLLMEmailExtraction:
    """Integration tests for LLM-based email extraction"""

    def test_extract_email_01(self, ai_extractor):
        """Test LLM extraction on email 01"""
        filepath = Path("dummy_data/emails/email_01.eml")
        content = filepath.read_text(encoding="utf-8")

        schema = {
            "client_name": "Full name of the client",
            "email": "Email address",
            "phone": "Phone number",
            "company": "Company name",
            "service_interest": "Service or subject of interest",
            "message": "Message body content",
        }

        data, confidence = ai_extractor.extract_structured_data(content, schema, RecordType.EMAIL)

        # Verify extracted data
        assert data["client_name"] == "Σπύρος Μιχαήλ"
        assert data["email"] == "spyros.michail@techcorp.gr"
        assert data["phone"] == "210-3344556"
        assert data["company"] == "TechCorp AE"
        assert "CRM" in data["service_interest"]
        assert data["message"] is not None

        # Verify confidence
        assert confidence >= 0.7, f"Confidence too low: {confidence}"

    def test_extract_all_emails(self, ai_extractor):
        """Test LLM extraction on all email files"""
        emails_dir = Path("dummy_data/emails")
        schema = {
            "client_name": "Full name of the client",
            "email": "Email address",
            "phone": "Phone number",
            "company": "Company name",
            "service_interest": "Service or subject of interest",
            "message": "Message body content",
        }

        results = []
        for email_file in sorted(emails_dir.glob("*.eml")):
            content = email_file.read_text(encoding="utf-8")
            data, confidence = ai_extractor.extract_structured_data(
                content, schema, RecordType.EMAIL
            )

            results.append(
                {
                    "file": email_file.name,
                    "data": data,
                    "confidence": confidence,
                }
            )

            # Basic assertions for all emails
            assert data is not None
            assert isinstance(data, dict)
            assert confidence >= 0.5, f"Low confidence for {email_file.name}: {confidence}"

            # Verify required fields are present
            assert "email" in data
            assert "field_confidences" in data

        # Should have processed all 10 emails
        assert len(results) == 10

        # Print summary for manual review
        print("\n=== Email Extraction Results ===")
        for result in results:
            print(f"\n{result['file']}: confidence={result['confidence']:.2f}")
            print(f"  Name: {result['data'].get('client_name')}")
            print(f"  Email: {result['data'].get('email')}")
            print(f"  Company: {result['data'].get('company')}")


class TestLLMInvoiceExtraction:
    """Integration tests for LLM-based invoice extraction"""

    def test_extract_invoice_001(self, ai_extractor):
        """Test LLM extraction on invoice TF-2024-001"""
        filepath = Path("dummy_data/invoices/invoice_TF-2024-001.html")
        content = filepath.read_text(encoding="utf-8")

        schema = {
            "invoice_number": "Invoice number (format: TF-YYYY-NNN)",
            "date": "Invoice date",
            "client_name": "Client name",
            "amount": "Base amount (number)",
            "vat": "VAT amount (number)",
            "total_amount": "Total amount (number)",
        }

        data, confidence = ai_extractor.extract_structured_data(content, schema, RecordType.INVOICE)

        # Verify extracted data
        assert data["invoice_number"] == "TF-2024-001"
        assert data["client_name"] == "Office Solutions Ltd"
        assert data["amount"] == 850.0 or data["amount"] == "850.0"
        assert data["vat"] == 204.0 or data["vat"] == "204.0"
        assert data["total_amount"] == 1054.0 or data["total_amount"] == "1054.0"

        # Verify confidence
        assert confidence >= 0.7, f"Confidence too low: {confidence}"

    def test_extract_all_invoices(self, ai_extractor):
        """Test LLM extraction on all invoice files"""
        invoices_dir = Path("dummy_data/invoices")
        schema = {
            "invoice_number": "Invoice number (format: TF-YYYY-NNN)",
            "date": "Invoice date",
            "client_name": "Client name",
            "amount": "Base amount (number)",
            "vat": "VAT amount (number)",
            "total_amount": "Total amount (number)",
        }

        results = []
        for invoice_file in sorted(invoices_dir.glob("*.html")):
            content = invoice_file.read_text(encoding="utf-8")
            data, confidence = ai_extractor.extract_structured_data(
                content, schema, RecordType.INVOICE
            )

            results.append(
                {
                    "file": invoice_file.name,
                    "data": data,
                    "confidence": confidence,
                }
            )

            # Basic assertions for all invoices
            assert data is not None
            assert isinstance(data, dict)
            assert confidence >= 0.5, f"Low confidence for {invoice_file.name}: {confidence}"

            # Verify required fields are present
            assert "invoice_number" in data
            assert "client_name" in data
            assert "field_confidences" in data

        # Should have processed all 10 invoices
        assert len(results) == 10

        # Print summary for manual review
        print("\n=== Invoice Extraction Results ===")
        for result in results:
            print(f"\n{result['file']}: confidence={result['confidence']:.2f}")
            print(f"  Invoice: {result['data'].get('invoice_number')}")
            print(f"  Client: {result['data'].get('client_name')}")
            print(f"  Amount: {result['data'].get('amount')}")
            print(f"  VAT: {result['data'].get('vat')}")
            print(f"  Total: {result['data'].get('total_amount')}")


class TestLLMExtractionQuality:
    """Tests for LLM extraction quality and accuracy"""

    def test_confidence_scores_are_reasonable(self, ai_extractor):
        """Test that confidence scores are in reasonable ranges"""
        # Test with a clear, well-structured form
        filepath = Path("dummy_data/forms/contact_form_1.html")
        content = filepath.read_text(encoding="utf-8")

        schema = {
            "client_name": "Full name",
            "email": "Email address",
            "phone": "Phone number",
        }

        data, confidence = ai_extractor.extract_structured_data(content, schema, RecordType.FORM)

        # Well-structured documents should have high confidence
        assert confidence >= 0.8, f"Expected high confidence for clear form, got {confidence}"

        # Individual field confidences should also be high
        field_confidences = data.get("field_confidences", {})
        for field, conf in field_confidences.items():
            if data.get(field) is not None:
                assert conf >= 0.7, f"Low confidence for field {field}: {conf}"

    def test_handles_missing_fields_gracefully(self, ai_extractor):
        """Test that LLM handles missing fields with appropriate confidence"""
        # Create minimal content
        content = "<html><body><p>Name: John Doe</p></body></html>"

        schema = {
            "client_name": "Full name",
            "email": "Email address",
            "phone": "Phone number",
            "company": "Company name",
        }

        data, confidence = ai_extractor.extract_structured_data(content, schema, RecordType.FORM)

        # Should extract name but not other fields
        assert data["client_name"] is not None
        assert data["email"] is None or data["email"] == ""
        assert data["phone"] is None or data["phone"] == ""

        # Confidence should be lower due to missing fields
        assert confidence < 0.8, f"Expected lower confidence for incomplete data, got {confidence}"

    def test_field_confidences_match_data_quality(self, ai_extractor):
        """Test that field-level confidences reflect data quality"""
        filepath = Path("dummy_data/forms/contact_form_1.html")
        content = filepath.read_text(encoding="utf-8")

        schema = {
            "client_name": "Full name",
            "email": "Email address",
            "phone": "Phone number",
        }

        data, confidence = ai_extractor.extract_structured_data(content, schema, RecordType.FORM)

        field_confidences = data.get("field_confidences", {})

        # Fields with values should have higher confidence than null fields
        for field_name in schema.keys():
            if data.get(field_name) is not None:
                assert field_confidences.get(field_name, 0) > 0.5, (
                    f"Field {field_name} has value but low confidence"
                )
