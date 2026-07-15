import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SensorReadingPoint } from "../types";

export function useSensorsLatest(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "sensors", "latest"],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<SensorReadingPoint[]>(`/plots/${plotId}/sensors/latest`);
      return data;
    },
    enabled: !!plotId,
    refetchInterval: 60_000,
  });
}
