// TypeScript interfaces matching backend Pydantic models

export enum RecordType {
  FORM = "FORM",
  EMAIL = "EMAIL",
  INVOICE = "INVOICE",
}

export enum ExtractionStatus {
  PENDING = "pending",
  APPROVED = "approved",
  REJECTED = "rejected",
}

export interface ValidationWarning {
  field: string;
  message: string;
  severity: "warning" | "error";
}

export interface ExtractionRecord {
  id: string;
  type: RecordType;
  source_file: string;
  extraction_timestamp: string;
  status: ExtractionStatus;
  confidence: number;
  warnings: ValidationWarning[];

  // Common fields
  date?: string | null;

  // Client fields (for FORM and EMAIL types)
  client_name?: string | null;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  service_interest?: string | null;
  priority?: string | null;
  message?: string | null;

  // Invoice fields (for INVOICE type)
  invoice_number?: string | null;
  amount?: number | null;
  vat?: number | null;
  total_amount?: number | null;

  // Metadata
  field_confidences: Record<string, number>;
  raw_extraction: Record<string, any>;
}

export interface ScanResult {
  processed_count: number;
  new_items_count: number;
  failed_count: number;
  errors: string[];
}

export interface ApprovalResult {
  success: boolean;
  sheet_row?: number | null;
  error?: string | null;
}

export interface HealthResponse {
  status: string;
  stats: {
    pending_count: number;
    processed_count: number;
    failed_count: number;
  };
}

export interface SourceResponse {
  content: string;
  type: string;
}
