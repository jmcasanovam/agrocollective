import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface WeatherRecord {
  date: string;
  station_code: string;
  air_temp: number | null;
  air_temp_max: number | null;
  air_temp_min: number | null;
  relative_humidity: number | null;
  relative_humidity_max: number | null;
  relative_humidity_min: number | null;
  soil_temp: number | null;
  eto: number | null;
  precipitation: number | null;
}

export function usePlotWeather(plotId: string | null) {
  return useQuery({
    queryKey: ["plots", plotId, "weather"],
    queryFn: async () => {
      if (!plotId) return null;
      const { data } = await apiClient.get<WeatherRecord[]>(`/plots/${plotId}/weather`);
      return data;
    },
    enabled: !!plotId,
  });
}
