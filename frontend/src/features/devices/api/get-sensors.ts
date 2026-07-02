import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Sensor } from "../types";

export function useSensors() {
  return useQuery({
    queryKey: ["sensors"],
    queryFn: async () => {
      const { data } = await apiClient.get<Sensor[]>("/sensors");
      return data;
    },
  });
}
