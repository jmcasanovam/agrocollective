"use client";

import type { Farm } from "../types";
import { useRegions } from "../api/get-regions";
import { useReverseGeocode } from "../api/get-reverse-geocode";

const MAIN_IMG_SIZE = { width: 480, height: 400 };
const SIDE_IMG_SIZE = { width: 480, height: 190 };

// Uniform aspect on mobile (all three tiles equal size, stacked). On desktop
// the close-up tile drops this and stretches to fill the spanned grid rows.
const TILE_ASPECT = "aspect-[480/190]";

// Bounding box half-widths (km): close-up (area-based), provincia/región, and
// comunidad autónoma scale.
const WIDE_PADDING_KM = 5;
const REGION_PADDING_KM = 35;

function farmPaddingKm(areaHa: number | null) {
  const areaKm2 = (areaHa ?? 5) / 100;
  const sideKm = Math.sqrt(areaKm2);
  return Math.max(sideKm * 4, 0.6);
}

function computeBoundingBox(lat: number, lon: number, paddedKm: number) {
  const latDelta = paddedKm / 111;
  const lonDelta = paddedKm / (111 * Math.cos((lat * Math.PI) / 180) || 1);
  return {
    minLon: lon - lonDelta,
    minLat: lat - latDelta,
    maxLon: lon + lonDelta,
    maxLat: lat + latDelta,
  };
}

function buildMapUrl(
  lat: number,
  lon: number,
  paddedKm: number,
  size: { width: number; height: number },
  service: "World_Imagery" | "World_Street_Map",
) {
  const { minLon, minLat, maxLon, maxLat } = computeBoundingBox(lat, lon, paddedKm);
  const params = new URLSearchParams({
    bbox: `${minLon},${minLat},${maxLon},${maxLat}`,
    bboxSR: "4326",
    imageSR: "4326",
    size: `${size.width},${size.height}`,
    format: "png32",
    f: "image",
  });
  return `https://server.arcgisonline.com/ArcGIS/rest/services/${service}/MapServer/export?${params.toString()}`;
}

function MapTile({
  url,
  alt,
  label,
  pinSize = 30,
  className = "",
  compact = false,
  fillOnDesktop = false,
}: {
  url: string;
  alt: string;
  label: string;
  pinSize?: number;
  className?: string;
  compact?: boolean;
  fillOnDesktop?: boolean;
}) {
  return (
    <div
      className={`relative rounded-xl overflow-hidden border border-[#e7e2d6] bg-[#eef0e8] ${TILE_ASPECT} ${
        fillOnDesktop ? "md:aspect-auto md:h-full" : ""
      } ${className}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt={alt} className="w-full h-full object-cover" loading="lazy" />

      {/* Pin at center */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <svg
          width={pinSize}
          height={pinSize}
          viewBox="0 0 24 24"
          fill="#c0453d"
          stroke="#fff"
          strokeWidth="1.5"
          className="-translate-y-1/4 drop-shadow-[0_1px_3px_rgba(0,0,0,0.5)]"
        >
          <path d="M12 22s7-7.58 7-13a7 7 0 1 0-14 0c0 5.42 7 13 7 13Z" />
          <circle cx="12" cy="9" r="2.5" fill="#fff" stroke="none" />
        </svg>
      </div>

      {/* Name label */}
      {!compact && (
        <div className="absolute top-1.5 left-1.5 text-[10px] font-semibold text-white bg-black/45 px-1.5 py-0.5 rounded">
          {label}
        </div>
      )}

      {/* Imagery attribution (required by Esri terms of use) */}
      {!compact && (
        <div className="absolute bottom-1 right-1.5 text-[8px] text-white bg-black/45 px-1 py-0.5 rounded">
          Esri ArcGIS
        </div>
      )}
    </div>
  );
}

export function FarmLocationMap({ farm, compact = false }: { farm: Farm; compact?: boolean }) {
  const { data: regions } = useRegions();
  const region = regions?.find((r) => r.id === farm.region_id);
  const { data: geocode } = useReverseGeocode(farm.latitude, farm.longitude);

  if (farm.latitude === null || farm.longitude === null) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-8 bg-[#f7f6f0] rounded-xl text-center">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#8a978d"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 22s7-7.58 7-13a7 7 0 1 0-14 0c0 5.42 7 13 7 13Z" />
          <path d="m4 4 16 16" />
        </svg>
        <p className="text-xs text-[#8a978d] max-w-[280px]">
          Esta finca no tiene coordenadas registradas. Añádelas para ver su ubicación en el mapa.
        </p>
      </div>
    );
  }

  const { latitude: lat, longitude: lon } = farm;
  const regionName = region?.name ?? "Región";

  const municipalityLabel =
    geocode?.municipality && geocode?.province
      ? `${geocode.municipality} (${geocode.province})`
      : regionName;
  const autonomousRegionLabel = geocode?.region ?? regionName;

  const closeUrl = buildMapUrl(
    lat,
    lon,
    farmPaddingKm(farm.area_ha),
    MAIN_IMG_SIZE,
    "World_Imagery",
  );
  const wideUrl = buildMapUrl(lat, lon, WIDE_PADDING_KM, SIDE_IMG_SIZE, "World_Street_Map");
  const regionUrl = buildMapUrl(lat, lon, REGION_PADDING_KM, SIDE_IMG_SIZE, "World_Street_Map");

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 md:grid-rows-2 gap-3">
        <MapTile
          className="md:col-start-1 md:row-start-1 md:row-span-2"
          url={closeUrl}
          alt={`Imagen satelital de ${farm.name}`}
          label={farm.name}
          pinSize={compact ? 14 : 28}
          compact={compact}
          fillOnDesktop
        />
        <MapTile
          className="md:col-start-2 md:row-start-1"
          url={wideUrl}
          alt={`Vista del municipio de ${farm.name}`}
          label={municipalityLabel}
          pinSize={compact ? 8 : 16}
          compact={compact}
        />
        <MapTile
          className="md:col-start-2 md:row-start-2"
          url={regionUrl}
          alt={`Vista de la comunidad autónoma de ${farm.name}`}
          label={autonomousRegionLabel}
          pinSize={compact ? 6 : 10}
          compact={compact}
        />
      </div>
      {!compact && (
        <p className="text-[11px] text-[#9aa79d] mt-1.5">
          Cerca de {regionName} ({lat.toFixed(4)}, {lon.toFixed(4)})
          {farm.area_ha ? ` · ${farm.area_ha} ha` : ""}
        </p>
      )}
    </div>
  );
}
