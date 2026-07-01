import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Plot, PlotCreate } from "../types";

export function useCreatePlot(farmId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (plotData: PlotCreate) => {
      if (!farmId) throw new Error("Finca no seleccionada");
      const { data } = await apiClient.post<Plot>(`/farms/${farmId}/plots`, plotData);
      return data;
    },
    onSuccess: () => {
      if (farmId) {
        queryClient.invalidateQueries({ queryKey: ["farms", farmId, "plots"] });
      }
    },
  });
}
