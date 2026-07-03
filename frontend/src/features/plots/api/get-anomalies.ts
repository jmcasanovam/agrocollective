import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { AnomalyRecord } from "../types";

export function useAnomalies(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "anomalies"],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<AnomalyRecord[]>(`/plots/${plotId}/anomalies`);
      return data;
    },
    enabled: !!plotId,
  });
}
