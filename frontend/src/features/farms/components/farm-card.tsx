"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Farm } from "../types";
import { useFarmStore } from "../stores/farm";
import { useRegions } from "../api/get-regions";

interface FarmCardProps {
  farm: Farm;
  onClick: () => void;
}

export function FarmCard({ farm, onClick }: FarmCardProps) {
  const selectedFarmId = useFarmStore((state) => state.selectedFarmId);
  const { data: regions } = useRegions();

  const { data: plots } = useQuery({
    queryKey: ["farms", farm.id, "plots"],
    queryFn: async () => {
      const { data } = await apiClient.get<unknown[]>(`/farms/${farm.id}/plots`);
      return data;
    },
  });

  const region = regions?.find((r) => r.id === farm.region_id);
  const plotCount = plots?.length ?? 0;
  const isSelected = selectedFarmId === farm.id;

  return (
    <div
      onClick={onClick}
      className={`p-6 rounded-2xl bg-white border cursor-pointer hover:shadow-md hover:border-[#2f5d3f]/30 active:scale-[0.99] transition-all flex flex-col justify-between h-[170px] ${
        isSelected ? "border-[#2f5d3f] ring-2 ring-[#2f5d3f]/10" : "border-[#d9d3c5]/60"
      }`}
    >
      <div>
        <div className="flex justify-between items-start mb-2">
          <h4 className="text-lg font-bold text-[#24302a] leading-snug">{farm.name}</h4>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#edf5ef] text-[#2f5d3f]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4ab46b] animate-pulse" />
            Salud · Óptima
          </span>
        </div>
        <p className="text-xs text-[#6b7a70]">
          {region ? `${region.name} (${region.code})` : "Sin región asignada"}
        </p>
      </div>

      <div className="flex justify-between items-center pt-4 border-t border-[#f0ede6]">
        <div className="text-xs text-[#6b7a70]">
          Superficie:{" "}
          <strong className="text-[#3a4a42]">{farm.area_ha ? `${farm.area_ha} ha` : "--"}</strong>
        </div>
        <div className="text-xs text-[#6b7a70]">
          Parcelas: <strong className="text-[#3a4a42]">{plotCount}</strong>
        </div>
      </div>
    </div>
  );
}
