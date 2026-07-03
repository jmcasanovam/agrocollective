import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { AnaloguePlot } from "../types";

export function useAnalogues(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "analogues"],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<AnaloguePlot[]>(`/plots/${plotId}/analogues`);
      return data;
    },
    enabled: !!plotId,
  });
}
