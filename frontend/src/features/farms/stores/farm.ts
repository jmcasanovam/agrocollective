import { create } from "zustand";
import type { Farm } from "../types";

interface FarmState {
  selectedFarmId: string | null;
  selectedFarm: Farm | null;
  selectFarm: (farm: Farm) => void;
  clearSelectedFarm: () => void;
  initSelectedFarm: (farms: Farm[]) => void;
}

export const useFarmStore = create<FarmState>((set) => ({
  selectedFarmId: null,
  selectedFarm: null,

  selectFarm: (farm) => {
    localStorage.setItem("selected_farm_id", farm.id);
    set({ selectedFarmId: farm.id, selectedFarm: farm });
  },

  clearSelectedFarm: () => {
    localStorage.removeItem("selected_farm_id");
    set({ selectedFarmId: null, selectedFarm: null });
  },

  initSelectedFarm: (farms) => {
    if (typeof window === "undefined") return;
    const storedId = localStorage.getItem("selected_farm_id");
    if (storedId) {
      const farm = farms.find((f) => f.id === storedId);
      if (farm) {
        set({ selectedFarmId: storedId, selectedFarm: farm });
      } else {
        localStorage.removeItem("selected_farm_id");
      }
    }
  },
}));
