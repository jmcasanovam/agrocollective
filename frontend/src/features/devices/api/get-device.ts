import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Device } from "../types";

export function useDevice(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "devices"],
    queryFn: async () => {
      if (!plotId) return null;
      try {
        const { data } = await apiClient.get<Device>(`/plots/${plotId}/devices`);
        return data;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
        if (err.response?.status === 404) {
          return null;
        }
        throw err;
      }
    },
    enabled: !!plotId,
  });
}
