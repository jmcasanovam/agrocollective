"use client";

import { PlotsList } from "@/features/plots/components/plots-list";
import { useFarmStore } from "@/features/farms/stores/farm";

export default function PlotsPage() {
  const selectedFarm = useFarmStore((state) => state.selectedFarm);

  return <PlotsList selectedFarm={selectedFarm} />;
}
