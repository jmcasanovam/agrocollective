"use client";

import Link from "next/link";
import { useFarmStore } from "@/features/farms/stores/farm";
import { useRegions } from "@/features/farms/api/get-regions";
export function Topbar() {
  const selectedFarm = useFarmStore((state) => state.selectedFarm);
  const { data: regions } = useRegions();

  const region = regions?.find((r) => r.id === selectedFarm?.region_id);

  return (
    <header className="h-[62px] shrink-0 bg-[#fbfaf6] border-b border-[#e3ddce] flex items-center px-[26px] gap-[18px] sticky top-0 z-20 font-sans">
      {/* Farm info */}
      <div className="min-w-0">
        {selectedFarm ? (
          <>
            <div className="text-[15px] font-bold text-[#24302a] tracking-tight leading-tight">
              {selectedFarm.name}
            </div>
            <div className="text-xs text-[#7d8c82]">
              {region ? `${region.name} (${region.code})` : "Sin región"} ·{" "}
              {selectedFarm.area_ha ? `${selectedFarm.area_ha} ha` : "—"}
            </div>
          </>
        ) : (
          <div className="text-[15px] font-bold text-[#7d8c82]">Ninguna finca seleccionada</div>
        )}
      </div>

      {/* Change farm button */}
      {selectedFarm && (
        <Link
          href="/farms"
          className="ml-2 h-8 px-3.5 border border-[#d9d3c5] bg-white rounded-lg text-[13px] font-medium text-[#3a4a42] no-underline inline-flex items-center gap-1.5 hover:bg-[#f4f2ea] transition-colors"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="m8 3 4 8 5-5 5 15H2L8 3z" />
          </svg>
          Cambiar finca
        </Link>
      )}

      {/* Right side */}
      <div className="ml-auto flex items-center gap-3.5">
        {/* Removed OS badge, notification bell, and user avatar */}
      </div>
    </header>
  );
}
