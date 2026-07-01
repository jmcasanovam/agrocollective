"use client";

import { useState } from "react";
import { FarmCard } from "./farm-card";
import { FarmFormModal } from "./farm-form-modal";
import { useFarmStore } from "../stores/farm";
import type { Farm } from "../types";

interface FarmGridProps {
  farms: Farm[];
}

export function FarmGrid({ farms }: FarmGridProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const selectFarm = useFarmStore((state) => state.selectFarm);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-[#24302a]">Mis Fincas</h2>
          <p className="text-xs text-[#6b7a70]">
            Selecciona o añade una explotación agrícola para gestionarla
          </p>
        </div>
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

      {farms.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 bg-white rounded-2xl border border-[#d9d3c5]/60 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-[#f4f2eb] flex items-center justify-center text-[#6b7a70]">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#24302a]">No tienes fincas registradas</h4>
            <p className="text-xs text-[#6b7a70] mt-1 max-w-[280px]">
              Crea tu primera explotación agrícola para empezar a asociar parcelas y sensores IoT.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="h-9 px-4 border-none rounded-lg bg-[#2f5d3f] text-white text-xs font-semibold cursor-pointer hover:bg-[#264b33] transition-colors"
          >
            Añadir finca
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {farms.map((farm) => (
            <FarmCard key={farm.id} farm={farm} onClick={() => selectFarm(farm)} />
          ))}
        </div>
      )}

      <FarmFormModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </div>
  );
}
