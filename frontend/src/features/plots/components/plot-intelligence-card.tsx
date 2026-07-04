"use client";

import { useState } from "react";
import { useRecommendations } from "../api/get-recommendations";
import { useAnomalies } from "../api/get-anomalies";
import { useAnalogues } from "../api/get-analogues";
import { useMlPredictions } from "../api/get-ml-predictions";
import { usePerformanceHistory } from "../api/get-performance-history";
import { buildLinePath } from "@/lib/svg-line";
import {
  BrainIcon,
  LightbulbIcon,
  AlertTriangleIcon,
  LinkIcon,
  BotIcon,
  TrendingUpIcon,
} from "@/components/icons/card-icons";
import type { RecommendationPriority } from "../types";

interface PlotIntelligenceCardProps {
  plotId: string;
}

type Tab = "recommendations" | "anomalies" | "analogues" | "predictions" | "history";

const TABS: {
  key: Tab;
  label: string;
  icon: (props: { className?: string }) => React.JSX.Element;
}[] = [
  { key: "recommendations", label: "Recomendaciones", icon: LightbulbIcon },
  { key: "anomalies", label: "Anomalías", icon: AlertTriangleIcon },
  { key: "analogues", label: "Parcelas análogas", icon: LinkIcon },
  { key: "predictions", label: "Predicción ML", icon: BotIcon },
  { key: "history", label: "Evolución", icon: TrendingUpIcon },
];

const PRIORITY_RANK: Record<RecommendationPriority, number> = { high: 0, medium: 1, low: 2 };
const PRIORITY_STYLE: Record<RecommendationPriority, { bg: string; text: string; label: string }> =
  {
    high: { bg: "bg-[#f8e5e2]", text: "text-[#b23a33]", label: "Alta" },
    medium: { bg: "bg-[#fbecd6]", text: "text-[#a8701e]", label: "Media" },
    low: { bg: "bg-[#eef0ea]", text: "text-[#5c6a5f]", label: "Baja" },
  };

const CHART_WIDTH = 480;
const CHART_HEIGHT = 90;

function formatRunDate(runDate: string) {
  return new Date(runDate).toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function PlotIntelligenceCard({ plotId }: PlotIntelligenceCardProps) {
  const [tab, setTab] = useState<Tab>("recommendations");

  const recommendations = useRecommendations(plotId);
  const anomalies = useAnomalies(plotId);
  const analogues = useAnalogues(plotId);
  const mlPredictions = useMlPredictions(plotId);
  const performanceHistory = usePerformanceHistory(plotId, 90);

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 space-y-5">
      <div className="flex items-center gap-2 border-b border-[#f0ece2] pb-3">
        <BrainIcon className="w-[18px] h-[18px] text-[#3a4a42]" />
        <h3 className="text-sm font-bold text-[#24302a] m-0">Inteligencia colectiva</h3>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11.5px] font-semibold transition-colors ${
                tab === t.key
                  ? "bg-[#2f5d3f] text-white"
                  : "bg-[#f4f2eb] text-[#6b7a70] hover:bg-[#eae7db]"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === "recommendations" && (
        <RecommendationsTab
          isLoading={recommendations.isLoading}
          isError={recommendations.isError}
          data={recommendations.data}
        />
      )}

      {tab === "anomalies" && (
        <AnomaliesTab
          isLoading={anomalies.isLoading}
          isError={anomalies.isError}
          data={anomalies.data}
        />
      )}

      {tab === "analogues" && (
        <AnaloguesTab
          isLoading={analogues.isLoading}
          isError={analogues.isError}
          data={analogues.data}
        />
      )}

      {tab === "predictions" && (
        <PredictionsTab
          isLoading={mlPredictions.isLoading}
          isError={mlPredictions.isError}
          data={mlPredictions.data}
        />
      )}

      {tab === "history" && (
        <HistoryTab
          isLoading={performanceHistory.isLoading}
          isError={performanceHistory.isError}
          data={performanceHistory.data}
        />
      )}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <p className="text-xs text-[#9aa79d] text-center py-6">{message}</p>;
}

function LoadingState() {
  return (
    <div className="text-center py-6">
      <div className="w-6 h-6 rounded-full border-[3px] border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
      <p className="text-xs text-[#6b7a70]">Cargando...</p>
    </div>
  );
}

function ErrorState() {
  return (
    <p className="text-xs text-red-600 text-center py-6">Error al cargar los datos del pipeline.</p>
  );
}

function RecommendationsTab({
  isLoading,
  isError,
  data,
}: {
  isLoading: boolean;
  isError: boolean;
  data: ReturnType<typeof useRecommendations>["data"];
}) {
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState />;
  if (!data || data.length === 0) {
    return (
      <EmptyState message="Sin recomendaciones. La parcela está dentro de los parámetros esperados." />
    );
  }

  const sorted = [...data].sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]);

  return (
    <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
      {sorted.map((rec) => {
        const style = PRIORITY_STYLE[rec.priority];
        return (
          <div key={rec.id} className="border border-[#f0ece2] rounded-xl p-3.5 space-y-1.5">
            <div className="flex items-center justify-between gap-2">
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${style.bg} ${style.text}`}
              >
                {style.label}
              </span>
              <span className="text-[10px] text-[#9aa79d] uppercase tracking-wide">
                {rec.category}
              </span>
            </div>
            <h5 className="text-[13px] font-bold text-[#24302a] m-0">{rec.title}</h5>
            <p className="text-[12px] text-[#6b7a70] m-0">{rec.body}</p>
            <p className="text-[10px] text-[#b7bfb4] m-0">
              Última actualización: {formatRunDate(rec.run_date)}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function AnomaliesTab({
  isLoading,
  isError,
  data,
}: {
  isLoading: boolean;
  isError: boolean;
  data: ReturnType<typeof useAnomalies>["data"];
}) {
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState />;
  if (!data || data.length === 0) {
    return <EmptyState message="Sin historial de anomalías todavía." />;
  }

  return (
    <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
      {data.map((anomaly) => (
        <div key={anomaly.id} className="border border-[#f0ece2] rounded-xl p-3.5 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11.5px] font-semibold text-[#3a4a42]">
              {formatRunDate(anomaly.run_date)}
            </span>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                anomaly.is_anomaly ? "bg-[#f8e5e2] text-[#b23a33]" : "bg-[#e3efdd] text-[#356440]"
              }`}
            >
              {anomaly.is_anomaly ? "Anómala" : "Normal"}
            </span>
          </div>
          <div className="flex justify-between text-[11.5px] text-[#6b7a70]">
            <span>LOF score</span>
            <span className="font-mono font-semibold text-[#24302a]">
              {anomaly.lof_score.toFixed(2)}
            </span>
          </div>
          {anomaly.anomalous_features.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {anomaly.anomalous_features.map((feature) => (
                <span
                  key={feature}
                  className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#f4f2eb] text-[#6b7a70]"
                >
                  {feature}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function AnaloguesTab({
  isLoading,
  isError,
  data,
}: {
  isLoading: boolean;
  isError: boolean;
  data: ReturnType<typeof useAnalogues>["data"];
}) {
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState />;
  if (!data || data.length === 0) {
    return (
      <EmptyState message="Aún no hay suficientes parcelas en la red para calcular análogas." />
    );
  }

  const sorted = [...data].sort((a, b) => a.rank - b.rank);

  return (
    <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
      {sorted.map((analogue) => (
        <div
          key={analogue.id}
          className="flex items-center justify-between border border-[#f0ece2] rounded-xl p-3.5"
        >
          <div>
            <span className="text-[13px] font-bold text-[#24302a]">
              Parcela análoga #{analogue.rank}
            </span>
            <p className="text-[10.5px] text-[#9aa79d] m-0">
              {analogue.same_cluster ? "Mismo grupo K-Means" : "Grupo distinto"}
            </p>
          </div>
          <span className="text-[11.5px] font-mono font-semibold text-[#2f5d3f]">
            distancia {analogue.distance.toFixed(3)}
          </span>
        </div>
      ))}
    </div>
  );
}

function PredictionsTab({
  isLoading,
  isError,
  data,
}: {
  isLoading: boolean;
  isError: boolean;
  data: ReturnType<typeof useMlPredictions>["data"];
}) {
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState />;
  if (!data || data.length === 0) {
    return <EmptyState message="El modelo aún no ha generado predicciones para esta parcela." />;
  }

  const labels: Record<string, { title: string; unit: string }> = {
    yield_kg_ha: { title: "Rendimiento esperado", unit: "kg/ha" },
    water_efficiency: { title: "Eficiencia hídrica esperada", unit: "kg/m³" },
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {data.map((prediction) => {
        const label = labels[prediction.target] ?? { title: prediction.target, unit: "" };
        return (
          <div key={prediction.id} className="border border-[#f0ece2] rounded-xl p-4 space-y-2">
            <h5 className="text-xs font-bold text-[#6b7a70] uppercase tracking-wide m-0">
              {label.title}
            </h5>
            <p className="text-2xl font-bold text-[#24302a] m-0">
              {prediction.predicted_value !== null
                ? `${prediction.predicted_value.toFixed(1)} ${label.unit}`
                : "Sin dato"}
            </p>
            <p className="text-[11px] text-[#9aa79d] m-0">
              {prediction.model_r2 !== null
                ? `R² del modelo: ${prediction.model_r2.toFixed(2)} · ${prediction.n_training_samples} parcelas de entrenamiento`
                : "Modelo aún sin suficientes datos de entrenamiento"}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function HistoryTab({
  isLoading,
  isError,
  data,
}: {
  isLoading: boolean;
  isError: boolean;
  data: ReturnType<typeof usePerformanceHistory>["data"];
}) {
  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState />;
  if (!data || data.length < 2) {
    return (
      <EmptyState message="Se necesitan al menos dos ejecuciones del pipeline para mostrar evolución." />
    );
  }

  const chronological = [...data].reverse();

  const metrics: {
    key: keyof (typeof chronological)[number];
    label: string;
    unit: string;
    color: string;
  }[] = [
    { key: "yield_kg_ha", label: "Rendimiento", unit: "kg/ha", color: "#2f5d3f" },
    { key: "water_efficiency", label: "Eficiencia hídrica", unit: "kg/m³", color: "#3a6ea5" },
    { key: "avg_soil_humidity", label: "Humedad media de suelo", unit: "%", color: "#8a5b52" },
  ];

  return (
    <div className="space-y-5 max-h-[400px] overflow-y-auto pr-1">
      {metrics.map((metric) => {
        const values = chronological.map((entry) => entry[metric.key] as number | null);
        const path = buildLinePath(values, CHART_WIDTH, CHART_HEIGHT);
        const lastValue = [...values].reverse().find((v) => v !== null);

        return (
          <div key={metric.key}>
            <div className="flex justify-between items-baseline mb-1">
              <span className="text-[11.5px] font-semibold text-[#3a4a42]">{metric.label}</span>
              <span className="text-[11.5px] font-mono font-bold text-[#24302a]">
                {lastValue !== undefined && lastValue !== null
                  ? `${lastValue.toFixed(1)} ${metric.unit}`
                  : "sin dato"}
              </span>
            </div>
            {path ? (
              <svg
                viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
                className="w-full h-[90px]"
                preserveAspectRatio="none"
              >
                <path
                  d={path}
                  fill="none"
                  stroke={metric.color}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <p className="text-[11px] text-[#9aa79d]">
                Datos insuficientes para graficar esta métrica.
              </p>
            )}
          </div>
        );
      })}
      <p className="text-[10px] text-[#b7bfb4] text-right">
        Última ejecución: {formatRunDate(chronological[chronological.length - 1].run_date)}
      </p>
    </div>
  );
}
