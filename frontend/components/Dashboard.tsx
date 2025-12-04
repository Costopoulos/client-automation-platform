import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { usePendingQueue } from "@/hooks/usePendingQueue";
import { useApproval } from "@/hooks/useApproval";
import { useSessionStats } from "@/hooks/useSessionStats";
import { useWebSocket } from "@/hooks/useWebSocket";
import { ExtractionCard } from "@/components/ExtractionCard";
import { EditModal } from "@/components/EditModal";
import { SourceViewer } from "@/components/SourceViewer";
import { FilterBar, FilterType } from "@/components/FilterBar";
import { StatsHeader } from "@/components/StatsHeader";
import { ExtractionRecord, RecordType } from "@/types/extraction";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle, FileSearch } from "lucide-react";
import { toast } from "sonner";

export function Dashboard() {
  const queryClient = useQueryClient();
  const { data: pendingRecords, isLoading, error } = usePendingQueue();
  const { approve, reject, edit, isEditing } = useApproval();
  const { approvedCount, rejectedCount, incrementApproved, incrementRejected, reset } = useSessionStats();

  // Modal state
  const [editingRecord, setEditingRecord] = React.useState<ExtractionRecord | null>(null);
  const [viewingSourceId, setViewingSourceId] = React.useState<string | null>(null);

  // Filter state
  const [filter, setFilter] = React.useState<FilterType>("all");

  // Track new items indicator
  const [hasNewItems, setHasNewItems] = React.useState(false);

  // WebSocket integration for real-time updates
  const { status: wsStatus } = useWebSocket({
    onMessage: (event) => {
      // Invalidate pending queue cache to trigger refetch
      queryClient.invalidateQueries({ queryKey: ["pending"] });

      // Handle different event types
      if (event.type === "record_added") {
        toast.success("New extraction record added", {
          description: "A new item is ready for review",
        });
        setHasNewItems(true);
      } else if (event.type === "record_removed") {
        // Record removed (approved or rejected)
        // No toast needed as approval/rejection already shows toast
      } else if (event.type === "record_updated") {
        toast.info("Record updated", {
          description: "An extraction record has been modified",
        });
      }
    },
    // Callbacks are handled in useWebSocket hook with better logging
  });

  // Track previous pending count to detect queue clear and new batch
  const prevPendingCountRef = React.useRef<number | null>(null);

  // Auto-reset statistics when queue is cleared or new batch arrives
  React.useEffect(() => {
    if (!pendingRecords) return;

    const currentCount = pendingRecords.length;
    const prevCount = prevPendingCountRef.current;

    // Reset stats in two scenarios:
    // 1. Queue becomes empty (cleared) - starting fresh
    // 2. Queue goes from 0 to having items (new batch arrives)
    if (prevCount !== null) {
      if ((prevCount > 0 && currentCount === 0) || (prevCount === 0 && currentCount > 0)) {
        reset();
      }
    }

    // Update ref for next comparison
    prevPendingCountRef.current = currentCount;
  }, [pendingRecords, reset]);

  // Clear new items indicator when user views the dashboard
  React.useEffect(() => {
    if (hasNewItems && pendingRecords) {
      // Clear indicator after a short delay to ensure user sees it
      const timer = setTimeout(() => {
        setHasNewItems(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [hasNewItems, pendingRecords]);

  // Handle approve action
  const handleApprove = (recordId: string) => {
    approve(recordId, {
      onSuccess: () => {
        incrementApproved();
      },
    });
  };

  // Handle reject action
  const handleReject = (recordId: string) => {
    reject(recordId, {
      onSuccess: () => {
        incrementRejected();
      },
    });
  };

  // Handle edit action - open modal
  const handleEdit = (recordId: string) => {
    const record = pendingRecords?.find((r) => r.id === recordId);
    if (record) {
      setEditingRecord(record);
    }
  };

  // Handle view source action
  const handleViewSource = (recordId: string) => {
    setViewingSourceId(recordId);
  };

  // Handle save from edit modal
  const handleSave = (recordId: string, updates: Partial<ExtractionRecord>) => {
    edit(
      { recordId, updates },
      {
        onSuccess: () => {
          setEditingRecord(null);
        },
      }
    );
  };

  // Calculate statistics
  const stats = React.useMemo(() => {
    if (!pendingRecords) {
      return {
        pendingCount: 0,
        warningCount: 0,
        counts: {
          all: 0,
          [RecordType.FORM]: 0,
          [RecordType.EMAIL]: 0,
          [RecordType.INVOICE]: 0,
        },
      };
    }

    const warningCount = pendingRecords.filter((r) => r.warnings.length > 0).length;
    const counts = {
      all: pendingRecords.length,
      [RecordType.FORM]: pendingRecords.filter((r) => r.type === RecordType.FORM).length,
      [RecordType.EMAIL]: pendingRecords.filter((r) => r.type === RecordType.EMAIL).length,
      [RecordType.INVOICE]: pendingRecords.filter((r) => r.type === RecordType.INVOICE).length,
    };

    return {
      pendingCount: pendingRecords.length,
      warningCount,
      counts,
    };
  }, [pendingRecords]);

  // Filter and sort records: warnings first, then by confidence (low to high)
  const filteredAndSortedRecords = React.useMemo(() => {
    if (!pendingRecords) return [];

    // Apply filter
    let filtered = pendingRecords;
    if (filter !== "all") {
      filtered = pendingRecords.filter((r) => r.type === filter);
    }

    // Sort: warnings first, then by confidence (low to high)
    return [...filtered].sort((a, b) => {
      // Records with warnings come first
      const aHasWarnings = a.warnings.length > 0;
      const bHasWarnings = b.warnings.length > 0;

      if (aHasWarnings && !bHasWarnings) return -1;
      if (!aHasWarnings && bHasWarnings) return 1;

      // Then sort by confidence (low to high)
      return a.confidence - b.confidence;
    });
  }, [pendingRecords, filter]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Loading pending records...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load pending records: {(error as Error).message}
        </AlertDescription>
      </Alert>
    );
  }

  if (!pendingRecords || pendingRecords.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileSearch className="h-16 w-16 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Pending Records</h3>
        <p className="text-muted-foreground max-w-md">
          There are no extraction records waiting for review. Trigger a scan to process new files.
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Statistics Header */}
      <div className="mb-6">
        <StatsHeader
          pendingCount={stats.pendingCount}
          warningCount={stats.warningCount}
          approvedCount={approvedCount}
          rejectedCount={rejectedCount}
          errorCount={0}
          wsStatus={wsStatus}
          hasNewItems={hasNewItems}
        />
      </div>

      {/* Filter Bar */}
      <div className="mb-6">
        <FilterBar
          filter={filter}
          onFilterChange={setFilter}
          counts={stats.counts}
        />
      </div>

      {/* Extraction Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredAndSortedRecords.map((record) => (
          <ExtractionCard
            key={record.id}
            record={record}
            onApprove={handleApprove}
            onReject={handleReject}
            onEdit={handleEdit}
            onViewSource={handleViewSource}
          />
        ))}
      </div>

      {/* Edit Modal */}
      <EditModal
        record={editingRecord}
        open={!!editingRecord}
        onOpenChange={(open) => !open && setEditingRecord(null)}
        onSave={handleSave}
        isSaving={isEditing}
      />

      {/* Source Viewer Modal */}
      <SourceViewer
        recordId={viewingSourceId}
        open={!!viewingSourceId}
        onOpenChange={(open) => !open && setViewingSourceId(null)}
      />
    </>
  );
}
