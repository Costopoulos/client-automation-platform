// TanStack Query mutations for approval workflow

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { approveRecord, rejectRecord, editRecord } from "@/lib/api";
import { toast } from "sonner";
import { ExtractionRecord } from "@/types/extraction";

export function useApproval() {
  const queryClient = useQueryClient();

  const approveMutation = useMutation({
    mutationFn: (recordId: string) => approveRecord(recordId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["pending"] });
      toast.success(
        `Record approved and saved to Google Sheets${data.sheet_row ? ` (row ${data.sheet_row})` : ""}`
      );
    },
    onError: (error: Error) => {
      toast.error(`Approval failed: ${error.message}`);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (recordId: string) => rejectRecord(recordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending"] });
      toast.success("Record rejected and removed from queue");
    },
    onError: (error: Error) => {
      toast.error(`Rejection failed: ${error.message}`);
    },
  });

  const editMutation = useMutation({
    mutationFn: ({
      recordId,
      updates,
    }: {
      recordId: string;
      updates: Partial<ExtractionRecord>;
    }) => editRecord(recordId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pending"] });
      toast.success("Record updated successfully");
    },
    onError: (error: Error) => {
      toast.error(`Update failed: ${error.message}`);
    },
  });

  return {
    // Expose mutateAsync to allow custom onSuccess callbacks
    approve: (recordId: string, options?: { onSuccess?: () => void }) => {
      approveMutation.mutate(recordId, options);
    },
    reject: (recordId: string, options?: { onSuccess?: () => void }) => {
      rejectMutation.mutate(recordId, options);
    },
    edit: editMutation.mutate,
    isApproving: approveMutation.isPending,
    isRejecting: rejectMutation.isPending,
    isEditing: editMutation.isPending,
  };
}
