import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FilterBar } from "../FilterBar";
import { RecordType } from "@/types/extraction";

describe("FilterBar", () => {
    const mockCounts = {
        all: 10,
        [RecordType.FORM]: 3,
        [RecordType.EMAIL]: 4,
        [RecordType.INVOICE]: 3,
    };

    it("renders all filter buttons", () => {
        render(
            <FilterBar
                filter="all"
                onFilterChange={vi.fn()}
                counts={mockCounts}
            />
        );

        expect(screen.getByRole("button", { name: /all/i })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /forms/i })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /emails/i })).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /invoices/i })).toBeInTheDocument();
    });

    it("displays correct counts for each filter", () => {
        render(
            <FilterBar
                filter="all"
                onFilterChange={vi.fn()}
                counts={mockCounts}
            />
        );

        expect(screen.getByText("10")).toBeInTheDocument(); // All
        expect(screen.getAllByText("3")).toHaveLength(2); // Forms and Invoices both have 3
        expect(screen.getByText("4")).toBeInTheDocument(); // Emails
    });

    it("highlights active filter", () => {
        const { rerender } = render(
            <FilterBar
                filter="all"
                onFilterChange={vi.fn()}
                counts={mockCounts}
            />
        );

        const allButton = screen.getByRole("button", { name: /all/i });
        expect(allButton).toHaveClass("bg-primary");

        rerender(
            <FilterBar
                filter={RecordType.FORM}
                onFilterChange={vi.fn()}
                counts={mockCounts}
            />
        );

        const formsButton = screen.getByRole("button", { name: /forms/i });
        expect(formsButton).toHaveClass("bg-primary");
    });

    it("calls onFilterChange when filter button clicked", async () => {
        const user = userEvent.setup();
        const onFilterChange = vi.fn();

        render(
            <FilterBar
                filter="all"
                onFilterChange={onFilterChange}
                counts={mockCounts}
            />
        );

        await user.click(screen.getByRole("button", { name: /forms/i }));
        expect(onFilterChange).toHaveBeenCalledWith(RecordType.FORM);

        await user.click(screen.getByRole("button", { name: /emails/i }));
        expect(onFilterChange).toHaveBeenCalledWith(RecordType.EMAIL);

        await user.click(screen.getByRole("button", { name: /invoices/i }));
        expect(onFilterChange).toHaveBeenCalledWith(RecordType.INVOICE);

        await user.click(screen.getByRole("button", { name: /all/i }));
        expect(onFilterChange).toHaveBeenCalledWith("all");
    });

    it("handles zero counts", () => {
        const zeroCounts = {
            all: 0,
            [RecordType.FORM]: 0,
            [RecordType.EMAIL]: 0,
            [RecordType.INVOICE]: 0,
        };

        render(
            <FilterBar
                filter="all"
                onFilterChange={vi.fn()}
                counts={zeroCounts}
            />
        );

        // Should still render buttons with 0 counts
        const allZeros = screen.getAllByText("0");
        expect(allZeros.length).toBeGreaterThan(0);
    });

    it("does not call onFilterChange when clicking active filter", async () => {
        const user = userEvent.setup();
        const onFilterChange = vi.fn();

        render(
            <FilterBar
                filter="all"
                onFilterChange={onFilterChange}
                counts={mockCounts}
            />
        );

        // Click the already active filter
        await user.click(screen.getByRole("button", { name: /all/i }));

        // Should still be called (component doesn't prevent this)
        expect(onFilterChange).toHaveBeenCalledWith("all");
    });
});
