"use client";

import Link from "next/link";
import { usePlot } from "../api/get-plot";
import { useCrops, useSoils } from "../api/get-catalog";
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
        <div className="mt-4">
          <Link href="/plots" className="text-xs font-bold text-[#2f5d3f] hover:underline">
            &larr; Volver a parcelas
          </Link>
        </div>
      </div>
    );
  }

  const crop = crops?.find((c) => c.id === plot.crop_id);
  const soil = soils?.find((s) => s.id === plot.soil_id);

  return (
    <div className="space-y-6">
      {/* Header breadcrumbs & actions */}
      <div className="flex flex-col gap-2 md:flex-row md:justify-between md:items-center">
        <div>
          <div className="flex items-center gap-2 text-xs text-[#6b7a70] mb-1">
            <Link href="/plots" className="hover:underline">
              Parcelas
            </Link>
            <span>&rarr;</span>
            <span className="text-[#24302a] font-medium">{plot.name}</span>
          </div>
          <h2 className="text-xl font-bold text-[#24302a]">{plot.name}</h2>
        </div>
        <Link
          href="/plots"
          className="inline-flex items-center gap-1 text-xs font-bold text-[#2f5d3f] hover:underline"
        >
          &larr; Volver al listado
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Column: Properties & IoT device */}
        <div className="md:col-span-1 space-y-6">
          {/* Metadata Card */}
          <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 space-y-4">
            <h3 className="text-sm font-bold text-[#24302a] border-b border-[#f0ede6] pb-2">
              Propiedades Agronómicas
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
                  Hash Anónimo
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
        <div className="md:col-span-2 space-y-6">
          {/* Readings Card Placeholder */}
          <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 opacity-60 flex flex-col justify-between h-[180px]">
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#6b7a70] uppercase tracking-wider mb-2">
                <span>📊</span> Lecturas en tiempo real
              </div>
              <h4 className="text-md font-bold text-[#24302a] mb-1">Humedad y Temperatura</h4>
              <p className="text-xs text-[#6b7a70]">
                Los gráficos históricos, lecturas activas de sensores y alarmas de estrés hídrico se
                habilitarán una vez que el pipeline reciba telemetría del dispositivo vinculado.
              </p>
            </div>
            <div className="text-[10px] text-[#809185] italic font-semibold">
              Módulo de Lecturas de Sensores · Próximamente (Flujo 4)
            </div>
          </div>

          {/* Intelligence recommendations placeholder */}
          <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 opacity-60 flex flex-col justify-between h-[180px]">
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#6b7a70] uppercase tracking-wider mb-2">
                <span>🤖</span> Inteligencia colectiva
              </div>
              <h4 className="text-md font-bold text-[#24302a] mb-1">Recomendaciones y Clústeres</h4>
              <p className="text-xs text-[#6b7a70]">
                Análisis comparativo K-Means frente a parcelas análogas de la red, detección de
                anomalías con LOF y predicciones de necesidad de riego a 7 días.
              </p>
            </div>
            <div className="text-[10px] text-[#809185] italic font-semibold">
              Pipeline de Análisis Nocturno y Recomendaciones · Próximamente (Flujos 5 y 6)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
