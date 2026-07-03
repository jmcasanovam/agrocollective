import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Recommendation } from "../types";

export function useRecommendations(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "recommendations"],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<Recommendation[]>(`/plots/${plotId}/recommendations`);
      return data;
    },
    enabled: !!plotId,
  });
}
