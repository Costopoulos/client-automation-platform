import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Wifi,
  WifiOff,
  Bell,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { WebSocketStatus } from "@/hooks/useWebSocket";

interface StatsHeaderProps {
  pendingCount: number;
  approvedCount?: number;
  rejectedCount?: number;
  errorCount?: number;
  warningCount?: number;
  wsStatus?: WebSocketStatus;
  hasNewItems?: boolean;
}

export function StatsHeader({
  pendingCount,
  approvedCount = 0,
  rejectedCount = 0,
  errorCount = 0,
  warningCount = 0,
  wsStatus = "disconnected",
  hasNewItems = false,
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

  // WebSocket status indicator
  const wsStatusConfig = {
    connected: {
      icon: <Wifi className="h-4 w-4" />,
      label: "Live",
      color: "text-green-600",
      bgColor: "bg-green-50",
    },
    connecting: {
      icon: <Wifi className="h-4 w-4 animate-pulse" />,
      label: "Connecting",
      color: "text-yellow-600",
      bgColor: "bg-yellow-50",
    },
    disconnected: {
      icon: <WifiOff className="h-4 w-4" />,
      label: "Offline",
      color: "text-gray-600",
      bgColor: "bg-gray-50",
    },
    error: {
      icon: <WifiOff className="h-4 w-4" />,
      label: "Error",
      color: "text-red-600",
      bgColor: "bg-red-50",
    },
  };

  const currentWsStatus = wsStatusConfig[wsStatus];

  return (
    <div>
      {/* WebSocket Status and New Items Indicator */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={cn(
              "flex items-center gap-1.5 px-3 py-1",
              currentWsStatus.bgColor,
              currentWsStatus.color
            )}
          >
            {currentWsStatus.icon}
            <span className="text-xs font-medium">{currentWsStatus.label}</span>
          </Badge>
          {hasNewItems && (
            <Badge
              variant="default"
              className="flex items-center gap-1.5 px-3 py-1 bg-blue-600 text-white animate-pulse"
            >
              <Bell className="h-4 w-4" />
              <span className="text-xs font-medium">New Items Available</span>
            </Badge>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
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
    </div>
  );
}
