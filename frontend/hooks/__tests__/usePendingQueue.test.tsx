import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePendingQueue } from "../usePendingQueue";
import * as api from "@/lib/api";

// Mock the API
vi.mock("@/lib/api");

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

describe("usePendingQueue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches pending records successfully", async () => {
    const mockRecords = [
      {
        id: "1",
        type: "EMAIL",
        client_name: "John Doe",
        confidence: 0.9,
      },
      {
        id: "2",
        type: "FORM",
        client_name: "Jane Smith",
        confidence: 0.85,
      },
    ];

    vi.mocked(api.getPendingRecords).mockResolvedValue(mockRecords as any);

    const { result } = renderHook(() => usePendingQueue(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockRecords);
    expect(api.getPendingRecords).toHaveBeenCalledTimes(1);
  });

  it("handles empty pending queue", async () => {
    vi.mocked(api.getPendingRecords).mockResolvedValue([]);

    const { result } = renderHook(() => usePendingQueue(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual([]);
  });

  it("handles fetch errors", async () => {
    vi.mocked(api.getPendingRecords).mockRejectedValue(
      new Error("Network error")
    );

    const { result } = renderHook(() => usePendingQueue(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeUndefined();
  });
});
