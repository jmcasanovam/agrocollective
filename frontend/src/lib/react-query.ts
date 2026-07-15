import { QueryClient } from "@tanstack/react-query";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import type { PersistQueryClientOptions } from "@tanstack/react-query-persist-client";

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 min
        retry: 1,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// Singleton para el cliente de navegador (evita recrear en cada render)
let browserQueryClient: QueryClient | undefined;

export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") {
    return makeQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

// Persistencia en localStorage SOLO para los datos climaticos SiAR (ver
// get-plot-weather.ts, queryKey ["siar-weather", ...]): el resto de datos
// (fincas, parcelas, sesion) se mantienen solo en memoria por sesion. Asi
// una recarga de pagina no vuelve a pedir el clima de una estacion ya
// consultada; logout() y el boton "Vaciar cache" siguen limpiandolo (logout
// llama a queryClient.clear(), que borra tanto la cache en memoria como,
// via este persister, la copia en localStorage en el siguiente flush).
let siarPersister: ReturnType<typeof createAsyncStoragePersister> | undefined;

export function getSiarPersister() {
  if (!siarPersister) {
    siarPersister = createAsyncStoragePersister({
      storage: typeof window === "undefined" ? undefined : window.localStorage,
      key: "agrocollective-siar-cache",
    });
  }
  return siarPersister;
}

export const SIAR_PERSIST_OPTIONS: Omit<PersistQueryClientOptions, "persister" | "queryClient"> = {
  maxAge: Infinity, // sin caducidad por tiempo: solo se limpia por logout o borrado manual
  dehydrateOptions: {
    shouldDehydrateQuery: (query) =>
      query.queryKey[0] === "siar-weather" && query.state.status === "success",
  },
};
