import { type ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-[#eef0e8] font-sans">
      {/* Brand Panel */}
      <div className="hidden md:flex flex-col justify-between w-[46%] bg-[#22402e] text-[#eef3ea] p-14 relative overflow-hidden">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#4f8a5b] flex items-center justify-center">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#fff"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
              <path d="M2 21c0-3 1.85-5.36 5.08-6" />
            </svg>
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight">AgroCollective</div>
            <div className="text-[11px] tracking-widest uppercase text-[#9bc0a4]">
              Inteligencia colectiva agrícola
            </div>
          </div>
        </div>

        <div className="max-w-[420px] z-10">
          <h1 className="text-3xl font-bold leading-tight tracking-tight mb-5">
            Tus parcelas aprenden de miles de otras.
          </h1>
          <p className="text-md leading-relaxed text-[#c4d8ca] mb-8">
            Sensores IoT en tiempo real, un pipeline agronómico nocturno y recomendaciones
            priorizadas que comparan cada parcela con las más parecidas del sistema.
          </p>
          <div className="flex gap-7">
            <div>
              <div className="text-2xl font-bold">1.240</div>
              <div className="text-xs text-[#9bc0a4]">parcelas en red</div>
            </div>
            <div>
              <div className="text-2xl font-bold">−18%</div>
              <div className="text-xs text-[#9bc0a4]">agua media / temporada</div>
            </div>
            <div>
              <div className="text-2xl font-bold">4×</div>
              <div className="text-xs text-[#9bc0a4]">lecturas al día</div>
            </div>
          </div>
        </div>

        <div className="text-xs text-[#7fa389] z-10">
          SiAR · Picassent V17 · Baza GR01: datos agroclimáticos oficiales
        </div>
        <div className="absolute -right-16 -bottom-16 w-72 h-72 rounded-full bg-gradient-to-tr from-[#4f8a5b]/35 to-transparent filter blur-2xl pointer-events-none" />
      </div>

      {/* Form Panel */}
      <div className="flex-1 flex items-center justify-center p-8 bg-[#eef0e8]">
        <div className="w-full max-w-sm bg-white md:bg-transparent p-8 md:p-0 rounded-2xl md:rounded-none shadow-md md:shadow-none border md:border-none border-[#d9d3c5]/60">
          {children}
        </div>
      </div>
    </div>
  );
}
