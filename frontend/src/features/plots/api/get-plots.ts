import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";

import type { PlotsResponse } from "../types";

export const plotsKeys = {
  all: ["plots"] as const,
  list: (params?: Record<string, unknown>) => [...plotsKeys.all, "list", params] as const,
};

async function fetchPlots(): Promise<PlotsResponse> {
  const { data } = await apiClient.get<PlotsResponse>("/api/v1/plots");
  return data;
}

export function usePlots() {
  return useQuery({
    queryKey: plotsKeys.list(),
    queryFn: fetchPlots,
  });
}
