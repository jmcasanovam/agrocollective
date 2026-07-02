"use client";

import { use } from "react";
import { PlotDetail } from "@/features/plots/components/plot-detail";
import { useFarmStore } from "@/features/farms/stores/farm";
import { useDevice } from "@/features/devices/api/get-device";
import { DeviceStatusCard } from "@/features/devices/components/device-status-card";
import { DevicePairCard } from "@/features/devices/components/device-pair-card";

interface PageProps {
  params: Promise<{ plotId: string }>;
}

import { usePlot } from "@/features/plots/api/get-plot";

function PlotDeviceManager({ plotId }: { plotId: string }) {
  const { data: device, isLoading: isDeviceLoading } = useDevice(plotId);
  const selectedFarm = useFarmStore((state) => state.selectedFarm);
  const { data: plot, isLoading: isPlotLoading } = usePlot({
    farmId: selectedFarm?.id ?? null,
    plotId,
  });

  const isLoading = isDeviceLoading || isPlotLoading;

  if (isLoading) {
    return (
      <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 text-center">
        <div className="w-5 h-5 rounded-full border-2 border-[#2f5d3f] border-t-transparent animate-spin mx-auto mb-1" />
        <p className="text-[10px] text-[#6b7a70]">Cargando dispositivo...</p>
      </div>
    );
  }

  if (!device) {
    return <DevicePairCard plotId={plotId} plot={plot ?? null} />;
  }

  return <DeviceStatusCard plotId={plotId} device={device} />;
}

export default function PlotDetailPage({ params }: PageProps) {
  const { plotId } = use(params);
  const selectedFarm = useFarmStore((state) => state.selectedFarm);

  return (
    <PlotDetail
      farmId={selectedFarm?.id ?? null}
      plotId={plotId}
      deviceEl={<PlotDeviceManager plotId={plotId} />}
    />
  );
}
