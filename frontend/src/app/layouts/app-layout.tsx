"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/features/auth/stores/auth";
import { useFarmStore } from "@/features/farms/stores/farm";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isInitializing = useAuthStore((state) => state.isInitializing);
  const initAuth = useAuthStore((state) => state.initAuth);

  const selectedFarmId = useFarmStore((state) => state.selectedFarmId);

  // Initialize Auth
  useEffect(() => {
    initAuth();
  }, [initAuth]);

  // Auth & farm selection routing checks
  useEffect(() => {
    if (isInitializing) return;

    if (!isAuthenticated) {
      if (pathname !== "/login") {
        router.push("/login");
      }
    } else {
      if (pathname === "/login") {
        router.push("/farms");
      } else if (!selectedFarmId && pathname !== "/farms") {
        router.push("/farms");
      }
    }
  }, [isAuthenticated, isInitializing, selectedFarmId, pathname, router]);

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-[#eef0e8] flex items-center justify-center">
        <div className="text-center space-y-2">
          <div className="w-8 h-8 rounded-full border-4 border-[#2f5d3f] border-t-transparent animate-spin mx-auto" />
          <p className="text-xs text-[#6b7a70] font-sans">Cargando AgroCollective...</p>
        </div>
      </div>
    );
  }

  // If not logged in, render children directly (allows rendering login page)
  if (!isAuthenticated) {
    return <>{children}</>;
  }

  // If on login or farms, render without main app shell layout (sidebar/topbar)
  if (pathname === "/login" || pathname === "/farms") {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen bg-[#eef0e8] font-sans overflow-hidden">
      {/* Sidebar navigation */}
      <Sidebar />

      {/* Main app layout wrapper */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar farm selector/status */}
        <Topbar />

        {/* Dynamic page contents */}
        <main className="flex-1 overflow-y-auto p-8 max-w-[1300px] w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}
