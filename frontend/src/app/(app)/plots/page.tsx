"use client";

import { PlotsList } from "@/features/plots/components/plots-list";
import { useFarmStore } from "@/features/farms/stores/farm";
import { useFarmLocationLabel } from "@/features/farms/hooks/use-farm-location-label";

export default function PlotsPage() {
  const selectedFarm = useFarmStore((state) => state.selectedFarm);
  const { label: locationLabel } = useFarmLocationLabel(selectedFarm);

  return <PlotsList selectedFarm={selectedFarm} locationLabel={locationLabel} />;
}
