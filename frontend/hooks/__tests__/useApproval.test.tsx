import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useApproval } from "../useApproval";
import * as api from "@/lib/api";

// Mock the API
vi.mock("@/lib/api");

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("useApproval", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("approves a record successfully", async () => {
    vi.mocked(api.approveRecord).mockResolvedValue({
      success: true,
      sheet_row: 42,
    });

    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    result.current.approve("test-123");

    await waitFor(() => {
      expect(result.current.isApproving).toBe(false);
    });

    expect(api.approveRecord).toHaveBeenCalledWith("test-123");
  });

  it("rejects a record successfully", async () => {
    vi.mocked(api.rejectRecord).mockResolvedValue({ success: true });

    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    result.current.reject("test-123");

    await waitFor(() => {
      expect(result.current.isRejecting).toBe(false);
    });

    expect(api.rejectRecord).toHaveBeenCalledWith("test-123");
  });

  it("edits a record successfully", async () => {
    const mockUpdatedRecord = {
      id: "test-123",
      client_name: "Updated Name",
    };

    vi.mocked(api.editRecord).mockResolvedValue(mockUpdatedRecord as any);

    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    result.current.edit({
      recordId: "test-123",
      updates: { client_name: "Updated Name" },
    });

    await waitFor(() => {
      expect(result.current.isEditing).toBe(false);
    });

    expect(api.editRecord).toHaveBeenCalledWith("test-123", {
      client_name: "Updated Name",
    });
  });

  it("handles approval errors", async () => {
    vi.mocked(api.approveRecord).mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    result.current.approve("test-123");

    await waitFor(() => {
      expect(result.current.isApproving).toBe(false);
    });
  });

  it("calls custom onSuccess callback", async () => {
    vi.mocked(api.approveRecord).mockResolvedValue({
      success: true,
      sheet_row: 42,
    });

    const onSuccess = vi.fn();

    const { result } = renderHook(() => useApproval(), {
      wrapper: createWrapper(),
    });

    result.current.approve("test-123", { onSuccess });

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
