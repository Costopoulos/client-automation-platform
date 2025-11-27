import * as React from "react";
import { useForm } from "react-hook-form";
import { ExtractionRecord, RecordType } from "@/types/extraction";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface EditModalProps {
  record: ExtractionRecord | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (recordId: string, updates: Partial<ExtractionRecord>) => void;
  isSaving?: boolean;
}

export function EditModal({
  record,
  open,
  onOpenChange,
  onSave,
  isSaving = false,
}: EditModalProps) {
  const { register, handleSubmit, reset } = useForm<Partial<ExtractionRecord>>();

  // Reset form when record changes
  React.useEffect(() => {
    if (record) {
      reset(record);
    }
  }, [record, reset]);

  const onSubmit = (data: Partial<ExtractionRecord>) => {
    if (!record) return;
    onSave(record.id, data);
  };

  if (!record) return null;

  const isInvoice = record.type === RecordType.INVOICE;
  const isClientRecord = record.type === RecordType.FORM || record.type === RecordType.EMAIL;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Extraction Record</DialogTitle>
          <DialogDescription>
            Make changes to the extracted data. Click save when you&apos;re done.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Common fields */}
          <div className="space-y-2">
            <Label htmlFor="date">Date</Label>
            <Input
              id="date"
              type="text"
              {...register("date")}
              placeholder="YYYY-MM-DD"
            />
          </div>

          {/* Invoice-specific fields */}
          {isInvoice && (
            <>
              <div className="space-y-2">
                <Label htmlFor="invoice_number">Invoice Number</Label>
                <Input
                  id="invoice_number"
                  type="text"
                  {...register("invoice_number")}
                  placeholder="TF-2024-001"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="client_name">Client Name</Label>
                <Input
                  id="client_name"
                  type="text"
                  {...register("client_name")}
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="amount">Amount (€)</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    {...register("amount", { valueAsNumber: true })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="vat">VAT (€)</Label>
                  <Input
                    id="vat"
                    type="number"
                    step="0.01"
                    {...register("vat", { valueAsNumber: true })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="total_amount">Total (€)</Label>
                  <Input
                    id="total_amount"
                    type="number"
                    step="0.01"
                    {...register("total_amount", { valueAsNumber: true })}
                  />
                </div>
              </div>
            </>
          )}

          {/* Client record fields */}
          {isClientRecord && (
            <>
              <div className="space-y-2">
                <Label htmlFor="client_name">Client Name</Label>
                <Input
                  id="client_name"
                  type="text"
                  {...register("client_name")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  {...register("email")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  type="tel"
                  {...register("phone")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="company">Company</Label>
                <Input
                  id="company"
                  type="text"
                  {...register("company")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="service_interest">Service Interest</Label>
                <Input
                  id="service_interest"
                  type="text"
                  {...register("service_interest")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Input
                  id="priority"
                  type="text"
                  {...register("priority")}
                  placeholder="High, Medium, Low"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="message">Message</Label>
                <Textarea
                  id="message"
                  {...register("message")}
                  rows={4}
                />
              </div>
            </>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
