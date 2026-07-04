"use client";

import { useRef, useState } from "react";
import { useSensorsLatest } from "../api/get-sensors-latest";
import { useSensorsHistory } from "../api/get-sensors-history";
import { buildLinePath } from "@/lib/svg-line";
import { ActivityIcon } from "@/components/icons/card-icons";
import type { SensorKey, SensorReadingPoint } from "../types";

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
const CHART_PADDING = 4;

export function PlotSensorsCard({ plotId }: PlotSensorsCardProps) {
  const {
    data: latest,
    isLoading: isLatestLoading,
    isError: isLatestError,
  } = useSensorsLatest(plotId);
  const { data: history, isLoading: isHistoryLoading } = useSensorsHistory(plotId, 24);
  const chartRef = useRef<SVGSVGElement>(null);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

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

  const seriesBySensor = sensorKeys.reduce(
    (acc, key) => {
      acc[key] = (history ?? []).filter((point) => point.sensor === key);
      return acc;
    },
    {} as Record<SensorKey, SensorReadingPoint[]>,
  );
  const pointCount = Math.max(0, ...sensorKeys.map((key) => seriesBySensor[key].length));
  const chartStep = pointCount > 1 ? (CHART_WIDTH - CHART_PADDING * 2) / (pointCount - 1) : 0;

  const handleChartMove = (event: React.MouseEvent<SVGSVGElement>) => {
    if (!chartRef.current || pointCount < 2) return;
    const rect = chartRef.current.getBoundingClientRect();
    const relX = ((event.clientX - rect.left) / rect.width) * CHART_WIDTH;
    const idx = Math.round((relX - CHART_PADDING) / chartStep);
    setHoverIndex(Math.min(pointCount - 1, Math.max(0, idx)));
  };

  const hoverTimestamp =
    hoverIndex !== null
      ? sensorKeys
          .map((key) => seriesBySensor[key][hoverIndex]?.recorded_at)
          .find((recordedAt) => !!recordedAt)
      : undefined;

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 space-y-5">
      <div className="flex items-center gap-2 border-b border-[#f0ece2] pb-3">
        <ActivityIcon className="w-[18px] h-[18px] text-[#3a4a42]" />
        <h3 className="text-sm font-bold text-[#24302a] m-0">Telemetría</h3>
      </div>

      {!hasAnyReading ? (
        <p className="text-xs text-[#6b7a70] text-center py-4">
          Aún no se han recibido lecturas del dispositivo vinculado a esta parcela.
        </p>
      ) : (
        <div className="flex flex-nowrap gap-3 overflow-x-auto pb-1">
          {sensorKeys.map((key) => {
            const meta = SENSOR_META[key];
            const reading = latestBySensor.get(key);
            const value = reading ? `${reading.value.toFixed(1)}${meta.unit}` : "—";
            return (
              <div
                key={key}
                className="flex-1 min-w-[90px] flex flex-col items-center gap-1.5 text-center"
              >
                {meta.isPercentage ? (
                  <SensorGauge
                    value={Math.min(100, Math.max(0, reading?.value ?? 0))}
                    color={meta.color}
                    label={value}
                  />
                ) : (
                  <div
                    className="w-14 h-14 rounded-full border-2 flex items-center justify-center"
                    style={{ borderColor: meta.color }}
                  >
                    <span className="text-[10px] font-bold text-[#24302a] font-mono">{value}</span>
                  </div>
                )}
                <span className="text-[11px] text-[#6b7a70]">{meta.label}</span>
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
            <div className="relative">
              <svg
                ref={chartRef}
                viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                className="w-full h-[120px] cursor-crosshair"
                preserveAspectRatio="none"
                onMouseMove={handleChartMove}
                onMouseLeave={() => setHoverIndex(null)}
              >
                {sensorKeys.map((key) => {
                  const values = seriesBySensor[key].map((point) => point.value);
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
                {hoverIndex !== null && (
                  <line
                    x1={CHART_PADDING + hoverIndex * chartStep}
                    x2={CHART_PADDING + hoverIndex * chartStep}
                    y1={0}
                    y2={CHART_HEIGHT}
                    stroke="#d9d3c5"
                    strokeWidth={1}
                  />
                )}
              </svg>

              {hoverIndex !== null && hoverTimestamp && (
                <div
                  className="absolute top-0 z-10 -translate-x-1/2 bg-white border border-[#e7e2d6] rounded-lg shadow-md px-2.5 py-1.5 text-[10.5px] whitespace-nowrap pointer-events-none"
                  style={{
                    left: `${((CHART_PADDING + hoverIndex * chartStep) / CHART_WIDTH) * 100}%`,
                  }}
                >
                  <p className="font-bold text-[#24302a] m-0 mb-1">
                    {new Date(hoverTimestamp).toLocaleString("es-ES", {
                      day: "2-digit",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                  {sensorKeys.map((key) => {
                    const point = seriesBySensor[key][hoverIndex];
                    if (!point) return null;
                    return (
                      <div key={key} className="flex items-center gap-1.5 text-[#6b7a70]">
                        <span
                          className="w-1.5 h-1.5 rounded-full inline-block"
                          style={{ backgroundColor: SENSOR_META[key].color }}
                        />
                        {SENSOR_META[key].label}:{" "}
                        <span className="font-semibold text-[#24302a] font-mono">
                          {point.value.toFixed(1)}
                          {SENSOR_META[key].unit}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
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

function SensorGauge({ value, color, label }: { value: number; color: string; label: string }) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative w-14 h-14 flex items-center justify-center">
      <svg width="56" height="56" viewBox="0 0 40 40" className="-rotate-90">
        <circle cx="20" cy="20" r={radius} fill="none" stroke="#eef0ea" strokeWidth={4} />
        <circle
          cx="20"
          cy="20"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-500"
        />
      </svg>
      <span className="absolute text-[10px] font-bold text-[#24302a] font-mono">{label}</span>
    </div>
  );
}
