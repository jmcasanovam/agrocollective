import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Device, DeviceCreate } from "../types";

export function useCreateDevice(plotId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (deviceData: DeviceCreate) => {
      if (!plotId) throw new Error("Parcela no seleccionada");
      const { data } = await apiClient.post<Device>(`/plots/${plotId}/devices`, deviceData);
      return data;
    },
    onSuccess: () => {
      if (plotId) {
        queryClient.invalidateQueries({ queryKey: ["plots", plotId, "devices"] });
      }
    },
  });
}
