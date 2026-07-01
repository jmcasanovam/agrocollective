import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Crop, Soil } from "../types";

export function useCrops() {
  return useQuery({
    queryKey: ["crops"],
    queryFn: async () => {
      const { data } = await apiClient.get<Crop[]>("/crops");
      return data;
    },
  });
}

export function useSoils() {
  return useQuery({
    queryKey: ["soils"],
    queryFn: async () => {
      const { data } = await apiClient.get<Soil[]>("/soils");
      return data;
    },
  });
}
