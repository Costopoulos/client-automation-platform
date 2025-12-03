import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface StatsHeaderProps {
  pendingCount: number;
  approvedCount?: number;
  rejectedCount?: number;
  errorCount?: number;
  warningCount?: number;
}

export function StatsHeader({
  pendingCount,
  approvedCount = 0,
  rejectedCount = 0,
  errorCount = 0,
  warningCount = 0,
}: StatsHeaderProps) {
  const stats = [
    {
      label: "Pending Review",
      value: pendingCount,
      icon: <Clock className="h-5 w-5" />,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      borderColor: "border-blue-200",
    },
    {
      label: "With Warnings",
      value: warningCount,
      icon: <AlertTriangle className="h-5 w-5" />,
      color: "text-yellow-600",
      bgColor: "bg-yellow-50",
      borderColor: "border-yellow-200",
    },
    {
      label: "Approved",
      value: approvedCount,
      icon: <CheckCircle className="h-5 w-5" />,
      color: "text-green-600",
      bgColor: "bg-green-50",
      borderColor: "border-green-200",
    },
    {
      label: "Rejected",
      value: rejectedCount,
      icon: <XCircle className="h-5 w-5" />,
      color: "text-gray-600",
      bgColor: "bg-gray-50",
      borderColor: "border-gray-200",
    },
    {
      label: "Errors",
      value: errorCount,
      icon: <AlertTriangle className="h-5 w-5" />,
      color: "text-red-600",
      bgColor: "bg-red-50",
      borderColor: "border-red-200",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {stats.map((stat) => (
        <Card
          key={stat.label}
          className={cn(
            "border-2 transition-all hover:shadow-md",
            stat.borderColor
          )}
        >
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  {stat.label}
                </p>
                <p className={cn("text-2xl font-bold", stat.color)}>
                  {stat.value}
                </p>
              </div>
              <div className={cn("p-2 rounded-lg", stat.bgColor)}>
                <div className={stat.color}>{stat.icon}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
