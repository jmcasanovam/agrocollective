import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Device, DeviceUpdate } from "../types";

export function useUpdateDevice(plotId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ deviceId, data }: { deviceId: string; data: DeviceUpdate }) => {
      if (!plotId) throw new Error("Parcela no seleccionada");
      const { data: resData } = await apiClient.put<Device>(
        `/plots/${plotId}/devices/${deviceId}`,
        data,
      );
      return resData;
    },
    onSuccess: () => {
      if (plotId) {
        queryClient.invalidateQueries({ queryKey: ["plots", plotId, "devices"] });
      }
    },
  });
}
