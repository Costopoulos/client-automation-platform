import * as React from "react";
import { usePendingQueue } from "@/hooks/usePendingQueue";
import { useApproval } from "@/hooks/useApproval";
import { ExtractionCard } from "@/components/ExtractionCard";
import { EditModal } from "@/components/EditModal";
import { SourceViewer } from "@/components/SourceViewer";
import { FilterBar, FilterType } from "@/components/FilterBar";
import { StatsHeader } from "@/components/StatsHeader";
import { ExtractionRecord, RecordType } from "@/types/extraction";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle, FileSearch } from "lucide-react";

export function Dashboard() {
  const { data: pendingRecords, isLoading, error } = usePendingQueue();
  const { approve, reject, edit, isEditing } = useApproval();

  // Modal state
  const [editingRecord, setEditingRecord] = React.useState<ExtractionRecord | null>(null);
  const [viewingSourceId, setViewingSourceId] = React.useState<string | null>(null);

  // Filter state
  const [filter, setFilter] = React.useState<FilterType>("all");

  // Handle approve action
  const handleApprove = (recordId: string) => {
    approve(recordId);
  };

  // Handle reject action
  const handleReject = (recordId: string) => {
    reject(recordId);
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
    if (!pendingRecords) return [];

    return [...pendingRecords].sort((a, b) => {
      // Records with warnings come first
      const aHasWarnings = a.warnings.length > 0;
      const bHasWarnings = b.warnings.length > 0;

      if (aHasWarnings && !bHasWarnings) return -1;
      if (!aHasWarnings && bHasWarnings) return 1;

      // Then sort by confidence (low to high)
      return a.confidence - b.confidence;
    });
  }, [pendingRecords]);

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedRecords.map((record) => (
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
