import { useRegions } from "../api/get-regions";
import { useReverseGeocode } from "../api/get-reverse-geocode";
import type { Farm } from "../types";

// Un municipio+provincia legible (via reverse geocoding) para mostrar donde
// esta una finca/parcela fuera del mapa satelital dedicado: en listados y
// fichas donde solo hace falta una linea de contexto, no las 3 imagenes.
export function useFarmLocationLabel(
  farm: Pick<Farm, "latitude" | "longitude" | "region_id"> | null | undefined,
) {
  const { data: regions } = useRegions();
  const { data: geocode, isLoading } = useReverseGeocode(
    farm?.latitude ?? null,
    farm?.longitude ?? null,
  );

  const region = regions?.find((r) => r.id === farm?.region_id);
  const stationCode = region?.siar_station_code ?? null;

  if (!farm || farm.latitude === null || farm.longitude === null) {
    return { label: null, isLoading: false, coords: null, stationCode };
  }

  const label =
    geocode?.municipality && geocode?.province
      ? `${geocode.municipality} (${geocode.province})`
      : (region?.name ?? null);

  return { label, isLoading, coords: { lat: farm.latitude, lon: farm.longitude }, stationCode };
}
