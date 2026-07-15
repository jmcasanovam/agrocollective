import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Farm, FarmCreate } from "../types";

export function useCreateFarm() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (farmData: FarmCreate) => {
      const { data } = await apiClient.post<Farm>("/farms", farmData);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["farms"] });
    },
  });
}
