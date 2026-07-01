import axios from "axios";

import { env } from "@/config/env";

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auth_token");
}

export const apiClient = axios.create({
  baseURL: env.NEXT_PUBLIC_API_URL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      if (status === 401) {
        // Token expirado: limpiar sesión
        if (typeof window !== "undefined") {
          localStorage.removeItem("auth_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  },
);
