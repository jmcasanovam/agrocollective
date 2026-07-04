"use client";

import { useState } from "react";
import { usePlotWeather, type WeatherRecord } from "../api/get-plot-weather";
import { CloudSunIcon } from "@/components/icons/card-icons";
import { AlertPopup } from "@/components/ui/alert-popup";

interface PlotWeatherCardProps {
  plotId: string;
}

const MAX_TODAY_ATTEMPTS = 5;
const RETRY_INTERVAL_MS = 5000;

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

export function PlotWeatherCard({ plotId }: PlotWeatherCardProps) {
  const [dismissed, setDismissed] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [lastCountedUpdate, setLastCountedUpdate] = useState(0);

  const {
    data: weather,
    isLoading,
    isError,
    dataUpdatedAt,
  } = usePlotWeather(plotId, {
    refetchInterval: (query) => {
      const data = query.state.data;
      if (hasTodayRecord(data)) return false;
      if (attempts >= MAX_TODAY_ATTEMPTS) return false;
      return RETRY_INTERVAL_MS;
    },
  });

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

  const waitingForToday = !isLoading && !isError && weather && !gotToday && !exhaustedRetries;

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

  const stationCode = weather[0]?.station_code || "N/D";

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 space-y-4">
      {stalePopup}
      {/* Header */}
      <div className="flex justify-between items-center border-b border-[#f0ece2] pb-3">
        <div className="flex items-center gap-2">
          <CloudSunIcon className="w-[18px] h-[18px] text-[#3a4a42]" />
          <h3 className="text-sm font-bold text-[#24302a] m-0">
            Registros climáticos diario (SiAR)
          </h3>
        </div>
        <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-[#f4f2eb] text-[#3a4a42]">
          Estación: {stationCode}
        </span>
      </div>

      {/* Table container */}
      <div className="overflow-x-auto max-h-[300px] overflow-y-auto pr-1">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-[#f0ece2] text-[#6b7a70]">
              <th className="pb-2 font-bold uppercase text-[9px] tracking-wider">Fecha</th>
              <th className="pb-2 font-bold uppercase text-[9px] tracking-wider text-center">
                Temp. (°C)
              </th>
              <th className="pb-2 font-bold uppercase text-[9px] tracking-wider text-center">
                Mín/Máx
              </th>
              <th className="pb-2 font-bold uppercase text-[9px] tracking-wider text-center">
                Hum. (%)
              </th>
              <th className="pb-2 font-bold uppercase text-[9px] tracking-wider text-center">
                Hum. Mín/Máx
              </th>
              <th className="pb-2 font-bold uppercase text-[9px] tracking-wider text-center">
                Lluvia (mm)
              </th>
              <th className="pb-2 font-bold uppercase text-[9px] tracking-wider text-center">
                ETo (mm/d)
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
                  {row.air_temp !== null ? `${row.air_temp.toFixed(1)}°` : "no hay datos"}
                </td>
                <td className="py-2.5 text-center text-[#6b7a70]">
                  {row.air_temp_min !== null && row.air_temp_max !== null ? (
                    <span>
                      {row.air_temp_min.toFixed(0)}° / {row.air_temp_max.toFixed(0)}°
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
