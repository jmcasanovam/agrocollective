"use client";

import { useFarmStore } from "@/features/farms/stores/farm";
import { useRegions } from "@/features/farms/api/get-regions";
import { useAuthStore } from "@/features/auth/stores/auth";

export function Topbar() {
  const selectedFarm = useFarmStore((state) => state.selectedFarm);
  const clearSelectedFarm = useFarmStore((state) => state.clearSelectedFarm);
  const { data: regions } = useRegions();
  const user = useAuthStore((state) => state.user);

  const region = regions?.find((r) => r.id === selectedFarm?.region_id);

  // User initials
  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : "US";

  return (
    <header className="h-16 bg-white border-b border-[#d9d3c5]/60 flex items-center justify-between px-8 font-sans">
      <div className="flex items-center gap-4">
        {selectedFarm ? (
          <>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-[#24302a]">{selectedFarm.name}</span>
                <span className="text-[10px] text-[#6b7a70] bg-[#f4f2eb] px-1.5 py-0.5 rounded-sm">
                  {region ? `${region.name} (${region.code})` : "Sin región"}
                </span>
                {selectedFarm.area_ha && (
                  <span className="text-[10px] text-[#6b7a70] bg-[#f4f2eb] px-1.5 py-0.5 rounded-sm">
                    {selectedFarm.area_ha} ha
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={clearSelectedFarm}
              className="h-7 px-2.5 border border-[#d9d3c5] rounded-md text-[10px] font-bold text-[#3a4a42] bg-white cursor-pointer hover:bg-zinc-50 transition-colors"
            >
              Cambiar finca
            </button>
          </>
        ) : (
          <span className="text-sm font-bold text-[#6b7a70]">Ninguna finca seleccionada</span>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* System Active Badging */}
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-[#edf5ef] text-[#2f5d3f]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#4ab46b]" />
          Sistema Operativo
        </span>

        {/* Notification Icon */}
        <button className="p-1.5 text-[#6b7a70] hover:text-[#24302a] bg-transparent border-none cursor-pointer relative">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-orange-500 border border-white" />
        </button>

        {/* User initials Avatar */}
        <div className="w-8 h-8 rounded-full bg-[#4f8a5b] text-white flex items-center justify-center text-xs font-bold shadow-xs">
          {initials}
        </div>
      </div>
    </header>
  );
}
