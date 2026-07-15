"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  usePlotWeather,
  type WeatherMonthFilter,
  type WeatherRecord,
} from "../api/get-plot-weather";
import { getSiarPersister } from "@/lib/react-query";
import { CloudSunIcon } from "@/components/icons/card-icons";
import { AlertPopup } from "@/components/ui/alert-popup";

interface PlotWeatherCardProps {
  plotId: string;
  // Resuelto por el llamador (features/plots no puede importar de features/farms):
  // ver plot-detail.tsx / app/(app)/plots/[plotId]/page.tsx.
  stationCode?: string | null;
}

const MAX_TODAY_ATTEMPTS = 5;
const RETRY_INTERVAL_MS = 5000;

// El cero no es positivo ni negativo: evita mostrar "-0" o "-0.0" cuando una
// temperatura muy cercana a cero redondea a cero pero conserva el signo.
function formatSigned(value: number, digits: number): string {
  return value.toFixed(digits).replace(/^-0(\.0+)?$/, (m) => m.slice(1));
}

// La estacion SiAR solo tiene datos reales desde esta fecha (ver scripts/download_siar.py).
const FIRST_AVAILABLE_MONTH = { year: 2025, month: 6 };

const MONTH_LABELS = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];

function availableMonths(): WeatherMonthFilter[] {
  const now = new Date();
  const months: WeatherMonthFilter[] = [];
  let y = FIRST_AVAILABLE_MONTH.year;
  let m = FIRST_AVAILABLE_MONTH.month;
  while (y < now.getFullYear() || (y === now.getFullYear() && m <= now.getMonth() + 1)) {
    months.push({ year: y, month: m });
    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
  }
  return months.reverse(); // mas reciente primero
}

function todayStr() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(
    now.getDate(),
  ).padStart(2, "0")}`;
}

function hasTodayRecord(weather: WeatherRecord[] | null | undefined) {
  if (!weather) return false;
  const today = todayStr();
  return weather.some((row) => row.date === today);
}

export function PlotWeatherCard({ plotId, stationCode = null }: PlotWeatherCardProps) {
  const [dismissed, setDismissed] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [lastCountedUpdate, setLastCountedUpdate] = useState(0);
  const [monthFilter, setMonthFilter] = useState<WeatherMonthFilter | null>(null);

  const queryClient = useQueryClient();

  const {
    data: weather,
    isLoading,
    isError,
    dataUpdatedAt,
  } = usePlotWeather(plotId, {
    stationCode,
    filter: monthFilter,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (hasTodayRecord(data)) return false;
      if (attempts >= MAX_TODAY_ATTEMPTS) return false;
      return RETRY_INTERVAL_MS;
    },
  });

  const months = useMemo(() => availableMonths(), []);

  const clearCache = () => {
    queryClient.removeQueries({ queryKey: ["siar-weather"] });
    void getSiarPersister().removeClient();
  };

  const gotToday = hasTodayRecord(weather);

  // Count each resolved fetch that still doesn't carry today's record, so
  // polling gives up after MAX_TODAY_ATTEMPTS instead of retrying forever.
  // Adjusting state during render (not an effect) mirrors "adjusting state
  // when a prop changes" from the React docs: it's idempotent per render
  // since the condition clears itself once lastCountedUpdate catches up.
  if (dataUpdatedAt && dataUpdatedAt !== lastCountedUpdate) {
    setLastCountedUpdate(dataUpdatedAt);
    if (!gotToday) setAttempts((a) => a + 1);
  }

  const exhaustedRetries = attempts >= MAX_TODAY_ATTEMPTS;
  const showStalePopup = !dismissed && !!weather && !gotToday && exhaustedRetries;

  const stalePopup = showStalePopup && (
    <AlertPopup
      title="Datos climáticos de hoy no disponibles"
      message="No se han podido obtener los registros de la estación SiAR correspondientes al día de hoy. Se muestran los últimos datos disponibles."
      onClose={() => setDismissed(true)}
    />
  );

  const waitingForToday =
    !monthFilter && !isLoading && !isError && weather && !gotToday && !exhaustedRetries;

  if (isLoading || waitingForToday) {
    return (
      <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 text-center">
        <div className="w-6 h-6 rounded-full border-[3px] border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
        <p className="text-xs text-[#6b7a70]">
          {waitingForToday
            ? "Esperando los datos climáticos de hoy de la estación SiAR..."
            : "Cargando datos climáticos de la estación..."}
        </p>
      </div>
    );
  }

  if (isError || !weather) {
    return (
      <div className="p-6 bg-white rounded-2xl border border-red-100 text-red-600 text-xs text-center">
        Error al cargar los datos de la estación climática.
      </div>
    );
  }

  if (weather.length === 0) {
    return (
      <>
        {stalePopup}
        <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 text-center text-xs text-[#6b7a70]">
          No hay registros climáticos disponibles para este sector.
        </div>
      </>
    );
  }

  const displayStationCode = weather[0]?.station_code || stationCode || "N/D";

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 space-y-4">
      {stalePopup}
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center gap-3 border-b border-[#f0ece2] pb-3">
        <div className="flex items-center gap-2">
          <CloudSunIcon className="w-[18px] h-[18px] text-[#3a4a42]" />
          <h3 className="text-sm font-bold text-[#24302a] m-0">
            Registros climáticos diario (SiAR)
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={monthFilter ? `${monthFilter.year}-${monthFilter.month}` : "recent"}
            onChange={(e) => {
              if (e.target.value === "recent") {
                setMonthFilter(null);
                return;
              }
              const [y, m] = e.target.value.split("-").map(Number);
              setMonthFilter({ year: y, month: m });
            }}
            className="text-xs font-semibold text-[#3a4a42] bg-[#f4f2eb] border border-[#e7e2d6] rounded px-2 py-1 outline-none cursor-pointer"
          >
            <option value="recent">Últimos 30 días</option>
            {months.map((m) => (
              <option key={`${m.year}-${m.month}`} value={`${m.year}-${m.month}`}>
                {MONTH_LABELS[m.month - 1]} {m.year}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={clearCache}
            title="Vuelve a pedir los datos climáticos a la estación en vez de usar los guardados en esta sesión"
            className="text-xs font-semibold text-[#6b7a70] bg-transparent border border-[#e7e2d6] rounded px-2 py-1 cursor-pointer hover:bg-[#f4f2eb]"
          >
            Vaciar caché
          </button>
          <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-[#f4f2eb] text-[#3a4a42]">
            Estación: {displayStationCode}
          </span>
        </div>
      </div>

      {/* Table container */}
      <div className="overflow-x-auto max-h-[300px] overflow-y-auto pr-1">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-white">
            <tr className="border-b border-[#f0ece2] text-[#6b7a70]">
              <th className="pb-2 bg-white font-bold uppercase text-[9px] tracking-wider">Fecha</th>
              <th className="pb-2 bg-white font-bold uppercase text-[9px] tracking-wider text-center">
                Temp. (°C)
              </th>
              <th className="pb-2 bg-white font-bold uppercase text-[9px] tracking-wider text-center">
                Mín/Máx
              </th>
              <th className="pb-2 bg-white font-bold uppercase text-[9px] tracking-wider text-center">
                Hum. (%)
              </th>
              <th className="pb-2 bg-white font-bold uppercase text-[9px] tracking-wider text-center">
                Hum. Mín/Máx
              </th>
              <th className="pb-2 bg-white font-bold uppercase text-[9px] tracking-wider text-center">
                Lluvia (mm)
              </th>
              <th className="pb-2 bg-white font-bold uppercase text-[9px] tracking-wider text-center">
                <span className="relative group inline-flex items-center gap-1 cursor-help border-b border-dotted border-[#9aa79d]">
                  ETo (mm/d)
                  {/* Se abre hacia abajo (no hacia arriba): el header es "sticky top-0" dentro
                      de un contenedor con scroll, así que no hay espacio visible por encima. */}
                  <span className="pointer-events-none absolute top-full right-0 mt-2 w-56 rounded-lg bg-[#24302a] text-white text-[10.5px] normal-case tracking-normal font-normal p-2.5 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity z-30">
                    <strong className="block mb-1">Evapotranspiración de referencia (ETo)</strong>
                    Agua que pierde un cultivo de referencia por evaporación y transpiración en un
                    día, medida en mm/día. Cuanto más alta, más riego hace falta para compensarla.
                  </span>
                </span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#fcfbfa]">
            {weather.map((row) => (
              <tr key={row.date} className="hover:bg-[#fcfbf9] transition-colors">
                <td className="py-2.5 font-medium text-[#24302a]">
                  {new Date(row.date).toLocaleDateString("es-ES", {
                    day: "2-digit",
                    month: "short",
                  })}
                </td>
                <td className="py-2.5 text-center text-[#24302a] font-semibold">
                  {row.air_temp !== null ? `${formatSigned(row.air_temp, 1)}°` : "no hay datos"}
                </td>
                <td className="py-2.5 text-center text-[#6b7a70]">
                  {row.air_temp_min !== null && row.air_temp_max !== null ? (
                    <span>
                      {formatSigned(row.air_temp_min, 0)}° / {formatSigned(row.air_temp_max, 0)}°
                    </span>
                  ) : (
                    "no hay datos"
                  )}
                </td>
                <td className="py-2.5 text-center text-[#24302a]">
                  {row.relative_humidity !== null
                    ? `${row.relative_humidity.toFixed(0)}%`
                    : "no hay datos"}
                </td>
                <td className="py-2.5 text-center text-[#6b7a70]">
                  {row.relative_humidity_min !== null && row.relative_humidity_max !== null ? (
                    <span>
                      {row.relative_humidity_min.toFixed(0)}% /{" "}
                      {row.relative_humidity_max.toFixed(0)}%
                    </span>
                  ) : (
                    "no hay datos"
                  )}
                </td>
                <td className="py-2.5 text-center font-semibold text-[#2f5d3f]">
                  {row.precipitation !== null && row.precipitation > 0 ? (
                    <span className="bg-[#e3efdd] text-[#356440] px-1.5 py-0.5 rounded">
                      {row.precipitation.toFixed(1)} mm
                    </span>
                  ) : (
                    <span className="text-[#9aa79d]">0.0</span>
                  )}
                </td>
                <td className="py-2.5 text-center text-[#8a5b52] font-mono font-semibold">
                  {row.eto !== null ? row.eto.toFixed(1) : "no hay datos"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
