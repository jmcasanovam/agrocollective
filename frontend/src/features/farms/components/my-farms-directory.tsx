"use client";

import { useState } from "react";
import { useFarms } from "../api/get-farms";
import { usePlots } from "@/features/plots/api/get-plots";
import { useDevice } from "@/features/devices/api/get-device";
import { useCrops, useSoils } from "@/features/plots/api/get-catalog";
import { useRegions } from "../api/get-regions";
import { FarmFormModal } from "./farm-form-modal";
import type { Plot } from "@/features/plots/types";

export function MyFarmsDirectory() {
  const { data: farms, isLoading, isError } = useFarms();
  const { data: regions } = useRegions();
  const [isModalOpen, setIsModalOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-[#d9d3c5]/60">
        <div className="w-6 h-6 rounded-full border-[3px] border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
        <p className="text-xs text-[#6b7a70]">Cargando directorio de fincas...</p>
      </div>
    );
  }

  if (isError || !farms) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-red-100 text-red-600 text-sm">
        Error al cargar el directorio de fincas.
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-[1120px] mx-auto">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-bold text-[#24302a] tracking-tight m-0">
          Directorio de fincas
        </h1>
        <button
          onClick={() => setIsModalOpen(true)}
          className="h-10 px-4 border-none rounded-lg bg-[#2f5d3f] text-white text-xs font-semibold cursor-pointer hover:bg-[#264b33] transition-colors flex items-center gap-1.5"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14" />
            <path d="M12 5v14" />
          </svg>
          Nueva finca
        </button>
      </div>

      <div className="space-y-6">
        {farms.map((farm) => {
          const region = regions?.find((r) => r.id === farm.region_id);
          return (
            <div
              key={farm.id}
              className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden"
            >
              {/* Farm Header */}
              <div className="bg-[#fcfbf9] px-6 py-4 border-b border-[#e7e2d6] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <h3 className="text-base font-bold text-[#24302a] m-0">{farm.name}</h3>
                  <span className="text-xs text-[#6b7a70]">
                    Región: {region ? `${region.name} (${region.code})` : "No especificada"}
                  </span>
                </div>
                <div className="text-xs font-semibold text-[#2f5d3f] bg-[#eef5eb] px-3 py-1 rounded-full border border-[#d8e4d3] self-start sm:self-auto">
                  Superficie: {farm.area_ha ? `${farm.area_ha} ha` : "no hay datos"}
                </div>
              </div>

              {/* Plots Table */}
              <div className="p-6">
                <FarmPlotsTable farmId={farm.id} />
              </div>
            </div>
          );
        })}
      </div>

      <FarmFormModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}

function FarmPlotsTable({ farmId }: { farmId: string }) {
  const { data: plots, isLoading, isError } = usePlots(farmId);

  if (isLoading) {
    return <div className="text-xs text-[#6b7a70] italic">Cargando parcelas...</div>;
  }

  if (isError || !plots) {
    return <div className="text-xs text-red-500">Error al cargar parcelas de la finca.</div>;
  }

  if (plots.length === 0) {
    return (
      <div className="text-xs text-[#6b7a70] italic">
        No hay parcelas registradas en esta finca.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse text-xs">
        <thead>
          <tr className="border-b border-[#f0ece2] text-[#6b7a70] font-bold uppercase text-[9px] tracking-wider">
            <th className="pb-2.5">Parcela</th>
            <th className="pb-2.5">Cultivo</th>
            <th className="pb-2.5">Suelo</th>
            <th className="pb-2.5">Superficie</th>
            <th className="pb-2.5">Dispositivo</th>
            <th className="pb-2.5 text-center">Batería</th>
            <th className="pb-2.5 text-right">Estado</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#fcfbfa]">
          {plots.map((plot) => (
            <PlotRow key={plot.id} plot={plot} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlotRow({ plot }: { plot: Plot }) {
  const { data: crops } = useCrops();
  const { data: soils } = useSoils();
  const { data: device, isLoading } = useDevice(plot.id);

  const crop = crops?.find((c) => c.id === plot.crop_id);
  const soil = soils?.find((s) => s.id === plot.soil_id);

  // Battery calculations
  const batteryMv = device?.battery_mv ?? 0;
  const batteryPct = Math.min(100, Math.max(0, Math.round(((batteryMv - 3300) / 900) * 100)));
  const isOnline = device?.is_active && !!device?.last_seen_at;

  return (
    <tr className="hover:bg-[#fcfbf9] transition-colors">
      <td className="py-3 font-semibold text-[#24302a]">{plot.name}</td>
      <td className="py-3 text-[#5c6b62]">{crop?.name || "No especificado"}</td>
      <td className="py-3 text-[#5c6b62]">{soil?.name || "No especificado"}</td>
      <td className="py-3 text-[#5c6b62]">
        {plot.area_ha ? `${plot.area_ha} ha` : "no hay datos"}
      </td>
      <td className="py-3 font-mono text-[#3a4a42]">
        {isLoading ? (
          <span className="text-gray-400 italic">Cargando...</span>
        ) : device ? (
          device.code
        ) : (
          <span className="text-[#a1aba3] italic">Sin vincular</span>
        )}
      </td>
      <td className="py-3 text-center text-[#3a4a42] font-medium">
        {device && device.battery_mv !== null ? (
          <span>{batteryPct}%</span>
        ) : (
          <span className="text-gray-300">no hay datos</span>
        )}
      </td>
      <td className="py-3 text-right">
        {device ? (
          <span
            className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-semibold ${
              isOnline ? "bg-[#e3efdd] text-[#356440]" : "bg-[#f8e5e2] text-[#b23a33]"
            }`}
          >
            {isOnline ? "En línea" : "Offline"}
          </span>
        ) : (
          <span className="text-[#a1aba3] text-[10.5px] italic">no hay datos</span>
        )}
      </td>
    </tr>
  );
}
