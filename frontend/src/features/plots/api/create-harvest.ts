import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Harvest, HarvestCreate } from "../types";

export function useCreateHarvest(plotId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: HarvestCreate) => {
      if (!plotId) throw new Error("Parcela no seleccionada");
      const { data: created } = await apiClient.post<Harvest>(`/plots/${plotId}/harvests`, data);
      return created;
    },
    onSuccess: () => {
      if (plotId) {
        queryClient.invalidateQueries({ queryKey: ["plots", plotId, "harvests"] });
      }
    },
  });
}
