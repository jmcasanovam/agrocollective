"use client";

import { usePlots } from "../api/get-plots";

const CROP_LABELS: Record<string, string> = {
  olivo: "Olivo",
  tomate: "Tomate",
  almendro: "Almendro",
  vina: "Viña",
  naranjo: "Naranjo",
};

const REGION_LABELS: Record<string, string> = {
  VALENCIA: "Valencia",
  GUADIX_BAZA: "Guadix / Baza",
};

export function PlotsList() {
  const { data, isLoading, isError, error } = usePlots();

  if (isLoading) {
    return <p className="text-gray-500">Cargando parcelas…</p>;
  }

  if (isError) {
    return (
      <p className="text-red-600">
        Error al cargar parcelas: {error instanceof Error ? error.message : "Desconocido"}
      </p>
    );
  }

  if (!data || data.items.length === 0) {
    return <p className="text-gray-500">No hay parcelas registradas.</p>;
  }

  return (
    <div>
      <p className="mb-4 text-sm text-gray-500">
        {data.total} parcela{data.total !== 1 ? "s" : ""} en total
      </p>
      <ul className="divide-y divide-gray-200 rounded border border-gray-200">
        {data.items.map((plot) => (
          <li key={plot.id} className="flex items-center justify-between px-4 py-3">
            <div>
              <span className="font-medium">{plot.name}</span>
              <span className="ml-2 text-sm text-gray-500">
                {CROP_LABELS[plot.crop_type] ?? plot.crop_type}
              </span>
            </div>
            <span className="text-sm text-gray-400">
              {REGION_LABELS[plot.region_code] ?? plot.region_code}
              {plot.area_ha ? ` · ${plot.area_ha} ha` : ""}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
