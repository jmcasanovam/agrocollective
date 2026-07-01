"use client";

import { useFarms } from "../api/get-farms";
import { FarmGrid } from "./farm-grid";
import { useAuthStore } from "@/features/auth/stores/auth";

export function FarmSelector() {
  const { data: farms, isLoading, isError } = useFarms();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#eef0e8] flex items-center justify-center">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 rounded-full border-4 border-[#2f5d3f] border-t-transparent animate-spin mx-auto" />
          <p className="text-xs text-[#6b7a70]">Cargando explotaciones...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-[#eef0e8] flex items-center justify-center p-4">
        <div className="w-full max-w-sm bg-white p-6 rounded-2xl border border-red-100 text-center space-y-4 shadow-sm">
          <div className="text-red-500 font-bold text-lg">Error de carga</div>
          <p className="text-xs text-[#6b7a70]">
            No se han podido cargar tus explotaciones agrícolas. Por favor, inténtalo de nuevo.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="w-full h-10 border-none rounded-lg bg-[#2f5d3f] text-white text-xs font-semibold cursor-pointer hover:bg-[#264b33]"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#eef0e8] flex flex-col font-sans">
      {/* Top Bar for Select screen */}
      <header className="h-16 bg-white border-b border-[#d9d3c5]/60 flex items-center justify-between px-6 md:px-12">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[#2f5d3f] flex items-center justify-center">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#fff"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z" />
            </svg>
          </div>
          <span className="text-md font-bold text-[#24302a]">AgroCollective</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-xs font-bold text-[#24302a]">{user?.email}</div>
            <div className="text-[10px] text-[#6b7a70]">Productor</div>
          </div>
          <button
            onClick={logout}
            className="text-xs text-red-600 font-semibold bg-transparent border-none cursor-pointer hover:underline"
          >
            Cerrar sesión
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-6 md:px-12 py-10">
        <FarmGrid farms={farms || []} />
      </main>
    </div>
  );
}
