import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Plot } from "../types";

export function usePlots(farmId: string | null) {
  return useQuery({
    queryKey: ["farms", farmId, "plots"],
    queryFn: async () => {
      if (!farmId) return [];
      const { data } = await apiClient.get<Plot[]>(`/farms/${farmId}/plots`);
      return data;
    },
    enabled: !!farmId,
  });
}
