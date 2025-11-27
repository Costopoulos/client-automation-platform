// TanStack Query hook for fetching pending records

import { useQuery } from "@tanstack/react-query";
import { getPendingRecords } from "@/lib/api";

export function usePendingQueue() {
  return useQuery({
    queryKey: ["pending"],
    queryFn: getPendingRecords,
    // WebSocket will trigger refetch via invalidateQueries
  });
}
