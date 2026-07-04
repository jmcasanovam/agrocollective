"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/stores/auth";
import { useFarmStore } from "@/features/farms/stores/farm";
import { useRegions } from "@/features/farms/api/get-regions";
import { useFarms } from "@/features/farms/api/get-farms";

function getNextAnalysisRun(): Date {
  const now = new Date();
  const next = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 2, 0, 0, 0),
  );
  if (next.getTime() <= now.getTime()) {
    next.setUTCDate(next.getUTCDate() + 1);
  }
  return next;
}

function formatCountdown(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const pad = (n: number) => String(n).padStart(2, "0");
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${pad(hours)}h ${pad(minutes)}m ${pad(seconds)}s`;
}

function formatRunDate(date: Date): string {
  const day = String(date.getUTCDate()).padStart(2, "0");
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const year = date.getUTCFullYear();
  return `${day}/${month}/${year}`;
}

function NextAnalysisCountdown() {
  const [nextRun, setNextRun] = useState(getNextAnalysisRun);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => {
      const current = new Date();
      setNow(current);
      if (current.getTime() >= nextRun.getTime()) {
        setNextRun(getNextAnalysisRun());
      }
    }, 1000);
    return () => clearInterval(id);
  }, [nextRun]);

  return (
    <div className="bg-[#eef3ea] border border-[#d8e4d3] rounded-xl p-3.5">
      <div className="text-[11px] tracking-widest uppercase text-[#6b8a72] mb-1">
        Próximo análisis
      </div>
      <div className="text-[15px] font-bold text-[#2f5d3f] font-mono">
        {formatCountdown(nextRun.getTime() - now.getTime())}
      </div>
      <div className="text-[11px] text-[#7d8c82] mt-0.5">{formatRunDate(nextRun)} · 02:00 UTC</div>
    </div>
  );
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const user = useAuthStore((state) => state.user);
  const selectedFarm = useFarmStore((state) => state.selectedFarm);
  const clearSelectedFarm = useFarmStore((state) => state.clearSelectedFarm);
  const { data: regions } = useRegions();
  const { data: farms } = useFarms();
  const region = regions?.find((r) => r.id === selectedFarm?.region_id);
  const hasMultipleFarms = (farms?.length ?? 0) > 1;

  const handleChangeFarm = () => {
    clearSelectedFarm();
    onClose();
    router.push("/farms");
  };

  const navItems = [
    {
      name: "Resumen",
      href: "/",
      icon: (
        <svg
          width="17"
          height="17"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M3 3v18h18" />
          <path d="M18 17V9" />
          <path d="M13 17V5" />
          <path d="M8 17v-3" />
        </svg>
      ),
      match: (p: string) => p === "/",
      disabled: false,
    },
    {
      name: "Parcelas",
      href: "/plots",
      icon: (
        <svg
          width="17"
          height="17"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M7 20h10" />
          <path d="M10 20c5.5-2.5.8-6.4 3-10" />
          <path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z" />
          <path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z" />
        </svg>
      ),
      match: (p: string) => p === "/plots" || p.startsWith("/plots/"),
      disabled: false,
    },
    {
      name: "Fincas",
      href: "/farms",
      icon: (
        <svg
          width="17"
          height="17"
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
      ),
      match: (p: string) => p === "/farms",
      disabled: false,
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-screen w-[236px] shrink-0 flex-col border-r border-[#e3ddce] bg-[#f4f2ea] px-3.5 py-5 font-sans transition-transform duration-200 ease-out lg:sticky lg:top-0 lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand */}
        <div className="flex items-center justify-between gap-2.5 px-2 pb-5">
          <div className="flex items-center gap-2.5">
            <div className="w-[34px] h-[34px] rounded-[10px] bg-[#2f5d3f] flex items-center justify-center">
              <svg
                width="19"
                height="19"
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
            <div className="text-[15px] font-bold tracking-tight text-[#24302a]">
              AgroCollective
            </div>
          </div>

          {/* Close button (mobile/tablet only) */}
          <button
            onClick={onClose}
            aria-label="Cerrar menú"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[#5c6b62] hover:bg-[#e9e5da] lg:hidden"
          >
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
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-[3px]">
          {navItems.map((item) => {
            const isActive = item.match(pathname);

            if (item.disabled) {
              return (
                <div
                  key={item.name}
                  className="flex items-center gap-[11px] px-3 py-[9px] rounded-[9px] text-sm font-medium text-[#5c6b62] cursor-not-allowed select-none"
                >
                  {item.icon}
                  {item.name}
                </div>
              );
            }

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={onClose}
                className={`flex items-center gap-[11px] px-3 py-[9px] rounded-[9px] text-sm font-medium transition-colors no-underline ${
                  isActive ? "bg-[#dbe8d3] text-[#2f5d3f]" : "text-[#5c6b62] hover:bg-[#e9e5da]"
                }`}
              >
                {item.icon}
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Spacer */}
        <div className="mt-auto flex flex-col gap-3">
          {/* Next analysis countdown */}
          <NextAnalysisCountdown />

          {/* Selected farm info (moved from topbar) */}
          {selectedFarm && (
            <div className="px-3 pt-2.5 border-t border-[#e3ddce]">
              <div className="text-[13px] font-bold text-[#24302a] tracking-tight leading-tight truncate">
                {selectedFarm.name}
              </div>
              <div className="text-[11px] text-[#7d8c82] truncate mb-2">
                {region ? `${region.name} (${region.code})` : "Sin región"} ·{" "}
                {selectedFarm.area_ha ? `${selectedFarm.area_ha} ha` : "no hay datos"}
              </div>
              {hasMultipleFarms && (
                <button
                  onClick={handleChangeFarm}
                  className="h-8 px-2.5 border border-[#d9d3c5] bg-white rounded-lg text-[12px] font-medium text-[#3a4a42] cursor-pointer inline-flex items-center gap-1.5 hover:bg-[#f0ede4] transition-colors"
                >
                  <svg
                    width="13"
                    height="13"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="m8 3 4 8 5-5 5 15H2L8 3z" />
                  </svg>
                  Cambiar finca
                </button>
              )}
            </div>
          )}

          {/* User email */}
          {user?.email && (
            <div className="px-3 pt-2 pb-0.5 text-xs text-[#5c6b62] font-semibold break-all border-t border-[#e3ddce]">
              {user.email}
            </div>
          )}

          {/* Logout */}
          <button
            onClick={logout}
            className="flex items-center gap-2.5 px-3 py-[9px] rounded-[9px] text-sm text-[#8a5b52] cursor-pointer bg-transparent border-none font-sans hover:bg-[#f3e8e5] transition-colors"
          >
            <svg
              width="17"
              height="17"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" x2="9" y1="12" y2="12" />
            </svg>
            Cerrar sesión
          </button>
        </div>
      </aside>
    </>
  );
}
