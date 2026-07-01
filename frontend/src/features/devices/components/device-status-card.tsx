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
        onSuccess: () => {
          setIsUnpairing(false);
        },
        onError: () => {
          setIsUnpairing(false);
        },
      });
    }
  };

  // Battery percentage computation (3300mV to 4200mV)
  const batteryMv = device.battery_mv ?? 0;
  const batteryPct = Math.min(100, Math.max(0, Math.round(((batteryMv - 3300) / 900) * 100)));

  const batteryVolts = (batteryMv / 1000).toFixed(2);

  // Connection status (Online if last_seen_at exists and is active)
  const isOnline = device.is_active && !!device.last_seen_at;

  const formattedLastSeen = device.last_seen_at
    ? new Date(device.last_seen_at).toLocaleTimeString("es-ES", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Nunca";

  return (
    <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60 space-y-5">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[#2f5d3f]/10 flex items-center justify-center text-[#2f5d3f]">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2" />
              <path d="M12 18h.01" />
            </svg>
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#24302a]">Dispositivo IoT</h3>
            <p className="text-[10px] text-[#6b7a70]">{device.code}</p>
          </div>
        </div>

        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
            isOnline
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-gray-100 text-gray-500 border border-gray-200"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${isOnline ? "bg-green-500" : "bg-gray-400"}`}
          />
          {isOnline ? "Conectado" : "Offline"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 py-1 border-t border-b border-[#f0ede6]">
        <div>
          <div className="text-[10px] text-[#6b7a70] uppercase tracking-wider font-bold">
            Batería
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="text-sm font-bold text-[#24302a]">
              {batteryMv > 0 ? `${batteryPct}%` : "No disp."}
            </span>
            <span className="text-[10px] text-[#6b7a70]">
              {batteryMv > 0 ? `(${batteryVolts}V)` : ""}
            </span>
          </div>
          {batteryMv > 0 && (
            <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden mt-1.5">
              <div
                className={`h-full rounded-full ${
                  batteryPct > 50 ? "bg-green-500" : batteryPct > 20 ? "bg-amber-500" : "bg-red-500"
                }`}
                style={{ width: `${batteryPct}%` }}
              />
            </div>
          )}
        </div>

        <div>
          <div className="text-[10px] text-[#6b7a70] uppercase tracking-wider font-bold">
            Última Señal
          </div>
          <div className="text-sm font-bold text-[#24302a] mt-1">{formattedLastSeen}</div>
          <div className="text-[10px] text-[#6b7a70] mt-1.5">
            Topic: <span className="font-mono text-[9px]">devices/{device.code}/readings</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-2">
          <button
            onClick={handleToggleActive}
            disabled={updateDeviceMutation.isPending}
            className={`w-9 h-5 rounded-full p-0.5 transition-colors focus:outline-none ${
              device.is_active ? "bg-[#2f5d3f]" : "bg-gray-300"
            }`}
          >
            <div
              className={`w-4 h-4 rounded-full bg-white transition-transform ${
                device.is_active ? "translate-x-4" : "translate-x-0"
              }`}
            />
          </button>
          <span className="text-xs font-semibold text-[#3a4a42]">
            {device.is_active ? "Dispositivo habilitado" : "Dispositivo deshabilitado"}
          </span>
        </div>

        <button
          onClick={handleUnpair}
          disabled={isUnpairing}
          className="text-xs text-red-600 font-bold bg-transparent border-none cursor-pointer hover:underline disabled:opacity-50"
        >
          Desvincular nodo
        </button>
      </div>
    </div>
  );
}
