"use client";

import { useState } from "react";
import { useIrrigation } from "../api/get-irrigation";
import { useCreateIrrigation } from "../api/create-irrigation";
import { useHarvests } from "../api/get-harvests";
import { useCreateHarvest } from "../api/create-harvest";

interface PlotIrrigationHarvestCardProps {
  plotId: string;
}

const inputClass =
  "w-full h-9 border border-[#d9d3c5] rounded-lg px-2.5 text-[13px] text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]";

export function PlotIrrigationHarvestCard({ plotId }: PlotIrrigationHarvestCardProps) {
  const { data: irrigation, isLoading: isIrrigationLoading } = useIrrigation(plotId);
  const createIrrigation = useCreateIrrigation(plotId);

  const { data: harvests, isLoading: isHarvestsLoading } = useHarvests(plotId);
  const createHarvest = useCreateHarvest(plotId);

  const [weekStart, setWeekStart] = useState("");
  const [irrigationMm, setIrrigationMm] = useState("");
  const [irrigationError, setIrrigationError] = useState<string | null>(null);

  const [harvestDate, setHarvestDate] = useState("");
  const [yieldKgHa, setYieldKgHa] = useState("");
  const [waterConsumedM3Ha, setWaterConsumedM3Ha] = useState("");

  const handleIrrigationSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setIrrigationError(null);
    if (!weekStart || !irrigationMm) return;

    createIrrigation.mutate(
      { week_start: weekStart, irrigation_mm: Number(irrigationMm) },
      {
        onSuccess: () => {
          setWeekStart("");
          setIrrigationMm("");
        },
        onError: () => {
          setIrrigationError(
            "No se pudo guardar el riego. ¿Ya existe un registro para esa semana?",
          );
        },
      },
    );
  };

  const handleHarvestSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!harvestDate) return;

    createHarvest.mutate(
      {
        harvest_date: harvestDate,
        yield_kg_ha: yieldKgHa ? Number(yieldKgHa) : null,
        water_consumed_m3_ha: waterConsumedM3Ha ? Number(waterConsumedM3Ha) : null,
      },
      {
        onSuccess: () => {
          setHarvestDate("");
          setYieldKgHa("");
          setWaterConsumedM3Ha("");
        },
      },
    );
  };

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-6 space-y-6">
      <div className="flex items-center gap-2 border-b border-[#f0ece2] pb-3">
        <span className="text-lg">🌾</span>
        <div>
          <h3 className="text-sm font-bold text-[#24302a] m-0">Riego y cosechas</h3>
          <p className="text-[11.5px] text-[#6b7a70] m-0">
            Registros manuales que alimentan el modelo de predicción
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Irrigation */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-[#3a4a42] uppercase tracking-wide">
            Riego semanal
          </h4>
          <form onSubmit={handleIrrigationSubmit} className="space-y-2">
            <div>
              <label
                htmlFor="irrigation-week-start"
                className="block text-[11px] text-[#6b7a70] mb-1"
              >
                Semana (inicio)
              </label>
              <input
                id="irrigation-week-start"
                type="date"
                value={weekStart}
                onChange={(e) => setWeekStart(e.target.value)}
                className={inputClass}
                required
              />
            </div>
            <div>
              <label htmlFor="irrigation-mm" className="block text-[11px] text-[#6b7a70] mb-1">
                Volumen (mm)
              </label>
              <input
                id="irrigation-mm"
                type="number"
                step="0.1"
                min="0.1"
                placeholder="12.5"
                value={irrigationMm}
                onChange={(e) => setIrrigationMm(e.target.value)}
                className={inputClass}
                required
              />
            </div>
            {irrigationError && <p className="text-[11px] text-red-500">{irrigationError}</p>}
            <button
              type="submit"
              disabled={createIrrigation.isPending}
              className="w-full h-9 rounded-lg text-[13px] font-semibold text-white bg-[#2f5d3f] hover:bg-[#264b33] transition-colors disabled:opacity-60"
            >
              {createIrrigation.isPending ? "Guardando..." : "Registrar riego"}
            </button>
          </form>

          <div className="max-h-[160px] overflow-y-auto space-y-1 pr-1">
            {isIrrigationLoading && <p className="text-[11px] text-[#9aa79d]">Cargando...</p>}
            {!isIrrigationLoading && irrigation?.length === 0 && (
              <p className="text-[11px] text-[#9aa79d]">Sin registros de riego todavía.</p>
            )}
            {irrigation?.map((record) => (
              <div
                key={record.id}
                className="flex justify-between text-[11.5px] py-1.5 border-b border-[#f6f4ef] last:border-0"
              >
                <span className="text-[#6b7a70]">
                  {new Date(record.week_start).toLocaleDateString("es-ES", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
                <span className="font-semibold text-[#24302a]">{record.irrigation_mm} mm</span>
              </div>
            ))}
          </div>
        </div>

        {/* Harvest */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold text-[#3a4a42] uppercase tracking-wide">Cosecha</h4>
          <form onSubmit={handleHarvestSubmit} className="space-y-2">
            <div>
              <label htmlFor="harvest-date" className="block text-[11px] text-[#6b7a70] mb-1">
                Fecha de cosecha
              </label>
              <input
                id="harvest-date"
                type="date"
                value={harvestDate}
                onChange={(e) => setHarvestDate(e.target.value)}
                className={inputClass}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label htmlFor="harvest-yield" className="block text-[11px] text-[#6b7a70] mb-1">
                  Rendimiento (kg/ha)
                </label>
                <input
                  id="harvest-yield"
                  type="number"
                  step="1"
                  placeholder="4200"
                  value={yieldKgHa}
                  onChange={(e) => setYieldKgHa(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor="harvest-water" className="block text-[11px] text-[#6b7a70] mb-1">
                  Agua (m³/ha)
                </label>
                <input
                  id="harvest-water"
                  type="number"
                  step="0.1"
                  placeholder="350"
                  value={waterConsumedM3Ha}
                  onChange={(e) => setWaterConsumedM3Ha(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={createHarvest.isPending}
              className="w-full h-9 rounded-lg text-[13px] font-semibold text-white bg-[#2f5d3f] hover:bg-[#264b33] transition-colors disabled:opacity-60"
            >
              {createHarvest.isPending ? "Guardando..." : "Registrar cosecha"}
            </button>
          </form>

          <div className="max-h-[160px] overflow-y-auto space-y-1 pr-1">
            {isHarvestsLoading && <p className="text-[11px] text-[#9aa79d]">Cargando...</p>}
            {!isHarvestsLoading && harvests?.length === 0 && (
              <p className="text-[11px] text-[#9aa79d]">Sin cosechas registradas todavía.</p>
            )}
            {harvests?.map((harvest) => (
              <div
                key={harvest.id}
                className="flex justify-between text-[11.5px] py-1.5 border-b border-[#f6f4ef] last:border-0"
              >
                <span className="text-[#6b7a70]">
                  {new Date(harvest.harvest_date).toLocaleDateString("es-ES", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                </span>
                <span className="font-semibold text-[#24302a]">
                  {harvest.yield_kg_ha !== null ? `${harvest.yield_kg_ha} kg/ha` : "sin dato"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
