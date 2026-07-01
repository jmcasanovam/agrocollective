"use client";

import { useState } from "react";
import { usePlots } from "../api/get-plots";
import { PlotCard } from "./plot-card";
import { PlotFormModal } from "./plot-form-modal";
interface PlotsListProps {
  selectedFarm?: { id: string; name: string } | null;
}

export function PlotsList({ selectedFarm }: PlotsListProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: plots, isLoading, isError, error } = usePlots(selectedFarm?.id ?? null);

  if (!selectedFarm) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-[#d9d3c5]/60">
        <p className="text-sm text-[#6b7a70]">
          Por favor, selecciona una finca para ver sus parcelas.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-8 text-center">
        <div className="w-6 h-6 rounded-full border-3 border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
        <p className="text-xs text-[#6b7a70]">Cargando parcelas...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-red-100 text-red-600 text-sm">
        Error al cargar parcelas: {error instanceof Error ? error.message : "Desconocido"}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-[#24302a]">Parcelas</h2>
          <p className="text-xs text-[#6b7a70]">
            Sectores e hidrantes bajo gestión en {selectedFarm.name}
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
          Nueva parcela
        </button>
      </div>

      {!plots || plots.length === 0 ? (
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
              <rect width="7" height="9" x="3" y="3" rx="1" />
              <rect width="7" height="5" x="14" y="3" rx="1" />
              <rect width="7" height="9" x="14" y="12" rx="1" />
              <rect width="7" height="5" x="3" y="16" rx="1" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-bold text-[#24302a]">No hay parcelas registradas</h4>
            <p className="text-xs text-[#6b7a70] mt-1 max-w-[280px]">
              Crea tu primera parcela para empezar a configurar las lecturas del suelo.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="h-9 px-4 border-none rounded-lg bg-[#2f5d3f] text-white text-xs font-semibold cursor-pointer hover:bg-[#264b33]"
          >
            Añadir parcela
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-[#d9d3c5]/60 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-[#fcfcfa] border-b border-[#d9d3c5]/60 text-[#6b7a70] text-[10px] font-bold tracking-wider uppercase">
                  <th className="py-3.5 px-4">Nombre</th>
                  <th className="py-3.5 px-4">Cultivo</th>
                  <th className="py-3.5 px-4">Perfil</th>
                  <th className="py-3.5 px-4">Superficie</th>
                  <th className="py-3.5 px-4">Dispositivo IoT</th>
                  <th className="py-3.5 px-4 text-right">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#f0ede6]">
                {plots.map((plot) => (
                  <PlotCard key={plot.id} plot={plot} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <PlotFormModal
        farmId={selectedFarm.id}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
