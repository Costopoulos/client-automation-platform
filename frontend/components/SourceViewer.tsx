import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { getSourceContent } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle } from "lucide-react";

interface SourceViewerProps {
  recordId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SourceViewer({
  recordId,
  open,
  onOpenChange,
}: SourceViewerProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["source", recordId],
    queryFn: () => getSourceContent(recordId!),
    enabled: !!recordId && open,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Original Source Document</DialogTitle>
          <DialogDescription>
            View the original source file content for comparison
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load source content: {(error as Error).message}
              </AlertDescription>
            </Alert>
          )}

          {data && (
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground">
                Type: <span className="font-medium">{data.type}</span>
              </div>

              {/* Render HTML content */}
              {(data.type === "text/html" || data.type === "html") && (
                <div className="border rounded-lg p-4 bg-muted/50">
                  <iframe
                    srcDoc={data.content}
                    className="w-full h-[500px] bg-white rounded"
                    title="Source Document"
                    sandbox="allow-same-origin"
                  />
                </div>
              )}

              {/* Render plain text content */}
              {(data.type === "text/plain" || data.type === "text" || data.type === "email") && (
                <div className="border rounded-lg p-4 bg-muted/50">
                  <pre className="text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                    {data.content}
                  </pre>
                </div>
              )}

              {/* Fallback for other types */}
              {data.type !== "text/html" &&
                data.type !== "html" &&
                data.type !== "text/plain" &&
                data.type !== "text" &&
                data.type !== "email" && (
                  <div className="border rounded-lg p-4 bg-muted/50">
                    <pre className="text-xs whitespace-pre-wrap font-mono overflow-x-auto">
                      {data.content}
                    </pre>
                  </div>
                )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
