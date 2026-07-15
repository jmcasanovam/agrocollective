import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface Region {
  id: string;
  code: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
  siar_station_code: string | null;
}

export function useRegions() {
  return useQuery({
    queryKey: ["regions"],
    queryFn: async () => {
      const { data } = await apiClient.get<Region[]>("/regions");
      return data;
    },
  });
}
