"use client";

import { useFarmStore } from "@/features/farms/stores/farm";
import { useAuthStore } from "@/features/auth/stores/auth";

export default function DashboardPage() {
  const selectedFarm = useFarmStore((state) => state.selectedFarm);
  const user = useAuthStore((state) => state.user);

  const userName = user?.email?.split("@")[0] || "usuario";

  return (
    <div className="max-w-[1200px] mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-3.5">
        <div>
          <h1 className="text-2xl font-bold text-[#24302a] tracking-tight m-0 mb-1">
            Hola, {userName} 👋
          </h1>
          <p className="text-sm text-[#6b7a70] m-0">
            Resumen de {selectedFarm?.name ?? "tu finca"} · las recomendaciones se actualizan con el
            pipeline nocturno
          </p>
        </div>
        <div className="inline-flex items-center gap-[7px] h-8 px-3.5 bg-[#eef3ea] border border-[#d8e4d3] rounded-full text-xs font-semibold text-[#35663f]">
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
            <path d="M12 8v4l3 3" />
            <circle cx="12" cy="12" r="9" />
          </svg>
          Pipeline pendiente
        </div>
      </div>

      {/* Collective Intelligence card */}
      <div className="bg-[#2f5d3f] text-[#eef3ea] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#bfe0c6"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 3v18" />
            <path d="m5 8 7-5 7 5" />
            <path d="M5 8v8l7 5 7-5V8" />
          </svg>
          <div className="text-[15px] font-bold">Inteligencia colectiva</div>
        </div>
        <p className="text-[13.5px] leading-relaxed text-[#d3e3d6] m-0 mb-3.5">
          Cuando el pipeline nocturno se ejecute, aquí aparecerán las recomendaciones basadas en el
          análisis de parcelas similares de la red AgroCollective.
        </p>
        <div className="bg-white/10 rounded-[10px] p-3">
          <div className="text-[10.5px] tracking-[0.1em] uppercase text-[#a7c9ae] mb-1">
            Próximo análisis
          </div>
          <div className="text-[13.5px] font-semibold text-white">
            Hoy · 02:00 UTC — resultados disponibles por la mañana
          </div>
        </div>
      </div>

      {/* Placeholder cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-[18px]">
        {/* Telemetry placeholder */}
        <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2f5d3f"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
            </svg>
            <h2 className="text-[15px] font-bold text-[#24302a] m-0">Telemetría en tiempo real</h2>
          </div>
          <p className="text-xs text-[#8a978d] m-0 mb-4">
            Los gauges de sensores aparecerán aquí cuando se conecte un dispositivo IoT.
          </p>
          <div className="flex gap-3">
            {["Humedad suelo", "Temp. aire", "Humedad aire"].map((label) => (
              <div key={label} className="flex-1 bg-[#f7f6f0] rounded-xl p-4 text-center">
                <div className="w-14 h-14 mx-auto mb-2 rounded-full border-[6px] border-[#eae8e0]" />
                <div className="text-xs font-semibold text-[#24302a]">{label}</div>
                <div className="text-[11px] text-[#8a978d] mt-0.5">Sin datos</div>
              </div>
            ))}
          </div>
        </div>

        {/* Recommendations placeholder */}
        <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
          <div className="flex items-center gap-2 mb-2">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#2f5d3f"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 18h6" />
              <path d="M10 22h4" />
              <path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14" />
            </svg>
            <h2 className="text-[15px] font-bold text-[#24302a] m-0">Recomendaciones</h2>
          </div>
          <p className="text-xs text-[#8a978d] m-0 mb-4">
            Las recomendaciones priorizadas aparecerán aquí tras la ejecución del pipeline.
          </p>
          <div className="space-y-2.5">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="border border-[#ece7db] border-l-4 border-l-[#c3ccbf] rounded-xl p-3.5"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded bg-[#f0ede6] text-[#8a978d]">
                    Pendiente
                  </span>
                </div>
                <div className="h-3 w-3/4 bg-[#f0ede6] rounded mb-1.5" />
                <div className="h-2.5 w-1/2 bg-[#f7f6f0] rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
