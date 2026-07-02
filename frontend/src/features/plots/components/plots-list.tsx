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
        <div className="w-6 h-6 rounded-full border-[3px] border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
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
    <div className="max-w-[1120px] mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#24302a] tracking-tight m-0 mb-1">
            Parcelas de {selectedFarm.name}
          </h1>
          <p className="text-sm text-[#6b7a70] m-0">
            Cada parcela tiene un nodo ESP32 y su propio análisis agronómico.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="h-10 px-4 border-none rounded-[9px] bg-[#2f5d3f] text-white text-sm font-semibold cursor-pointer hover:bg-[#264b33] transition-colors inline-flex items-center gap-2"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#fff"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M5 12h14" />
            <path d="M12 5v14" />
          </svg>
          Nueva parcela
        </button>
      </div>

      {/* Plot cards */}
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
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6" />
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
        <div className="flex flex-col gap-3.5">
          {plots.map((plot) => (
            <PlotCard key={plot.id} plot={plot} />
          ))}
        </div>
      )}

      <PlotFormModal
        farmId={selectedFarm.id}
        farmName={selectedFarm.name}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}
