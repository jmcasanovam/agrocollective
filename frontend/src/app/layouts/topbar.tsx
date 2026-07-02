"use client";

import Link from "next/link";
import { useFarmStore } from "@/features/farms/stores/farm";
import { useRegions } from "@/features/farms/api/get-regions";
import { useAuthStore } from "@/features/auth/stores/auth";

export function Topbar() {
  const selectedFarm = useFarmStore((state) => state.selectedFarm);
  const { data: regions } = useRegions();
  const user = useAuthStore((state) => state.user);

  const region = regions?.find((r) => r.id === selectedFarm?.region_id);
  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : "US";

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
        {/* System status badge */}
        <div className="inline-flex items-center gap-[7px] h-[30px] px-3 bg-[#e3efdd] rounded-full text-xs font-semibold text-[#35663f]">
          <span className="w-[7px] h-[7px] rounded-full bg-[#3d9a52] inline-block" />
          Sistema operativo
        </div>

        {/* Notification bell */}
        <button className="relative w-[34px] h-[34px] rounded-[9px] flex items-center justify-center cursor-pointer bg-transparent border-none hover:bg-[#f0ede4] transition-colors">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#4a5a51"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.268 21a2 2 0 0 0 3.464 0" />
            <path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326" />
          </svg>
          <span className="absolute top-[6px] right-[7px] w-[7px] h-[7px] bg-[#d24b43] rounded-full border-[1.5px] border-[#fbfaf6]" />
        </button>

        {/* User avatar */}
        <div className="w-[34px] h-[34px] rounded-full bg-[#cbdcc4] text-[#2f5d3f] flex items-center justify-center text-[13px] font-bold">
          {initials}
        </div>
      </div>
    </header>
  );
}
