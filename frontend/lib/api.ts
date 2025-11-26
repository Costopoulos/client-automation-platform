import {
  ExtractionRecord,
  ScanResult,
  ApprovalResult,
  HealthResponse,
  SourceResponse,
} from "@/types/extraction";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new APIError(
      errorData.error || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      errorData.detail
    );
  }
  return response.json();
}

/**
 * Trigger file scanning and extraction
 */
export async function scanFiles(): Promise<ScanResult> {
  const response = await fetch(`${API_URL}/api/scan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<ScanResult>(response);
}

/**
 * Get all pending extraction records
 */
export async function getPendingRecords(): Promise<ExtractionRecord[]> {
  const response = await fetch(`${API_URL}/api/pending`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<ExtractionRecord[]>(response);
}

/**
 * Get count of pending items
 */
export async function getPendingCount(): Promise<{ count: number; has_new: boolean }> {
  const response = await fetch(`${API_URL}/api/pending/count`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<{ count: number; has_new: boolean }>(response);
}

/**
 * Approve an extraction record and write to Google Sheets
 */
export async function approveRecord(recordId: string): Promise<ApprovalResult> {
  const response = await fetch(`${API_URL}/api/approve/${recordId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<ApprovalResult>(response);
}

/**
 * Reject an extraction record
 */
export async function rejectRecord(recordId: string): Promise<{ success: boolean }> {
  const response = await fetch(`${API_URL}/api/reject/${recordId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<{ success: boolean }>(response);
}

/**
 * Update fields in an extraction record
 */
export async function editRecord(
  recordId: string,
  updates: Partial<ExtractionRecord>
): Promise<ExtractionRecord> {
  const response = await fetch(`${API_URL}/api/edit/${recordId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
  });
  return handleResponse<ExtractionRecord>(response);
}

/**
 * Get original source file content
 */
export async function getSourceContent(recordId: string): Promise<SourceResponse> {
  const response = await fetch(`${API_URL}/api/source/${recordId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<SourceResponse>(response);
}

/**
 * Get system health and statistics
 */
export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/api/health`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });
  return handleResponse<HealthResponse>(response);
}

export { APIError };
