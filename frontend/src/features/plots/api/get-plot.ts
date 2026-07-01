import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Plot } from "../types";

export function usePlot({ farmId, plotId }: { farmId: string | null; plotId: string | null }) {
  return useQuery({
    queryKey: ["farms", farmId, "plots", plotId],
    queryFn: async () => {
      if (!farmId || !plotId) return null;
      const { data } = await apiClient.get<Plot>(`/farms/${farmId}/plots/${plotId}`);
      return data;
    },
    enabled: !!farmId && !!plotId,
  });
}
