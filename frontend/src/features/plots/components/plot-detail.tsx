"use client";

import Link from "next/link";
import { usePlot } from "../api/get-plot";
import { useCrops, useSoils } from "../api/get-catalog";
import { PlotWeatherCard } from "./plot-weather-card";
import { PlotSensorsCard } from "./plot-sensors-card";
import { PlotIrrigationHarvestCard } from "./plot-irrigation-harvest-card";
import { PlotIntelligenceCard } from "./plot-intelligence-card";
interface PlotDetailProps {
  farmId: string | null;
  plotId: string;
  deviceEl?: React.ReactNode;
}

export function PlotDetail({ farmId, plotId, deviceEl }: PlotDetailProps) {
  const { data: plot, isLoading: isPlotLoading, isError } = usePlot({ farmId, plotId });
  const { data: crops } = useCrops();
  const { data: soils } = useSoils();

  if (isPlotLoading) {
    return (
      <div className="p-8 text-center">
        <div className="w-8 h-8 rounded-full border-4 border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-2" />
        <p className="text-xs text-[#6b7a70]">Cargando detalle de la parcela...</p>
      </div>
    );
  }

  if (isError || !plot) {
    return (
      <div className="p-8 text-center bg-white rounded-2xl border border-red-100 text-red-600 text-sm">
        No se ha podido cargar la parcela o no existe.
      </div>
    );
  }

  const crop = crops?.find((c) => c.id === plot.crop_id);
  const soil = soils?.find((s) => s.id === plot.soil_id);

  return (
    <div className="space-y-6">
      {/* Header breadcrumbs */}
      <div>
        <div className="flex items-center gap-2 text-xs text-[#6b7a70] mb-1">
          <Link href="/plots" className="hover:underline">
            Parcelas
          </Link>
          <span>&gt;</span>
          <span className="text-[#24302a] font-medium">{plot.name}</span>
        </div>
        <h2 className="text-xl font-bold text-[#24302a]">{plot.name}</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Column: Properties & IoT device (sticky on large screens) */}
        <div className="lg:col-span-1 space-y-6 lg:sticky lg:top-6">
          {/* Metadata Card */}
          <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 space-y-4">
            <h3 className="text-sm font-bold text-[#24302a] border-b border-[#f0ede6] pb-2">
              Propiedades agronómicas
            </h3>
            <div className="space-y-3">
              <div>
                <span className="block text-[10px] text-[#6b7a70] uppercase font-bold">
                  Cultivo
                </span>
                <span className="text-sm font-semibold text-[#24302a]">
                  {crop?.name || "No especificado"}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-[#6b7a70] uppercase font-bold">
                  Tipo de suelo
                </span>
                <span className="text-sm font-semibold text-[#24302a]">
                  {soil?.name || "No especificado"}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-[#6b7a70] uppercase font-bold">
                  Superficie
                </span>
                <span className="text-sm font-semibold text-[#24302a]">
                  {plot.area_ha ? `${plot.area_ha} ha` : "No especificada"}
                </span>
              </div>
              <div>
                <span className="block text-[10px] text-[#6b7a70] uppercase font-bold">
                  Hash anónimo
                </span>
                <span className="text-xs font-mono text-[#6b7a70] break-all bg-[#f4f2eb] px-1.5 py-0.5 rounded">
                  {plot.hash_plot || "No asignado"}
                </span>
              </div>
            </div>
          </div>

          {/* IoT Device Block (Flow 3) injected from app zone */}
          {deviceEl}
        </div>

        {/* Right Column: Placeholders for flows 4-6 */}
        <div className="lg:col-span-2 space-y-6">
          {/* Flow 4: real-time sensor readings (Telemetría) */}
          <PlotSensorsCard plotId={plotId} />

          {/* Flow 6: nightly intelligence pipeline results */}
          <PlotIntelligenceCard plotId={plotId} />

          {/* Flow 5: irrigation and harvest records */}
          <PlotIrrigationHarvestCard plotId={plotId} />

          {/* SiAR Climate Records */}
          <PlotWeatherCard plotId={plotId} />
        </div>
      </div>
    </div>
  );
}
