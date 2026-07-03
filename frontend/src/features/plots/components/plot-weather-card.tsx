"use client";

import { usePlotWeather } from "../api/get-plot-weather";

interface PlotWeatherCardProps {
  plotId: string;
}

export function PlotWeatherCard({ plotId }: PlotWeatherCardProps) {
  const { data: weather, isLoading, isError } = usePlotWeather(plotId);

  if (isLoading) {
    return (
      <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 text-center">
        <div className="w-6 h-6 rounded-full border-[3px] border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
        <p className="text-xs text-[#6b7a70]">Cargando datos climáticos de la estación...</p>
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
      <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 text-center text-xs text-[#6b7a70]">
        No hay registros climáticos disponibles para este sector.
      </div>
    );
  }

  const stationCode = weather[0]?.station_code || "N/D";

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 space-y-4">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-[#f0ece2] pb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🌤️</span>
          <div>
            <h3 className="text-sm font-bold text-[#24302a] m-0">
              Registros Climáticos Diario (SiAR)
            </h3>
            <p className="text-[11.5px] text-[#6b7a70] m-0">Estación meteorológica de referencia</p>
          </div>
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
