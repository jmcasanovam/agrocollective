"use client";

import { useSensorsLatest } from "../api/get-sensors-latest";
import { useSensorsHistory } from "../api/get-sensors-history";
import { buildLinePath } from "@/lib/svg-line";
import type { SensorKey } from "../types";

interface PlotSensorsCardProps {
  plotId: string;
}

const SENSOR_META: Record<
  SensorKey,
  { label: string; unit: string; color: string; isPercentage: boolean }
> = {
  soil_humidity: { label: "Humedad suelo", unit: "%", color: "#2f5d3f", isPercentage: true },
  soil_temp: { label: "Temp. suelo", unit: "°C", color: "#8a5b52", isPercentage: false },
  air_temp: { label: "Temp. aire", unit: "°C", color: "#d98a2b", isPercentage: false },
  air_humidity: { label: "Humedad aire", unit: "%", color: "#3a6ea5", isPercentage: true },
};

const CHART_WIDTH = 480;
const CHART_HEIGHT = 120;

export function PlotSensorsCard({ plotId }: PlotSensorsCardProps) {
  const {
    data: latest,
    isLoading: isLatestLoading,
    isError: isLatestError,
  } = useSensorsLatest(plotId);
  const { data: history, isLoading: isHistoryLoading } = useSensorsHistory(plotId, 24);

  if (isLatestLoading) {
    return (
      <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 text-center">
        <div className="w-6 h-6 rounded-full border-[3px] border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
        <p className="text-xs text-[#6b7a70]">Cargando lecturas de sensores...</p>
      </div>
    );
  }

  if (isLatestError) {
    return (
      <div className="bg-white border border-red-100 rounded-2xl p-6 text-center text-xs text-red-600">
        Error al cargar las lecturas de sensores.
      </div>
    );
  }

  const latestBySensor = new Map((latest ?? []).map((point) => [point.sensor, point]));
  const sensorKeys = Object.keys(SENSOR_META) as SensorKey[];
  const hasAnyReading = latestBySensor.size > 0;

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 space-y-5">
      <div className="flex items-center gap-2 border-b border-[#f0ece2] pb-3">
        <span className="text-lg">📊</span>
        <div>
          <h3 className="text-sm font-bold text-[#24302a] m-0">Lecturas en tiempo real</h3>
          <p className="text-[11.5px] text-[#6b7a70] m-0">
            Humedad y temperatura del dispositivo IoT
          </p>
        </div>
      </div>

      {!hasAnyReading ? (
        <p className="text-xs text-[#6b7a70] text-center py-4">
          Aún no se han recibido lecturas del dispositivo vinculado a esta parcela.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {sensorKeys.map((key) => {
            const meta = SENSOR_META[key];
            const reading = latestBySensor.get(key);
            return (
              <div key={key} className="space-y-1.5">
                <div className="flex justify-between items-baseline text-xs">
                  <span className="text-[#6b7a70]">{meta.label}</span>
                  <span className="font-bold text-[#24302a] font-mono">
                    {reading ? `${reading.value.toFixed(1)}${meta.unit}` : "sin datos"}
                  </span>
                </div>
                {meta.isPercentage && (
                  <div className="h-2 bg-[#eef0ea] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, Math.max(0, reading?.value ?? 0))}%`,
                        backgroundColor: meta.color,
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="pt-1 border-t border-[#f0ece2]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold text-[#6b7a70] uppercase tracking-wider">
            Histórico 24 horas
          </span>
          {isHistoryLoading && <span className="text-[10px] text-[#9aa79d]">Cargando...</span>}
        </div>

        {!isHistoryLoading && (!history || history.length === 0) ? (
          <p className="text-xs text-[#9aa79d] text-center py-3">
            Sin histórico suficiente todavía.
          </p>
        ) : (
          <>
            <svg
              viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
              className="w-full h-[120px]"
              preserveAspectRatio="none"
            >
              {sensorKeys.map((key) => {
                const values = (history ?? [])
                  .filter((point) => point.sensor === key)
                  .map((point) => point.value);
                if (values.length < 2) return null;
                const path = buildLinePath(values, CHART_WIDTH, CHART_HEIGHT);
                if (!path) return null;
                return (
                  <path
                    key={key}
                    d={path}
                    fill="none"
                    stroke={SENSOR_META[key].color}
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="transition-all duration-500"
                  />
                );
              })}
            </svg>
            <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
              {sensorKeys.map((key) => (
                <div key={key} className="flex items-center gap-1.5 text-[10.5px] text-[#6b7a70]">
                  <span
                    className="w-2 h-2 rounded-full inline-block"
                    style={{ backgroundColor: SENSOR_META[key].color }}
                  />
                  {SENSOR_META[key].label}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
