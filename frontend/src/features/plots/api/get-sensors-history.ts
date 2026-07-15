import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SensorReadingPoint } from "../types";

export function useSensorsHistory(plotId: string | null, hours: number = 24) {
  return useQuery({
    queryKey: ["plots", plotId, "sensors", "history", hours],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<SensorReadingPoint[]>(
        `/plots/${plotId}/sensors/history`,
        {
          params: { hours },
        },
      );
      return data;
    },
    enabled: !!plotId,
    refetchInterval: 60_000,
  });
}
