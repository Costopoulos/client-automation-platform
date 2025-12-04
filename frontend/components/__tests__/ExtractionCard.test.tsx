import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ExtractionCard } from "../ExtractionCard";
import { ExtractionRecord, RecordType, ExtractionStatus } from "@/types/extraction";

const mockRecord: ExtractionRecord = {
  id: "test-123",
  type: RecordType.EMAIL,
  source_file: "test.eml",
  extraction_timestamp: "2024-01-01T00:00:00Z",
  status: ExtractionStatus.PENDING,
  confidence: 0.85,
  warnings: [],
  client_name: "John Doe",
  email: "john@example.com",
  phone: "+30 123 456 7890",
  company: "Test Corp",
  service_interest: "Web Development",
  message: "Test message",
  field_confidences: {},
  raw_extraction: {},
};

describe("ExtractionCard", () => {
  it("renders extraction record data", () => {
    render(
      <ExtractionCard
        record={mockRecord}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onViewSource={vi.fn()}
      />
    );

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("john@example.com")).toBeInTheDocument();
    expect(screen.getByText("Test Corp")).toBeInTheDocument();
  });

  it("displays confidence level", () => {
    render(
      <ExtractionCard
        record={mockRecord}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onViewSource={vi.fn()}
      />
    );

    expect(screen.getByText(/85%/i)).toBeInTheDocument();
  });

  it("shows warnings when present", () => {
    const recordWithWarnings = {
      ...mockRecord,
      warnings: [
        { field: "email", message: "Invalid format", severity: "warning" as const },
      ],
    };

    render(
      <ExtractionCard
        record={recordWithWarnings}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onViewSource={vi.fn()}
      />
    );

    expect(screen.getByText(/invalid format/i)).toBeInTheDocument();
  });

  it("calls onApprove when approve button clicked", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();

    render(
      <ExtractionCard
        record={mockRecord}
        onApprove={onApprove}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onViewSource={vi.fn()}
      />
    );

    await user.click(screen.getByRole("button", { name: /approve/i }));
    expect(onApprove).toHaveBeenCalledWith("test-123");
  });

  it("calls onReject when reject button clicked", async () => {
    const user = userEvent.setup();
    const onReject = vi.fn();

    render(
      <ExtractionCard
        record={mockRecord}
        onApprove={vi.fn()}
        onReject={onReject}
        onEdit={vi.fn()}
        onViewSource={vi.fn()}
      />
    );

    await user.click(screen.getByRole("button", { name: /reject/i }));
    expect(onReject).toHaveBeenCalledWith("test-123");
  });

  it("calls onEdit when edit button clicked", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();

    render(
      <ExtractionCard
        record={mockRecord}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={onEdit}
        onViewSource={vi.fn()}
      />
    );

    await user.click(screen.getByRole("button", { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith("test-123");
  });

  it("displays different record types correctly", () => {
    const invoiceRecord = {
      ...mockRecord,
      type: RecordType.INVOICE,
      invoice_number: "INV-001",
      amount: 1000,
      vat: 240,
      total_amount: 1240,
    };

    render(
      <ExtractionCard
        record={invoiceRecord}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onViewSource={vi.fn()}
      />
    );

    expect(screen.getByText("INV-001")).toBeInTheDocument();
    expect(screen.getByText(/1240/)).toBeInTheDocument();
  });

  it("displays low confidence correctly", () => {
    const lowConfidenceRecord = {
      ...mockRecord,
      confidence: 0.5,
    };

    render(
      <ExtractionCard
        record={lowConfidenceRecord}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
        onViewSource={vi.fn()}
      />
    );

    // Should show 50% confidence
    expect(screen.getByText(/50%/i)).toBeInTheDocument();
    // Should show "Low" label
    expect(screen.getByText(/low/i)).toBeInTheDocument();
  });
});
