"use client";

import { useFarmStore } from "@/features/farms/stores/farm";
import { FarmSelector } from "@/features/farms/components/farm-selector";
import { MyFarmsDirectory } from "@/features/farms/components/my-farms-directory";

export default function FarmsPage() {
  const selectedFarmId = useFarmStore((state) => state.selectedFarmId);

  if (selectedFarmId === null) {
    return <FarmSelector />;
  }

  return <MyFarmsDirectory />;
}
