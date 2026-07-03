import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { MlPrediction } from "../types";

export function useMlPredictions(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "ml-predictions"],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<MlPrediction[]>(`/plots/${plotId}/ml-predictions`);
      return data;
    },
    enabled: !!plotId,
  });
}
