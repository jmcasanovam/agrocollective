import { useQuery, type Query } from "@tanstack/react-query";
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

export interface WeatherMonthFilter {
  year: number;
  month: number; // 1-12
}

// Clave de caché: por estación SiAR (no por parcela), asi todas las parcelas
// que comparten estacion reutilizan el mismo fetch/cache en vez de repetirlo
// por cada parcela. Mientras no se conozca la estacion aun, se usa el plotId
// como clave provisional (no comparte cache hasta que se resuelve).
function weatherQueryKey(
  plotId: string | null,
  stationCode: string | null | undefined,
  filter: WeatherMonthFilter | null | undefined,
) {
  return [
    "siar-weather",
    stationCode ?? plotId,
    filter ? `${filter.year}-${filter.month}` : "recent",
  ];
}

export function usePlotWeather(
  plotId: string | null,
  options?: {
    stationCode?: string | null;
    filter?: WeatherMonthFilter | null;
    refetchInterval?: number | false | ((query: Query<WeatherRecord[] | null>) => number | false);
  },
) {
  const filter = options?.filter ?? null;

  return useQuery({
    queryKey: weatherQueryKey(plotId, options?.stationCode, filter),
    queryFn: async () => {
      if (!plotId) return null;
      const { data } = await apiClient.get<WeatherRecord[]>(`/plots/${plotId}/weather`, {
        params: filter ? { year: filter.year, month: filter.month } : undefined,
      });
      return data;
    },
    enabled: !!plotId,
    // El polling de "hoy" solo tiene sentido en la vista por defecto (recientes);
    // al mirar un mes concreto del pasado no hay nada que esperar.
    refetchInterval: filter ? false : (options?.refetchInterval ?? false),
  });
}
