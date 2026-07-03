"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useCrops, useSoils } from "../api/get-catalog";
import type { Plot } from "../types";

interface MiniDevice {
  is_active: boolean;
  code: string | null;
}

interface PlotCardProps {
  plot: Plot;
}

export function PlotCard({ plot }: PlotCardProps) {
  const { data: crops } = useCrops();
  const { data: soils } = useSoils();

  const { data: device } = useQuery({
    queryKey: ["plots", plot.id, "devices"],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get<MiniDevice>(`/plots/${plot.id}/devices`);
        return data;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
        if (err.response?.status === 404) return null;
        throw err;
      }
    },
  });

  const crop = crops?.find((c) => c.id === plot.crop_id);
  const soil = soils?.find((s) => s.id === plot.soil_id);

  // Status: derive from device presence / activity
  const hasDevice = !!device;
  const isActive = device?.is_active ?? false;

  return (
    <Link
      href={`/plots/${plot.id}`}
      className="bg-white border border-[#e7e2d6] rounded-[14px] shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-[18px_20px] flex items-center gap-5 no-underline hover:border-[#bcd3b6] hover:shadow-[0_6px_16px_rgba(47,93,63,0.09)] transition-all cursor-pointer"
    >
      {/* Icon */}
      <div
        className={`w-[46px] h-[46px] rounded-xl flex items-center justify-center shrink-0 ${
          hasDevice && isActive ? "bg-[#eef3ea]" : "bg-[#f7f6f0]"
        }`}
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke={hasDevice && isActive ? "#2f5d3f" : "#8a978d"}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6" />
        </svg>
      </div>

      {/* Name + meta */}
      <div className="min-w-[180px]">
        <div className="text-[15.5px] font-bold text-[#24302a]">{plot.name}</div>
        <div className="text-xs text-[#8a978d]">
          {crop?.name ?? "no hay datos"} · {soil?.name ?? "no hay datos"} ·{" "}
          {plot.area_ha ? `${plot.area_ha} ha` : "no hay datos"}
        </div>
      </div>

      {/* Middle data columns */}
      <div className="flex gap-[26px] ml-2">
        <div>
          <div className="text-[11px] text-[#9aa79d]">Perfil de riego</div>
          <div className="text-[13px] font-semibold text-[#3a4a42]">
            {plot.management_profile || "Secano"}
          </div>
        </div>
        <div>
          <div className="text-[11px] text-[#9aa79d]">Dispositivo</div>
          <div className="text-[13px] font-semibold text-[#3a4a42] font-mono">
            {device?.code ?? "no hay datos"}
          </div>
        </div>
      </div>

      {/* Status badge + arrow */}
      <div className="ml-auto flex items-center gap-3.5">
        <span
          className={`text-[11.5px] font-semibold px-[11px] py-1 rounded-full ${
            hasDevice && isActive
              ? "bg-[#e3efdd] text-[#356440]"
              : hasDevice
                ? "bg-[#f7ecd6] text-[#9c6114]"
                : "bg-[#f0ede6] text-[#8a978d]"
          }`}
        >
          {hasDevice && isActive ? "Activo" : hasDevice ? "Inactivo" : "Sin dispositivo"}
        </span>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#c3ccbf"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m9 18 6-6-6-6" />
        </svg>
      </div>
    </Link>
  );
}
