import { create } from "zustand";
import { apiClient } from "@/lib/api-client";
import { useFarmStore } from "@/features/farms/stores/farm";
import type { User } from "../types";

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  setToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  logout: () => void;
  initAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isInitializing: true,

  setToken: (token) => {
    if (token) {
      localStorage.setItem("auth_token", token);
      set({ token, isAuthenticated: true });
    } else {
      localStorage.removeItem("auth_token");
      set({ token: null, isAuthenticated: false, user: null });
    }
  },

  setUser: (user) => set({ user }),

  logout: () => {
    get().setToken(null);
    try {
      useFarmStore.getState().clearSelectedFarm();
    } catch (e) {
      console.error("Error clearing selected farm on logout:", e);
    }
  },

  initAuth: async () => {
    if (typeof window === "undefined") {
      set({ isInitializing: false });
      return;
    }

    const token = localStorage.getItem("auth_token");
    if (!token) {
      set({ isInitializing: false });
      return;
    }

    set({ token, isAuthenticated: true });

    try {
      const { data } = await apiClient.get<User>("/auth/me");
      set({ user: data });
    } catch (error) {
      console.error("Error al inicializar sesión:", error);
      get().setToken(null);
    } finally {
      set({ isInitializing: false });
    }
  },
}));
