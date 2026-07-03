import { http, HttpResponse } from "msw";
import type {
  AnaloguePlot,
  AnomalyRecord,
  Harvest,
  IrrigationRecord,
  MlPrediction,
  Plot,
  Recommendation,
  SensorReadingPoint,
} from "@/features/plots/types";

const MOCK_PLOTS: Plot[] = [
  {
    id: "p001",
    farm_id: "f001",
    crop_id: "crop-olivo-id",
    soil_id: "soil-franco-id",
    name: "Parcela 001",
    area_ha: 2.5,
    management_profile: "Riego deficitario controlado",
    hash_plot: "hash-001",
  },
  {
    id: "p002",
    farm_id: "f001",
    crop_id: "crop-tomate-id",
    soil_id: "soil-arenoso-id",
    name: "Parcela 002",
    area_ha: 1.0,
    management_profile: "Estándar SiAR",
    hash_plot: "hash-002",
  },
];

const MOCK_SENSORS_LATEST: SensorReadingPoint[] = [
  { sensor: "soil_humidity", value: 42.3, recorded_at: "2026-07-03T10:00:00Z" },
  { sensor: "air_temp", value: 24.1, recorded_at: "2026-07-03T10:00:00Z" },
  { sensor: "soil_temp", value: 20.5, recorded_at: "2026-07-03T10:00:00Z" },
  { sensor: "air_humidity", value: 58.2, recorded_at: "2026-07-03T10:00:00Z" },
];

const MOCK_IRRIGATION: IrrigationRecord[] = [
  {
    id: "irr-001",
    plot_id: "p001",
    week_start: "2026-06-22",
    irrigation_mm: 12.5,
    created_at: "2026-06-22T00:00:00Z",
  },
];

const MOCK_HARVESTS: Harvest[] = [
  {
    id: "harv-001",
    plot_id: "p001",
    harvest_date: "2026-06-28",
    yield_kg_ha: 4200,
    water_consumed_m3_ha: 350,
    created_at: "2026-06-28T00:00:00Z",
  },
];

// A proposito en el orden "equivocado" (medium antes que high): el componente debe
// reordenar por severidad real sin depender de que el backend ya venga ordenado.
const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    id: "rec-medium",
    plot_id: "p001",
    run_date: "2026-07-02",
    category: "benchmark",
    priority: "medium",
    title: "Recomendacion de prioridad media",
    body: "Cuerpo prioridad media",
  },
  {
    id: "rec-high",
    plot_id: "p001",
    run_date: "2026-07-02",
    category: "anomaly",
    priority: "high",
    title: "Anomalia de alta prioridad",
    body: "Cuerpo alta prioridad",
  },
];

const MOCK_ANOMALIES: AnomalyRecord[] = [
  {
    id: "anom-001",
    plot_id: "p001",
    run_date: "2026-07-02",
    cluster_id: 2,
    lof_score: 2.34,
    is_anomaly: true,
    anomalous_features: ["soil_humidity"],
  },
];

const MOCK_ANALOGUES: AnaloguePlot[] = [
  {
    id: "an-001",
    plot_id: "p001",
    analogue_plot_id: "other-user-plot-id",
    run_date: "2026-07-02",
    rank: 1,
    distance: 0.48,
    same_cluster: true,
  },
];

const MOCK_ML_PREDICTIONS: MlPrediction[] = [
  {
    id: "ml-001",
    plot_id: "p001",
    run_date: "2026-07-02",
    cluster_id: 2,
    target: "yield_kg_ha",
    predicted_value: 4100,
    model_r2: 0.74,
    n_training_samples: 10,
  },
];

export const handlers = [
  http.get("*/farms/:farmId/plots", () => {
    return HttpResponse.json(MOCK_PLOTS);
  }),
  http.get("*/plots/:plotId/sensors/latest", () => {
    return HttpResponse.json(MOCK_SENSORS_LATEST);
  }),
  http.get("*/plots/:plotId/sensors/history", () => {
    return HttpResponse.json([]);
  }),
  http.get("*/plots/:plotId/irrigation", () => {
    return HttpResponse.json(MOCK_IRRIGATION);
  }),
  http.post("*/plots/:plotId/irrigation", async ({ request }) => {
    const body = (await request.json()) as { week_start: string; irrigation_mm: number };
    return HttpResponse.json(
      { id: "irr-new", plot_id: "p001", created_at: "2026-07-03T00:00:00Z", ...body },
      { status: 201 },
    );
  }),
  http.get("*/plots/:plotId/harvests", () => {
    return HttpResponse.json(MOCK_HARVESTS);
  }),
  http.post("*/plots/:plotId/harvests", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      { id: "harv-new", plot_id: "p001", created_at: "2026-07-03T00:00:00Z", ...(body as object) },
      { status: 201 },
    );
  }),
  http.get("*/plots/:plotId/recommendations", () => {
    return HttpResponse.json(MOCK_RECOMMENDATIONS);
  }),
  http.get("*/plots/:plotId/anomalies", () => {
    return HttpResponse.json(MOCK_ANOMALIES);
  }),
  http.get("*/plots/:plotId/analogues", () => {
    return HttpResponse.json(MOCK_ANALOGUES);
  }),
  http.get("*/plots/:plotId/ml-predictions", () => {
    return HttpResponse.json(MOCK_ML_PREDICTIONS);
  }),
  http.get("*/plots/:plotId/performance-history", () => {
    return HttpResponse.json([]);
  }),
];
