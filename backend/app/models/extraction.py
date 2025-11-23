import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class RecordType(str, Enum):
    """Type of extraction record"""

    FORM = "FORM"
    EMAIL = "EMAIL"
    INVOICE = "INVOICE"


class ExtractionStatus(str, Enum):
    """Status of extraction record in the workflow"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ValidationWarning(BaseModel):
    """Warning or error from validation"""

    field: str
    message: str
    severity: str  # "warning" | "error"


class ExtractionRecord(BaseModel):
    """Complete extraction record with all fields"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: RecordType
    source_file: str
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: ExtractionStatus = ExtractionStatus.PENDING
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    warnings: List[ValidationWarning] = []

    # Common fields
    date: Optional[str] = None

    # Client fields (for FORM and EMAIL types)
    client_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    service_interest: Optional[str] = None
    priority: Optional[str] = None
    message: Optional[str] = None

    # Invoice fields (for INVOICE type)
    invoice_number: Optional[str] = None
    amount: Optional[float] = None
    vat: Optional[float] = None
    total_amount: Optional[float] = None

    # Metadata
    field_confidences: Optional[Dict[str, float]] = None
    raw_extraction: Optional[Dict[str, Any]] = None


class ScanResult(BaseModel):
    """Result of scanning and processing files"""

    processed_count: int
    new_items_count: int
    failed_count: int
    errors: List[str] = []


class ApprovalResult(BaseModel):
    """Result of approving an extraction record"""

    success: bool
    sheet_row: Optional[int] = None
    error: Optional[str] = None
