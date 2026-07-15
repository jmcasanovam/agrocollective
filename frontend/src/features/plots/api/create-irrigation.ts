import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { IrrigationCreate, IrrigationRecord } from "../types";

export function useCreateIrrigation(plotId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: IrrigationCreate) => {
      if (!plotId) throw new Error("Parcela no seleccionada");
      const { data: created } = await apiClient.post<IrrigationRecord>(
        `/plots/${plotId}/irrigation`,
        data,
      );
      return created;
    },
    onSuccess: () => {
      if (plotId) {
        queryClient.invalidateQueries({ queryKey: ["plots", plotId, "irrigation"] });
      }
    },
  });
}
