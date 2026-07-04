"use client";

import { useFarmStore } from "@/features/farms/stores/farm";
import { usePlots } from "@/features/plots/api/get-plots";
import { useFarmPerformanceSummary } from "@/features/plots/api/get-farm-performance-summary";
import { FarmLocationMap } from "@/features/farms/components/farm-location-map";
import type { PerformanceHistoryEntry } from "@/features/plots/types";

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

function deltaPct(actual: number | null, predicted: number | null): number | null {
  if (actual === null || predicted === null || predicted === 0) return null;
  return ((actual - predicted) / predicted) * 100;
}

function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  const day = String(date.getUTCDate()).padStart(2, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const year = date.getUTCFullYear();
  return `${day}/${month}/${year}`;
}

function DeltaBadge({ pct }: { pct: number | null }) {
  if (pct === null) {
    return <span className="text-xs text-[#9aa79d]">no hay datos suficientes</span>;
  }
  const isPositive = pct >= 0;
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full ${
        isPositive ? "bg-[#e3efdd] text-[#356440]" : "bg-[#f8e5e2] text-[#b23a33]"
      }`}
    >
      {isPositive ? "+" : ""}
      {pct.toFixed(1)}% vs. red
    </span>
  );
}

function EmptyCard({ message }: { message: string }) {
  return <p className="text-xs text-[#9aa79d] text-center py-6">{message}</p>;
}

export default function DashboardPage() {
  const selectedFarm = useFarmStore((state) => state.selectedFarm);

  const { data: plots } = usePlots(selectedFarm?.id ?? null);
  const plotIds = (plots ?? []).map((p) => p.id);
  const { entries, isLoading: isPerfLoading } = useFarmPerformanceSummary(plotIds);

  const hasRun = entries.length > 0;

  // Yield vs network
  const yieldEntries = entries.filter(
    (e): e is PerformanceHistoryEntry & { yield_kg_ha: number; predicted_yield: number } =>
      e.yield_kg_ha !== null && e.predicted_yield !== null,
  );
  const avgYield = average(yieldEntries.map((e) => e.yield_kg_ha));
  const avgPredictedYield = average(yieldEntries.map((e) => e.predicted_yield));
  const yieldDelta = deltaPct(avgYield, avgPredictedYield);

  // Water efficiency vs network
  const waterEntries = entries.filter(
    (
      e,
    ): e is PerformanceHistoryEntry & { water_efficiency: number; predicted_efficiency: number } =>
      e.water_efficiency !== null && e.predicted_efficiency !== null,
  );
  const avgEfficiency = average(waterEntries.map((e) => e.water_efficiency));
  const avgPredictedEfficiency = average(waterEntries.map((e) => e.predicted_efficiency));
  const efficiencyDelta = deltaPct(avgEfficiency, avgPredictedEfficiency);
  const totalWaterMm = entries.reduce((sum, e) => sum + (e.total_water_mm ?? 0), 0);

  // Alerts
  const anomalyCount = entries.filter((e) => e.is_anomaly).length;
  const totalHighPriority = entries.reduce((sum, e) => sum + e.n_high_priority, 0);
  const totalRecommendations = entries.reduce((sum, e) => sum + e.n_recommendations, 0);

  return (
    <div className="max-w-[1200px] mx-auto space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-lg text-[#5c6b62]">
          Finca seleccionada:{" "}
          <span className="font-bold text-[#24302a] tracking-tight">
            {selectedFarm?.name ?? "—"}
          </span>
        </div>
        <div className="inline-flex items-center gap-[7px] h-8 px-3.5 bg-[#eef3ea] border border-[#d8e4d3] rounded-full text-xs font-semibold text-[#35663f]">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 8v4l3 3" />
            <circle cx="12" cy="12" r="9" />
          </svg>
          {hasRun
            ? `Análisis: ${formatDate(entries[0].run_date)} · 02:00 UTC`
            : "Pipeline pendiente"}
        </div>
      </div>

      {/* Collective Intelligence banner (only until the first pipeline run) */}
      {!hasRun && !isPerfLoading && (
        <div className="bg-[#2f5d3f] text-[#eef3ea] rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#bfe0c6"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 3v18" />
              <path d="m5 8 7-5 7 5" />
              <path d="M5 8v8l7 5 7-5V8" />
            </svg>
            <div className="text-[15px] font-bold">Inteligencia colectiva</div>
          </div>
          <p className="text-[13.5px] leading-relaxed text-[#d3e3d6] m-0 mb-3.5">
            Cuando el pipeline nocturno se ejecute, aquí aparecerán las recomendaciones basadas en
            el análisis de parcelas similares de la red AgroCollective.
          </p>
          <div className="bg-white/10 rounded-[10px] p-3">
            <div className="text-[10.5px] tracking-widest uppercase text-[#a7c9ae] mb-1">
              Próximo análisis
            </div>
            <div className="text-[13.5px] font-semibold text-white">
              Hoy · 02:00 UTC: resultados disponibles por la mañana
            </div>
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[18px]">
        {/* Yield vs network */}
        <div className="flex h-full flex-col bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2f5d3f"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 3v18h18" />
              <path d="m7 12 3-3 3 3 5-5" />
            </svg>
            <h2 className="text-[15px] font-bold text-[#24302a] m-0">Rendimiento vs. red</h2>
          </div>
          <p className="text-xs text-[#8a978d] m-0 mb-4 min-h-8">
            Producción media vs. lo esperado por el modelo de la red.
          </p>
          <div>
            {isPerfLoading ? (
              <EmptyCard message="Cargando..." />
            ) : yieldEntries.length === 0 ? (
              <EmptyCard message="Sin datos de rendimiento todavía." />
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-[#24302a] font-mono">
                    {avgYield!.toFixed(0)} kg/ha
                  </span>
                  <DeltaBadge pct={yieldDelta} />
                </div>
                <p className="text-[11px] text-[#9aa79d]">
                  Red: {avgPredictedYield!.toFixed(0)} kg/ha esperados · {yieldEntries.length}{" "}
                  parcela
                  {yieldEntries.length === 1 ? "" : "s"} con datos
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Water consumption vs network */}
        <div className="flex h-full flex-col bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2f5d3f"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 2.69s-5.5 6.16-5.5 10.31a5.5 5.5 0 0 0 11 0c0-4.15-5.5-10.31-5.5-10.31Z" />
            </svg>
            <h2 className="text-[15px] font-bold text-[#24302a] m-0">Consumo de agua</h2>
          </div>
          <p className="text-xs text-[#8a978d] m-0 mb-4 min-h-8">
            Eficiencia hídrica media y agua total aplicada.
          </p>
          <div>
            {isPerfLoading ? (
              <EmptyCard message="Cargando..." />
            ) : waterEntries.length === 0 ? (
              <EmptyCard message="Sin registros de riego todavía." />
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-[#24302a] font-mono">
                    {avgEfficiency!.toFixed(2)} kg/m³
                  </span>
                  <DeltaBadge pct={efficiencyDelta} />
                </div>
                <p className="text-[11px] text-[#9aa79d]">
                  Red: {avgPredictedEfficiency!.toFixed(2)} kg/m³ esperados ·{" "}
                  {totalWaterMm.toFixed(0)} mm totales aplicados
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Active alerts */}
        <div className="flex h-full flex-col bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2f5d3f"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
            </svg>
            <h2 className="text-[15px] font-bold text-[#24302a] m-0">Alertas activas</h2>
          </div>
          <p className="text-xs text-[#8a978d] m-0 mb-4 min-h-8">
            Parcelas anómalas en el último análisis.
          </p>
          <div>
            {isPerfLoading ? (
              <EmptyCard message="Cargando..." />
            ) : !hasRun ? (
              <EmptyCard message="Sin ejecuciones del pipeline todavía." />
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-[#24302a] font-mono">
                    {anomalyCount}
                  </span>
                  <span
                    className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                      anomalyCount > 0
                        ? "bg-[#f8e5e2] text-[#b23a33]"
                        : "bg-[#e3efdd] text-[#356440]"
                    }`}
                  >
                    {anomalyCount > 0 ? "parcelas anómalas" : "todo normal"}
                  </span>
                </div>
                <p className="text-[11px] text-[#9aa79d]">
                  {anomalyCount} de {entries.length} parcela{entries.length === 1 ? "" : "s"}{" "}
                  analizada{entries.length === 1 ? "" : "s"}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Pending recommendations */}
        <div className="flex h-full flex-col bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2f5d3f"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 18h6" />
              <path d="M10 22h4" />
              <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
            </svg>
            <h2 className="text-[15px] font-bold text-[#24302a] m-0">Recomendaciones</h2>
          </div>
          <p className="text-xs text-[#8a978d] m-0 mb-4 min-h-8">
            Acciones sugeridas por el análisis nocturno.
          </p>
          <div>
            {isPerfLoading ? (
              <EmptyCard message="Cargando..." />
            ) : !hasRun ? (
              <EmptyCard message="Sin ejecuciones del pipeline todavía." />
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-[#24302a] font-mono">
                    {totalRecommendations}
                  </span>
                  <span
                    className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                      totalHighPriority > 0
                        ? "bg-[#f8e5e2] text-[#b23a33]"
                        : "bg-[#e3efdd] text-[#356440]"
                    }`}
                  >
                    {totalHighPriority} prioridad alta
                  </span>
                </div>
                <p className="text-[11px] text-[#9aa79d]">
                  recomendación{totalRecommendations === 1 ? "" : "es"} pendiente
                  {totalRecommendations === 1 ? "" : "s"} en total
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Farm location (satellite imagery centered on the farm's coordinates) */}
      {selectedFarm && (
        <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
          <h2 className="text-[15px] font-bold text-[#24302a] m-0 mb-3.5">Ubicación de la finca</h2>
          <FarmLocationMap farm={selectedFarm} />
        </div>
      )}
    </div>
  );
}
