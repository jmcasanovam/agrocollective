import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { IrrigationRecord } from "../types";

export function useIrrigation(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "irrigation"],
    queryFn: async () => {
      if (!plotId) return [];
      const { data } = await apiClient.get<IrrigationRecord[]>(`/plots/${plotId}/irrigation`);
      return data;
    },
    enabled: !!plotId,
  });
}
