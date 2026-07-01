"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { useCrops } from "../api/get-catalog";
import type { Plot } from "../types";

interface PlotCardProps {
  plot: Plot;
}

interface MiniDevice {
  is_active: boolean;
}

export function PlotCard({ plot }: PlotCardProps) {
  const { data: crops } = useCrops();

  // Fetch device for this plot to show connectivity state
  const { data: device } = useQuery({
    queryKey: ["plots", plot.id, "devices"],
    queryFn: async () => {
      try {
        const { data } = await apiClient.get<MiniDevice>(`/plots/${plot.id}/devices`);
        return data;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
        if (err.response?.status === 404) return null;
        throw err;
      }
    },
  });

  const crop = crops?.find((c) => c.id === plot.crop_id);

  return (
    <tr className="border-b border-[#f0ede6] hover:bg-[#fcfcfa] transition-colors">
      <td className="py-4 px-4 font-bold text-[#24302a] text-sm">{plot.name}</td>
      <td className="py-4 px-4 text-xs text-[#3a4a42]">
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#f4f2eb] font-semibold">
          {crop?.name || "Cargando..."}
        </span>
      </td>
      <td className="py-4 px-4 text-xs text-[#6b7a70]">{plot.management_profile || "Secano"}</td>
      <td className="py-4 px-4 text-xs text-[#24302a] font-medium">
        {plot.area_ha ? `${plot.area_ha} ha` : "--"}
      </td>
      <td className="py-4 px-4 text-xs">
        {device ? (
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold ${
              device.is_active
                ? "bg-green-50 text-green-700 border border-green-200"
                : "bg-amber-50 text-amber-700 border border-amber-200"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${device.is_active ? "bg-green-500" : "bg-amber-500"}`}
            />
            {device.is_active ? "Activo" : "Inactivo"}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-semibold bg-gray-50 text-gray-500 border border-gray-200">
            Sin dispositivo
          </span>
        )}
      </td>
      <td className="py-4 px-4 text-right text-xs">
        <Link href={`/plots/${plot.id}`} className="text-[#2f5d3f] font-bold hover:underline">
          Detalle &rarr;
        </Link>
      </td>
    </tr>
  );
}
