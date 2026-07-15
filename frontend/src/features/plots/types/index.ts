export interface Crop {
  id: string;
  name: string;
  description: string | null;
}

export interface Soil {
  id: string;
  name: string;
  description: string | null;
}

export interface Plot {
  id: string;
  farm_id: string;
  crop_id: string;
  soil_id: string;
  name: string;
  area_ha: number | null;
  management_profile: string | null;
  hash_plot: string | null;
}

export interface PlotCreate {
  crop_id: string;
  soil_id: string;
  name: string;
  area_ha?: number | null;
  management_profile?: string | null;
}

export interface PlotUpdate {
  crop_id?: string;
  soil_id?: string;
  name?: string;
  area_ha?: number | null;
  management_profile?: string | null;
}

export type SensorKey = "soil_humidity" | "soil_temp" | "air_temp" | "air_humidity";

export interface SensorReadingPoint {
  sensor: SensorKey;
  value: number;
  recorded_at: string;
}

export interface IrrigationRecord {
  id: string;
  plot_id: string;
  week_start: string;
  irrigation_mm: number;
  created_at: string;
}

export interface IrrigationCreate {
  week_start: string;
  irrigation_mm: number;
}

export interface Harvest {
  id: string;
  plot_id: string;
  harvest_date: string;
  yield_kg_ha: number | null;
  water_consumed_m3_ha: number | null;
  created_at: string;
}

export interface HarvestCreate {
  harvest_date: string;
  yield_kg_ha: number | null;
  water_consumed_m3_ha: number | null;
}

export type RecommendationCategory = "anomaly" | "prediction" | "benchmark";
export type RecommendationPriority = "high" | "medium" | "low";

export interface Recommendation {
  id: string;
  plot_id: string;
  run_date: string;
  category: RecommendationCategory;
  priority: RecommendationPriority;
  title: string;
  body: string;
}

export interface AnomalyRecord {
  id: string;
  plot_id: string;
  run_date: string;
  cluster_id: number;
  lof_score: number;
  is_anomaly: boolean;
  anomalous_features: string[];
}

export interface AnaloguePlot {
  id: string;
  plot_id: string;
  analogue_plot_id: string;
  run_date: string;
  rank: number;
  distance: number;
  same_cluster: boolean;
}

export type MlPredictionTarget = "yield_kg_ha" | "water_efficiency";

export interface MlPrediction {
  id: string;
  plot_id: string;
  run_date: string;
  cluster_id: number;
  target: MlPredictionTarget;
  predicted_value: number | null;
  model_r2: number | null;
  n_training_samples: number;
}

export interface PerformanceHistoryEntry {
  id: string;
  plot_id: string;
  run_date: string;
  cluster_id: number;
  avg_soil_humidity: number | null;
  avg_air_temp: number | null;
  avg_soil_temp: number | null;
  avg_air_humidity: number | null;
  irrigation_frequency: number | null;
  avg_irrigation_mm: number | null;
  total_water_mm: number | null;
  yield_kg_ha: number | null;
  water_efficiency: number | null;
  is_anomaly: boolean;
  lof_score: number | null;
  predicted_yield: number | null;
  predicted_efficiency: number | null;
  n_recommendations: number;
  n_high_priority: number;
}
