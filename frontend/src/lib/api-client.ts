import axios from "axios";

import { env } from "@/config/env";
import { getSiarPersister } from "@/lib/react-query";

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
        // Token expirado: limpiar toda la sesión (no solo el token) para que
        // el siguiente login no arranque con una finca/cache de la sesión
        // anterior todavia en sessionStorage/react-query: si no, el store
        // de fincas se inicializa con ese valor viejo antes de que el flujo
        // de login llegue a limpiarlo, y se ve un flash del directorio de
        // fincas antes del selector.
        if (typeof window !== "undefined") {
          localStorage.removeItem("auth_token");
          sessionStorage.removeItem("selected_farm_id");
          sessionStorage.removeItem("selected_farm_json");
          void getSiarPersister().removeClient();
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  },
);
