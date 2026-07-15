import { create } from "zustand";
import type { Farm } from "../types";

interface FarmState {
  selectedFarmId: string | null;
  selectedFarm: Farm | null;
  selectFarm: (farm: Farm) => void;
  clearSelectedFarm: () => void;
  initSelectedFarm: (farms: Farm[]) => void;
}

export const useFarmStore = create<FarmState>((set) => {
  // Synchronous client-side check to load immediately on page refresh
  let initialId: string | null = null;
  let initialFarm: Farm | null = null;
  if (typeof window !== "undefined") {
    initialId = sessionStorage.getItem("selected_farm_id");
    const storedFarm = sessionStorage.getItem("selected_farm_json");
    if (storedFarm) {
      try {
        initialFarm = JSON.parse(storedFarm);
      } catch {
        // ignore
      }
    }
  }

  return {
    selectedFarmId: initialId,
    selectedFarm: initialFarm,

    selectFarm: (farm) => {
      sessionStorage.setItem("selected_farm_id", farm.id);
      sessionStorage.setItem("selected_farm_json", JSON.stringify(farm));
      set({ selectedFarmId: farm.id, selectedFarm: farm });
    },

    clearSelectedFarm: () => {
      sessionStorage.removeItem("selected_farm_id");
      sessionStorage.removeItem("selected_farm_json");
      set({ selectedFarmId: null, selectedFarm: null });
    },

    initSelectedFarm: (farms) => {
      if (typeof window === "undefined") return;
      const storedId = sessionStorage.getItem("selected_farm_id");
      if (storedId) {
        const farm = farms.find((f) => f.id === storedId);
        if (farm) {
          sessionStorage.setItem("selected_farm_json", JSON.stringify(farm));
          set({ selectedFarmId: storedId, selectedFarm: farm });
        } else {
          sessionStorage.removeItem("selected_farm_id");
          sessionStorage.removeItem("selected_farm_json");
          set({ selectedFarmId: null, selectedFarm: null });
        }
      }
    },
  };
});
