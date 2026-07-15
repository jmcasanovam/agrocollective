"use client";

import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { type ReactNode } from "react";

import { ErrorBoundary } from "@/components/errors/error-boundary";
import { getQueryClient, getSiarPersister, SIAR_PERSIST_OPTIONS } from "@/lib/react-query";

export function AppProvider({ children }: { children: ReactNode }) {
  const queryClient = getQueryClient();
  const persister = getSiarPersister();

  return (
    <ErrorBoundary>
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{ persister, ...SIAR_PERSIST_OPTIONS }}
      >
        {children}
        {process.env.NODE_ENV === "development" && <ReactQueryDevtools initialIsOpen={false} />}
      </PersistQueryClientProvider>
    </ErrorBoundary>
  );
}
