import type { Metadata } from "next";

import { PlotsList } from "@/features/plots/components/plots-list";

export const metadata: Metadata = { title: "Parcelas" };

export default function PlotsPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-6 text-3xl font-bold">Parcelas</h1>
      <PlotsList />
    </main>
  );
}
