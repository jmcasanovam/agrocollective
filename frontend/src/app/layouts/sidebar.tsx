"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/features/auth/stores/auth";

export function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((state) => state.logout);

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
          <rect width="7" height="9" x="3" y="3" rx="1" />
          <rect width="7" height="5" x="14" y="3" rx="1" />
          <rect width="7" height="9" x="14" y="12" rx="1" />
          <rect width="7" height="5" x="3" y="16" rx="1" />
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
          <path d="M3 3v18h18" />
          <path d="m7 12 3-3 3 3 5-5" />
        </svg>
      ),
      match: (p: string) => p === "/plots" || p.startsWith("/plots/"),
      disabled: false,
    },
    {
      name: "Mis fincas",
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
          <path d="M18 20V10" />
          <path d="M12 20V4" />
          <path d="M6 20v-6" />
        </svg>
      ),
      match: (p: string) => p === "/farms",
      disabled: false,
    },
    {
      name: "Análisis",
      href: "#",
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
          <path d="m12 14 4-4" />
          <path d="M3.34 19a10 10 0 1 1 17.32 0" />
        </svg>
      ),
      match: () => false,
      disabled: true,
    },
    {
      name: "Ajustes",
      href: "#",
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
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      ),
      match: () => false,
      disabled: true,
    },
  ];

  return (
    <aside className="w-[236px] shrink-0 bg-[#f4f2ea] border-r border-[#e3ddce] flex flex-col py-5 px-3.5 sticky top-0 h-screen font-sans">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-2 pb-5">
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
        <div className="text-[15px] font-bold tracking-tight text-[#24302a]">AgroCollective</div>
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
        {/* Pipeline info */}
        <div className="bg-[#eef3ea] border border-[#d8e4d3] rounded-xl p-3.5">
          <div className="text-[11px] tracking-[0.1em] uppercase text-[#6b8a72] mb-1">
            Próximo pipeline
          </div>
          <div className="text-[13px] font-semibold text-[#2f5d3f]">Hoy · 02:00 UTC</div>
          <div className="text-[11px] text-[#7d8c82] mt-0.5">análisis nocturno de parcelas</div>
        </div>

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
  );
}
