import { http, HttpResponse } from "msw";
import type { Plot } from "@/features/plots/types";

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

export const handlers = [
  http.get("*/farms/:farmId/plots", () => {
    return HttpResponse.json(MOCK_PLOTS);
  }),
];
