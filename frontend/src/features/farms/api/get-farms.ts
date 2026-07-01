import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Farm } from "../types";
import { useFarmStore } from "../stores/farm";
import { useEffect } from "react";

export function useFarms() {
  const initSelectedFarm = useFarmStore((state) => state.initSelectedFarm);

  const query = useQuery({
    queryKey: ["farms"],
    queryFn: async () => {
      const { data } = await apiClient.get<Farm[]>("/farms");
      return data;
    },
  });

  useEffect(() => {
    if (query.data) {
      initSelectedFarm(query.data);
    }
  }, [query.data, initSelectedFarm]);

  return query;
}
