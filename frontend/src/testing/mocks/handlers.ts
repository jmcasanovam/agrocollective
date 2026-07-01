import { http, HttpResponse } from "msw";

import type { PlotsResponse } from "@/features/plots/types";

const MOCK_PLOTS: PlotsResponse = {
  items: [
    {
      id: "p001",
      farm_id: "f001",
      name: "Parcela 001",
      crop_type: "olivo",
      region_code: "VALENCIA",
      area_ha: 2.5,
      created_at: "2025-01-01T00:00:00Z",
    },
    {
      id: "p002",
      farm_id: "f001",
      name: "Parcela 002",
      crop_type: "tomate",
      region_code: "VALENCIA",
      area_ha: 1.0,
      created_at: "2025-01-01T00:00:00Z",
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

export const handlers = [
  http.get("*/api/v1/plots", () => {
    return HttpResponse.json(MOCK_PLOTS);
  }),
];
