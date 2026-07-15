import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Sensor } from "../types";

export function useAssignSensors(plotId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ deviceId, sensorIds }: { deviceId: string; sensorIds: string[] }) => {
      if (!plotId) throw new Error("Parcela no seleccionada");
      const { data } = await apiClient.post<Sensor[]>(
        `/plots/${plotId}/devices/${deviceId}/sensors`,
        { sensor_ids: sensorIds },
      );
      return data;
    },
    onSuccess: () => {
      if (plotId) {
        queryClient.invalidateQueries({ queryKey: ["plots", plotId, "devices"] });
      }
    },
  });
}
