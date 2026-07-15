import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { User } from "../types";

export function useRegister() {
  return useMutation({
    mutationFn: async (userData: Record<string, string>) => {
      const { data } = await apiClient.post<User>("/auth/register", userData);
      return data;
    },
  });
}
