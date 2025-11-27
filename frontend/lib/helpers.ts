import { RecordType, ExtractionRecord } from "@/types/extraction";

/**
 * Get color variant for confidence level
 * Green: >0.8, Yellow: >0.6, Red: ≤0.6
 */
export function getConfidenceColor(confidence: number): "default" | "secondary" | "destructive" {
  if (confidence > 0.8) return "default"; // Green
  if (confidence > 0.6) return "secondary"; // Yellow
  return "destructive"; // Red
}

/**
 * Get color class for confidence level (for custom styling)
 */
export function getConfidenceColorClass(confidence: number): string {
  if (confidence > 0.8) return "text-green-600 bg-green-50 border-green-200";
  if (confidence > 0.6) return "text-yellow-600 bg-yellow-50 border-yellow-200";
  return "text-red-600 bg-red-50 border-red-200";
}

/**
 * Format confidence as percentage
 */
export function formatConfidence(confidence: number): string {
  return `${(confidence * 100).toFixed(0)}%`;
}

/**
 * Get badge variant for record type
 */
export function getRecordTypeBadge(type: RecordType): {
  label: string;
  variant: "default" | "secondary" | "outline";
} {
  switch (type) {
    case RecordType.FORM:
      return { label: "Form", variant: "default" };
    case RecordType.EMAIL:
      return { label: "Email", variant: "secondary" };
    case RecordType.INVOICE:
      return { label: "Invoice", variant: "outline" };
    default:
      return { label: "Unknown", variant: "outline" };
  }
}

/**
 * Check if record has warnings
 */
export function hasWarnings(record: ExtractionRecord): boolean {
  return record.warnings.length > 0;
}

/**
 * Check if record has errors (severity: error)
 */
export function hasErrors(record: ExtractionRecord): boolean {
  return record.warnings.some((w) => w.severity === "error");
}

/**
 * Format date string to readable format
 */
export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateString;
  }
}

/**
 * Get display fields for a record based on its type
 */
export function getDisplayFields(record: ExtractionRecord): Array<{
  label: string;
  value: string | number | null | undefined;
}> {
  const commonFields = [
    { label: "Source", value: record.source_file },
    { label: "Date", value: record.date },
  ];

  if (record.type === RecordType.INVOICE) {
    return [
      ...commonFields,
      { label: "Invoice #", value: record.invoice_number },
      { label: "Client", value: record.client_name },
      { label: "Amount", value: record.amount ? `€${record.amount.toFixed(2)}` : null },
      { label: "VAT", value: record.vat ? `€${record.vat.toFixed(2)}` : null },
      { label: "Total", value: record.total_amount ? `€${record.total_amount.toFixed(2)}` : null },
    ];
  }

  // FORM or EMAIL
  return [
    ...commonFields,
    { label: "Client Name", value: record.client_name },
    { label: "Email", value: record.email },
    { label: "Phone", value: record.phone },
    { label: "Company", value: record.company },
    { label: "Service Interest", value: record.service_interest },
    { label: "Priority", value: record.priority },
    { label: "Message", value: record.message },
  ];
}

/**
 * Filter records by type
 */
export function filterRecordsByType(
  records: ExtractionRecord[],
  filter: "all" | RecordType
): ExtractionRecord[] {
  if (filter === "all") return records;
  return records.filter((r) => r.type === filter);
}

/**
 * Sort records - warnings first, then by confidence (low to high)
 */
export function sortRecords(records: ExtractionRecord[]): ExtractionRecord[] {
  return [...records].sort((a, b) => {
    // Records with warnings come first
    const aHasWarnings = hasWarnings(a);
    const bHasWarnings = hasWarnings(b);

    if (aHasWarnings && !bHasWarnings) return -1;
    if (!aHasWarnings && bHasWarnings) return 1;

    // Then sort by confidence (lowest first)
    return a.confidence - b.confidence;
  });
}
