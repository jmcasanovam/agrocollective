import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export function useDeleteDevice(plotId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (deviceId: string) => {
      if (!plotId) throw new Error("Parcela no seleccionada");
      const { data } = await apiClient.delete(`/plots/${plotId}/devices/${deviceId}`);
      return data;
    },
    onSuccess: () => {
      if (plotId) {
        queryClient.invalidateQueries({ queryKey: ["plots", plotId, "devices"] });
      }
    },
  });
}
