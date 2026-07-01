import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "../stores/auth";
import type { AuthResponse, User } from "../types";

export function useLogin() {
  const setToken = useAuthStore((state) => state.setToken);
  const setUser = useAuthStore((state) => state.setUser);

  return useMutation({
    mutationFn: async (credentials: Record<string, string>) => {
      const { data } = await apiClient.post<AuthResponse>("/auth/login", credentials);
      return data;
    },
    onSuccess: async (data) => {
      setToken(data.access_token);
      // Fetch user details
      const userRes = await apiClient.get<User>("/auth/me");
      setUser(userRes.data);
    },
  });
}
