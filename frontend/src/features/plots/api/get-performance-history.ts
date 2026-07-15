import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { PerformanceHistoryEntry } from "../types";

export function usePerformanceHistory(plotId: string | null, limit: number = 90) {
  return useQuery({
    queryKey: ["plots", plotId, "performance-history", limit],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<PerformanceHistoryEntry[]>(
        `/plots/${plotId}/performance-history`,
        { params: { limit } },
      );
      return data;
    },
    enabled: !!plotId,
  });
}
