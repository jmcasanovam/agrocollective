import { useQueries } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { PerformanceHistoryEntry } from "../types";

export function useFarmPerformanceSummary(plotIds: string[]) {
  const results = useQueries({
    queries: plotIds.map((plotId) => ({
      queryKey: ["plots", plotId, "performance-history", 1],
      queryFn: async () => {
        const { data } = await apiClient.get<PerformanceHistoryEntry[]>(
          `/plots/${plotId}/performance-history`,
          { params: { limit: 1 } },
        );
        return data[0] ?? null;
      },
      enabled: !!plotId,
    })),
  });

  const isLoading = plotIds.length > 0 && results.some((r) => r.isLoading);
  const entries = results
    .map((r) => r.data)
    .filter((entry): entry is PerformanceHistoryEntry => !!entry);

  return { entries, isLoading };
}
