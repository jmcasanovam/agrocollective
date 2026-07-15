import { useQuery } from "@tanstack/react-query";

interface AdministrativeEntry {
  name?: string;
  adminLevel?: number;
}

interface BigDataCloudResponse {
  city?: string;
  locality?: string;
  localityInfo?: {
    administrative?: AdministrativeEntry[];
  };
}

export interface LocationNames {
  municipality: string | null;
  province: string | null;
  region: string | null;
}

// Some Spanish admin names come back gazetteer-inverted (e.g. "Valenciana, Comunidad")
function normalizeName(name: string | undefined): string | null {
  if (!name) return null;
  return name.includes(", ") ? name.split(", ").reverse().join(" ") : name;
}

// Spain's admin hierarchy in BigDataCloud's response: 4 = comunidad autónoma, 6 = provincia, 8 = municipio
function findByAdminLevel(
  entries: AdministrativeEntry[] | undefined,
  level: number,
): string | null {
  return normalizeName(entries?.find((e) => e.adminLevel === level)?.name);
}

export function useReverseGeocode(lat: number | null, lon: number | null) {
  return useQuery({
    queryKey: ["reverse-geocode", lat, lon],
    queryFn: async (): Promise<LocationNames> => {
      const params = new URLSearchParams({
        latitude: String(lat),
        longitude: String(lon),
        localityLanguage: "es",
      });
      const res = await fetch(
        `https://api.bigdatacloud.net/data/reverse-geocode-client?${params.toString()}`,
      );
      if (!res.ok) throw new Error("No se pudo resolver la ubicación");
      const data: BigDataCloudResponse = await res.json();
      const administrative = data.localityInfo?.administrative;
      return {
        municipality:
          normalizeName(data.city) ??
          normalizeName(data.locality) ??
          findByAdminLevel(administrative, 8),
        province: findByAdminLevel(administrative, 6),
        region: findByAdminLevel(administrative, 4),
      };
    },
    enabled: lat !== null && lon !== null,
    staleTime: Infinity,
  });
}
