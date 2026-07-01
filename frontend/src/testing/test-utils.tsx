import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { type ReactNode } from "react";

function makeTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

function TestProviders({ children }: { children: ReactNode }) {
  const qc = makeTestQueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function customRender(ui: ReactNode, options?: Omit<RenderOptions, "wrapper">) {
  return render(ui, { wrapper: TestProviders, ...options });
}

export * from "@testing-library/react";
export { customRender as render, userEvent };
