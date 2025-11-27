import * as React from "react";
import { ExtractionRecord, RecordType } from "@/types/extraction";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle, FileText, Mail, Receipt } from "lucide-react";

interface ExtractionCardProps {
  record: ExtractionRecord;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string) => void;
  onViewSource?: (id: string) => void;
}

export function ExtractionCard({
  record,
  onApprove,
  onReject,
  onEdit,
  onViewSource,
}: ExtractionCardProps) {
  const hasWarnings = record.warnings.length > 0;

  // Confidence color coding: green >0.8, yellow >0.6, red ≤0.6
  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return "text-green-600 bg-green-50 border-green-200";
    if (confidence > 0.6) return "text-yellow-600 bg-yellow-50 border-yellow-200";
    return "text-red-600 bg-red-50 border-red-200";
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence > 0.8) return "High";
    if (confidence > 0.6) return "Medium";
    return "Low";
  };

  // Get icon for record type
  const getTypeIcon = (type: RecordType) => {
    switch (type) {
      case RecordType.FORM:
        return <FileText className="h-4 w-4" />;
      case RecordType.EMAIL:
        return <Mail className="h-4 w-4" />;
      case RecordType.INVOICE:
        return <Receipt className="h-4 w-4" />;
    }
  };

  // Get badge variant for record type
  const getTypeBadgeVariant = (type: RecordType) => {
    switch (type) {
      case RecordType.FORM:
        return "default";
      case RecordType.EMAIL:
        return "secondary";
      case RecordType.INVOICE:
        return "outline";
    }
  };

  // Render fields based on record type
  const renderFields = () => {
    if (record.type === RecordType.INVOICE) {
      return (
        <div className="space-y-2">
          {record.invoice_number && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Invoice #:
              </span>
              <span className="text-sm font-semibold">{record.invoice_number}</span>
            </div>
          )}
          {record.client_name && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Client:
              </span>
              <span className="text-sm">{record.client_name}</span>
            </div>
          )}
          {record.date && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Date:
              </span>
              <span className="text-sm">{record.date}</span>
            </div>
          )}
          {record.amount !== null && record.amount !== undefined && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Amount:
              </span>
              <span className="text-sm">€{record.amount.toFixed(2)}</span>
            </div>
          )}
          {record.vat !== null && record.vat !== undefined && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                VAT:
              </span>
              <span className="text-sm">€{record.vat.toFixed(2)}</span>
            </div>
          )}
          {record.total_amount !== null && record.total_amount !== undefined && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Total:
              </span>
              <span className="text-sm font-bold">€{record.total_amount.toFixed(2)}</span>
            </div>
          )}
        </div>
      );
    } else {
      // FORM or EMAIL type
      return (
        <div className="space-y-2">
          {record.client_name && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Name:
              </span>
              <span className="text-sm">{record.client_name}</span>
            </div>
          )}
          {record.email && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Email:
              </span>
              <span className="text-sm">{record.email}</span>
            </div>
          )}
          {record.phone && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Phone:
              </span>
              <span className="text-sm">{record.phone}</span>
            </div>
          )}
          {record.company && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Company:
              </span>
              <span className="text-sm">{record.company}</span>
            </div>
          )}
          {record.service_interest && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Service:
              </span>
              <span className="text-sm">{record.service_interest}</span>
            </div>
          )}
          {record.priority && (
            <div className="flex justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Priority:
              </span>
              <span className="text-sm">{record.priority}</span>
            </div>
          )}
          {record.message && (
            <div className="mt-2">
              <span className="text-sm font-medium text-muted-foreground">
                Message:
              </span>
              <p className="text-sm mt-1 line-clamp-3">{record.message}</p>
            </div>
          )}
        </div>
      );
    }
  };

  return (
    <Card
      className={cn(
        "transition-all hover:shadow-lg",
        hasWarnings && "border-yellow-500 border-2"
      )}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge
              variant={getTypeBadgeVariant(record.type)}
              className="flex items-center gap-1"
            >
              {getTypeIcon(record.type)}
              {record.type}
            </Badge>
          </div>
          <Badge
            className={cn(
              "flex items-center gap-1 border",
              getConfidenceColor(record.confidence)
            )}
          >
            {record.confidence > 0.8 ? (
              <CheckCircle className="h-3 w-3" />
            ) : (
              <AlertCircle className="h-3 w-3" />
            )}
            {getConfidenceLabel(record.confidence)} (
            {(record.confidence * 100).toFixed(0)}%)
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground mt-2">
          {record.source_file}
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        {renderFields()}

        {hasWarnings && (
          <Alert variant="destructive" className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Validation Warnings</AlertTitle>
            <AlertDescription>
              <ul className="list-disc list-inside space-y-1 mt-2">
                {record.warnings.map((warning, index) => (
                  <li key={index} className="text-xs">
                    <span className="font-medium">{warning.field}:</span>{" "}
                    {warning.message}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>

      <CardFooter className="flex flex-col gap-2 pt-3">
        <div className="flex gap-2 w-full">
          <Button
            onClick={() => onApprove(record.id)}
            variant="default"
            size="sm"
            className="flex-1"
          >
            Approve
          </Button>
          <Button
            onClick={() => onEdit(record.id)}
            variant="outline"
            size="sm"
            className="flex-1"
          >
            Edit
          </Button>
          <Button
            onClick={() => onReject(record.id)}
            variant="destructive"
            size="sm"
            className="flex-1"
          >
            Reject
          </Button>
        </div>
        {onViewSource && (
          <Button
            onClick={() => onViewSource(record.id)}
            variant="ghost"
            size="sm"
            className="w-full"
          >
            View Source Document
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
