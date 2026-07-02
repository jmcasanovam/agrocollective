"use client";

import { useUpdateDevice } from "../api/update-device";
import { useDeleteDevice } from "../api/delete-device";
import type { Device } from "../types";
import { useState } from "react";

interface DeviceStatusCardProps {
  plotId: string;
  device: Device;
}

export function DeviceStatusCard({ plotId, device }: DeviceStatusCardProps) {
  const updateDeviceMutation = useUpdateDevice(plotId);
  const deleteDeviceMutation = useDeleteDevice(plotId);
  const [isUnpairing, setIsUnpairing] = useState(false);

  const handleToggleActive = () => {
    updateDeviceMutation.mutate({
      deviceId: device.id,
      data: { is_active: !device.is_active },
    });
  };

  const handleUnpair = () => {
    if (window.confirm("¿Seguro que deseas desvincular este dispositivo?")) {
      setIsUnpairing(true);
      deleteDeviceMutation.mutate(device.id, {
        onSettled: () => setIsUnpairing(false),
      });
    }
  };

  // Battery percentage (3300mV = 0%, 4200mV = 100%)
  const batteryMv = device.battery_mv ?? 0;
  const batteryPct = Math.min(100, Math.max(0, Math.round(((batteryMv - 3300) / 900) * 100)));
  const batteryColor = batteryPct > 60 ? "#4f8a5b" : batteryPct > 35 ? "#d98a2b" : "#d24b43";

  // Connection status
  const isOnline = device.is_active && !!device.last_seen_at;

  const formattedLastSeen = device.last_seen_at
    ? new Date(device.last_seen_at).toLocaleString("es-ES", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Nunca";

  return (
    <div className="bg-white border border-[#e7e2d6] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] p-5">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#2f5d3f"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <rect x="9" y="9" width="6" height="6" />
          <path d="M15 2v2" />
          <path d="M15 20v2" />
          <path d="M2 15h2" />
          <path d="M2 9h2" />
          <path d="M20 15h2" />
          <path d="M20 9h2" />
          <path d="M9 2v2" />
          <path d="M9 20v2" />
        </svg>
        <h3 className="text-[15px] font-bold text-[#24302a] m-0">Dispositivo IoT</h3>
      </div>

      {/* Device info row */}
      <div className="flex items-center justify-between mb-3.5">
        <div>
          <div className="text-sm font-bold font-mono text-[#24302a]">{device.code}</div>
          <div className="text-xs text-[#8a978d]">Nodo ESP32</div>
        </div>
        <span
          className={`text-[11.5px] font-semibold px-[11px] py-1 rounded-full ${
            isOnline ? "bg-[#e3efdd] text-[#356440]" : "bg-[#f8e5e2] text-[#b23a33]"
          }`}
        >
          {isOnline ? "En línea" : "Offline"}
        </span>
      </div>

      {/* Battery */}
      <div className="space-y-2.5">
        <div>
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-[#6b7a70]">Batería</span>
            <span className="font-semibold text-[#3a4a42]">
              {batteryMv > 0 ? `${batteryPct}% · ${batteryMv} mV` : "No disponible"}
            </span>
          </div>
          {batteryMv > 0 && (
            <div className="h-2 bg-[#eef0ea] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${batteryPct}%`, backgroundColor: batteryColor }}
              />
            </div>
          )}
        </div>

        {/* Last seen */}
        <div className="flex justify-between text-xs pt-1.5 border-t border-[#f0ece2]">
          <span className="text-[#6b7a70]">Última señal</span>
          <span className="font-semibold text-[#3a4a42]">{formattedLastSeen}</span>
        </div>

        {/* MQTT Topic */}
        <div className="flex justify-between text-xs">
          <span className="text-[#6b7a70]">Topic MQTT · QoS 1</span>
          <span className="font-semibold text-[#3a4a42] font-mono text-[11px]">
            devices/{device.code}/readings
          </span>
        </div>

        {/* Toggle is_active */}
        <div className="flex items-center justify-between pt-2.5 mt-1 border-t border-[#f0ece2]">
          <div>
            <div className="text-[13px] font-semibold text-[#3a4a42]">Habilitado</div>
            <div className="text-[11.5px] text-[#9aa79d]">acepta lecturas del nodo</div>
          </div>
          <button
            onClick={handleToggleActive}
            disabled={updateDeviceMutation.isPending}
            className={`w-11 h-6 rounded-full relative cursor-pointer border-none transition-colors ${
              device.is_active ? "bg-[#4f8a5b]" : "bg-[#c3ccbf]"
            }`}
          >
            <div
              className={`absolute top-[2px] w-5 h-5 rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.25)] transition-[left] ${
                device.is_active ? "left-[22px]" : "left-[2px]"
              }`}
            />
          </button>
        </div>

        {/* Unpair */}
        <div className="pt-2 text-right">
          <button
            onClick={handleUnpair}
            disabled={isUnpairing}
            className="text-xs text-[#8a5b52] font-semibold bg-transparent border-none cursor-pointer hover:underline disabled:opacity-50"
          >
            Desvincular nodo
          </button>
        </div>
      </div>
    </div>
  );
}
