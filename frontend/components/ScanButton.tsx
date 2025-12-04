import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { scanFiles } from "@/lib/api";
import { toast } from "sonner";
import { Search, Loader2 } from "lucide-react";

export function ScanButton() {
  const queryClient = useQueryClient();

  const { mutate: triggerScan, isPending } = useMutation({
    mutationFn: scanFiles,
    onSuccess: (result) => {
      // Invalidate pending queue to refresh
      queryClient.invalidateQueries({ queryKey: ["pending"] });

      // Show success toast with details
      if (result.new_items_count > 0) {
        toast.success("Scan complete!", {
          description: `Found ${result.new_items_count} new file${result.new_items_count === 1 ? "" : "s"} to process`,
        });
      } else {
        toast.info("Scan complete", {
          description: "No new files found",
        });
      }

      // Show errors if any
      if (result.failed_count > 0) {
        toast.warning(`${result.failed_count} file${result.failed_count === 1 ? "" : "s"} failed to process`, {
          description: "Check logs for details",
        });
      }
    },
    onError: (error: Error) => {
      toast.error("Scan failed", {
        description: error.message,
      });
    },
  });

  return (
    <Button
      onClick={() => triggerScan()}
      disabled={isPending}
      size="lg"
      className="gap-2"
    >
      {isPending ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Scanning...
        </>
      ) : (
        <>
          <Search className="h-4 w-4" />
          Scan for New Files
        </>
      )}
    </Button>
  );
}
