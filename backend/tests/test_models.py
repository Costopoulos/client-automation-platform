from datetime import datetime

import pytest

from app.models import (
    ApprovalResult,
    ExtractionRecord,
    ExtractionStatus,
    RecordType,
    ScanResult,
    ValidationWarning,
)


def test_record_type_enum():
    """Test RecordType enum values"""
    assert RecordType.FORM == "FORM"
    assert RecordType.EMAIL == "EMAIL"
    assert RecordType.INVOICE == "INVOICE"


def test_extraction_status_enum():
    """Test ExtractionStatus enum values"""
    assert ExtractionStatus.PENDING == "pending"
    assert ExtractionStatus.APPROVED == "approved"
    assert ExtractionStatus.REJECTED == "rejected"


def test_validation_warning_creation():
    """Test ValidationWarning model creation"""
    warning = ValidationWarning(field="email", message="Invalid email format", severity="warning")
    assert warning.field == "email"
    assert warning.message == "Invalid email format"
    assert warning.severity == "warning"


def test_extraction_record_minimal():
    """Test ExtractionRecord with minimal required fields"""
    record = ExtractionRecord(type=RecordType.FORM, source_file="test_form.html")

    assert record.type == RecordType.FORM
    assert record.source_file == "test_form.html"
    assert record.confidence is None  # Default value when not provided
    assert record.status == ExtractionStatus.PENDING
    assert len(record.id) > 0
    assert isinstance(record.extraction_timestamp, datetime)
    assert record.warnings == []


def test_extraction_record_with_client_data():
    """Test ExtractionRecord with client fields"""
    record = ExtractionRecord(
        type=RecordType.FORM,
        source_file="contact_form.html",
        confidence=0.92,
        client_name="Giannis Mixalis",
        email="giannis@example.com",
        phone="+30 210 1234567",
        company="Example Corp",
        service_interest="Web Development",
    )

    assert record.client_name == "Giannis Mixalis"
    assert record.email == "giannis@example.com"
    assert record.phone == "+30 210 1234567"
    assert record.company == "Example Corp"
    assert record.service_interest == "Web Development"


def test_extraction_record_with_invoice_data():
    """Test ExtractionRecord with invoice fields"""
    record = ExtractionRecord(
        type=RecordType.INVOICE,
        source_file="invoice_001.html",
        confidence=0.95,
        invoice_number="TF-2024-001",
        amount=1000.0,
        vat=240.0,
        total_amount=1240.0,
    )

    assert record.invoice_number == "TF-2024-001"
    assert record.amount == 1000.0
    assert record.vat == 240.0
    assert record.total_amount == 1240.0


def test_extraction_record_with_warnings():
    """Test ExtractionRecord with validation warnings"""
    warnings = [
        ValidationWarning(field="email", message="Email format may be invalid", severity="warning"),
        ValidationWarning(
            field="phone", message="Phone number format not recognized", severity="error"
        ),
    ]

    record = ExtractionRecord(
        type=RecordType.EMAIL, source_file="email_01.eml", confidence=0.65, warnings=warnings
    )

    assert len(record.warnings) == 2
    assert record.warnings[0].field == "email"
    assert record.warnings[1].severity == "error"


def test_extraction_record_confidence_validation():
    """Test confidence score validation"""
    # Valid confidence scores
    record1 = ExtractionRecord(type=RecordType.FORM, source_file="test.html", confidence=0.0)
    assert record1.confidence == 0.0

    record2 = ExtractionRecord(type=RecordType.FORM, source_file="test.html", confidence=1.0)
    assert record2.confidence == 1.0

    # Invalid confidence scores should raise validation error
    with pytest.raises(Exception):
        ExtractionRecord(type=RecordType.FORM, source_file="test.html", confidence=1.5)

    with pytest.raises(Exception):
        ExtractionRecord(type=RecordType.FORM, source_file="test.html", confidence=-0.1)


def test_scan_result():
    """Test ScanResult model"""
    result = ScanResult(
        processed_count=10,
        new_items_count=8,
        failed_count=2,
        errors=["Failed to parse file1.html", "Invalid format in file2.eml"],
    )

    assert result.processed_count == 10
    assert result.new_items_count == 8
    assert result.failed_count == 2
    assert len(result.errors) == 2


def test_approval_result_success():
    """Test ApprovalResult for successful approval"""
    result = ApprovalResult(success=True, sheet_row=42)

    assert result.success is True
    assert result.sheet_row == 42
    assert result.error is None


def test_approval_result_failure():
    """Test ApprovalResult for failed approval"""
    result = ApprovalResult(
        success=False, error="Failed to write to Google Sheets: API rate limit exceeded"
    )

    assert result.success is False
    assert result.sheet_row is None
    assert "rate limit" in result.error
