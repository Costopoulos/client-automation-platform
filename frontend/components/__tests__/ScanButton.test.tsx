import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScanButton } from "../ScanButton";
import * as api from "@/lib/api";

// Mock the API
vi.mock("@/lib/api", () => ({
  scanFiles: vi.fn(),
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }

  Wrapper.displayName = 'TestWrapper';

  return Wrapper;
}

describe("ScanButton", () => {
  it("renders scan button with correct text", () => {
    render(<ScanButton />, { wrapper: createWrapper() });
    expect(screen.getByRole("button", { name: /scan for new files/i })).toBeInTheDocument();
  });

  it("shows loading state when scanning", async () => {
    const user = userEvent.setup();
    vi.mocked(api.scanFiles).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(<ScanButton />, { wrapper: createWrapper() });

    const button = screen.getByRole("button");
    await user.click(button);

    expect(screen.getByText(/scanning/i)).toBeInTheDocument();
    expect(button).toBeDisabled();
  });

  it("calls scanFiles API when clicked", async () => {
    const user = userEvent.setup();
    const mockScanFiles = vi.mocked(api.scanFiles).mockResolvedValue({
      processed_count: 5,
      new_items_count: 3,
      failed_count: 0,
      errors: [],
    });

    render(<ScanButton />, { wrapper: createWrapper() });

    const button = screen.getByRole("button");
    await user.click(button);

    await waitFor(() => {
      expect(mockScanFiles).toHaveBeenCalled();
    });
  });

  it("handles successful scan with new files", async () => {
    const user = userEvent.setup();
    vi.mocked(api.scanFiles).mockResolvedValue({
      processed_count: 5,
      new_items_count: 3,
      failed_count: 0,
      errors: [],
    });

    render(<ScanButton />, { wrapper: createWrapper() });

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByRole("button")).not.toBeDisabled();
    });
  });

  it("handles scan with no new files", async () => {
    const user = userEvent.setup();
    vi.mocked(api.scanFiles).mockResolvedValue({
      processed_count: 0,
      new_items_count: 0,
      failed_count: 0,
      errors: [],
    });

    render(<ScanButton />, { wrapper: createWrapper() });

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByRole("button")).not.toBeDisabled();
    });
  });

  it("handles scan errors", async () => {
    const user = userEvent.setup();
    vi.mocked(api.scanFiles).mockRejectedValue(new Error("Network error"));

    render(<ScanButton />, { wrapper: createWrapper() });

    await user.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(screen.getByRole("button")).not.toBeDisabled();
    });
  });
});
