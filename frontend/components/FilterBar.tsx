import * as React from "react";
import { Button } from "@/components/ui/button";
import { RecordType } from "@/types/extraction";
import { FileText, Mail, Receipt, List } from "lucide-react";
import { cn } from "@/lib/utils";

export type FilterType = "all" | RecordType;

interface FilterBarProps {
  filter: FilterType;
  onFilterChange: (filter: FilterType) => void;
  counts?: {
    all: number;
    [RecordType.FORM]: number;
    [RecordType.EMAIL]: number;
    [RecordType.INVOICE]: number;
  };
}

export function FilterBar({ filter, onFilterChange, counts }: FilterBarProps) {
  const filters: Array<{
    value: FilterType;
    label: string;
    icon: React.ReactNode;
  }> = [
    { value: "all", label: "All", icon: <List className="h-4 w-4" /> },
    { value: RecordType.FORM, label: "Forms", icon: <FileText className="h-4 w-4" /> },
    { value: RecordType.EMAIL, label: "Emails", icon: <Mail className="h-4 w-4" /> },
    { value: RecordType.INVOICE, label: "Invoices", icon: <Receipt className="h-4 w-4" /> },
  ];

  return (
    <div className="flex flex-wrap gap-2 items-center">
      <span className="text-sm font-medium text-muted-foreground mr-2">
        Filter by type:
      </span>
      {filters.map((f) => {
        const isActive = filter === f.value;
        const count = counts ? counts[f.value as keyof typeof counts] : undefined;

        return (
          <Button
            key={f.value}
            variant={isActive ? "default" : "outline"}
            size="sm"
            onClick={() => onFilterChange(f.value)}
            className={cn(
              "flex items-center gap-2",
              isActive && "shadow-md"
            )}
          >
            {f.icon}
            {f.label}
            {count !== undefined && (
              <span
                className={cn(
                  "ml-1 px-1.5 py-0.5 rounded-full text-xs font-semibold",
                  isActive
                    ? "bg-primary-foreground/20"
                    : "bg-muted"
                )}
              >
                {count}
              </span>
            )}
          </Button>
        );
      })}
    </div>
  );
}
