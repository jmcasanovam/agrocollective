"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/features/auth/stores/auth";
import { useFarmStore } from "@/features/farms/stores/farm";
import { useFarms } from "@/features/farms/api/get-farms";
import { getQueryClient } from "@/lib/react-query";
import { apiClient } from "@/lib/api-client";
import type { Farm } from "@/features/farms/types";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isInitializing = useAuthStore((state) => state.isInitializing);
  const initAuth = useAuthStore((state) => state.initAuth);

  const selectedFarmId = useFarmStore((state) => state.selectedFarmId);

  // Guards the /login resolution below against re-entering itself: it
  // clears/selects the farm as part of deciding where to go, which changes
  // `selectedFarmId` (a dependency of this same effect) while `pathname`
  // hasn't updated yet (router.push resolves asynchronously) — without this
  // guard that retriggers the whole clear→fetch→select→push cycle in a
  // tight loop that hammers "/" and never settles.
  const loginHandledRef = useRef(false);

  // Initialize Auth
  useEffect(() => {
    initAuth();
  }, [initAuth]);

  // Keep the selected farm's data in sync on every load/navigation, not just on /farms
  useFarms(isAuthenticated && !isInitializing);

  // Auth & farm selection routing checks
  useEffect(() => {
    if (isInitializing) return;

    if (!isAuthenticated) {
      loginHandledRef.current = false;
      if (pathname !== "/login") {
        router.push("/login");
      }
      return;
    }

    if (pathname === "/login") {
      // Run exactly once per arrival here — the resolution below changes
      // `selectedFarmId`, which would otherwise retrigger this same branch
      // before `pathname` catches up to the navigation it just started.
      if (loginHandledRef.current) return;
      loginHandledRef.current = true;

      // This is the single place that decides where a freshly-authenticated
      // user lands. Resolving the farm count *before* navigating means a
      // single-farm account (the common case) jumps straight to the
      // dashboard instead of visibly bouncing through /farms while it
      // fetches the same list — and having only one owner for this logic
      // avoids racing against any navigation login-form.tsx might trigger.
      let cancelled = false;
      useFarmStore.getState().clearSelectedFarm();
      getQueryClient()
        .fetchQuery({
          queryKey: ["farms"],
          queryFn: async () => {
            const { data } = await apiClient.get<Farm[]>("/farms");
            return data;
          },
        })
        .then((farms) => {
          if (cancelled) return;
          if (farms.length === 1) {
            useFarmStore.getState().selectFarm(farms[0]);
            router.push("/");
          } else {
            router.push("/farms");
          }
        })
        .catch(() => {
          if (!cancelled) router.push("/farms");
        });
      return () => {
        cancelled = true;
      };
    }

    loginHandledRef.current = false;

    if (!selectedFarmId && pathname !== "/farms") {
      router.push("/farms");
    }
  }, [isAuthenticated, isInitializing, selectedFarmId, pathname, router]);

  const loadingScreen = (
    <div className="min-h-screen bg-[#eef0e8] flex items-center justify-center">
      <div className="text-center space-y-2">
        <div className="w-8 h-8 rounded-full border-4 border-[#2f5d3f] border-t-transparent animate-spin mx-auto" />
        <p className="text-xs text-[#6b7a70] font-sans">Cargando AgroCollective...</p>
      </div>
    </div>
  );

  if (isInitializing) {
    return loadingScreen;
  }

  // If not logged in, render children directly only on /login — any other
  // route means the redirect effect above hasn't fired yet (e.g. right
  // after logout), so show the loading screen instead of flashing the
  // protected page's content without the shell.
  if (!isAuthenticated) {
    return pathname === "/login" ? <>{children}</> : loadingScreen;
  }

  // If on login or farms (when no farm is selected yet), render without main app shell layout (sidebar/topbar)
  if (pathname === "/login" || (pathname === "/farms" && !selectedFarmId)) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen bg-[#eef0e8] font-sans overflow-hidden">
      {/* Sidebar navigation */}
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      {/* Main app layout wrapper */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar farm selector/status */}
        <Topbar onMenuClick={() => setIsSidebarOpen(true)} />

        {/* Dynamic page contents */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1300px] w-full mx-auto p-4 sm:p-6 lg:p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
