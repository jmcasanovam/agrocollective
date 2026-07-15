import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Harvest } from "../types";

export function useHarvests(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "harvests"],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<Harvest[]>(`/plots/${plotId}/harvests`);
      return data;
    },
    enabled: !!plotId,
  });
}
