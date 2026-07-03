"use client";

import { useState } from "react";
import { isAxiosError } from "axios";
import { useCreateDevice } from "../api/create-device";
import { useUpdateDevice } from "../api/update-device";
import { useAssignSensors } from "../api/assign-sensors";
import { useSensors } from "../api/get-sensors";
import type { Plot } from "@/features/plots/types";

interface DevicePairCardProps {
  plotId: string;
  plot: Plot | null;
}

const generateDeviceCode = (plotName: string | undefined, plotId: string) => {
  if (plotName && /^Sim-P\d+$/i.test(plotName)) {
    const num = plotName.replace(/Sim-P/i, "");
    return `AGRO-P${num}-001`;
  }
  if (plotName && /^P\d+$/i.test(plotName)) {
    return `AGRO-${plotName.toUpperCase()}-001`;
  }
  return `AGRO-P-${plotId.substring(0, 8).toUpperCase()}`;
};

const getSensorLabel = (type: string, name: string) => {
  switch (type) {
    case "air_temperature":
      return `temperatura del aire (${name})`;
    case "relative_humidity":
      return `humedad relativa (${name})`;
    case "soil_temperature":
      return `temperatura del suelo (${name})`;
    case "soil_humidity":
      return `humedad del suelo (${name})`;
    default:
      return `${type} (${name})`;
  }
};

export function DevicePairCard({ plotId, plot }: DevicePairCardProps) {
  const createDeviceMutation = useCreateDevice(plotId);
  const updateDeviceMutation = useUpdateDevice(plotId);
  const assignSensorsMutation = useAssignSensors(plotId);
  const { data: sensors, isLoading: isSensorsLoading } = useSensors();

  const [isActive, setIsActive] = useState<boolean>(true);
  const [deselectedSensorIds, setDeselectedSensorIds] = useState<string[]>([]);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const selectedSensorIds = sensors
    ? sensors.filter((s) => !deselectedSensorIds.includes(s.id)).map((s) => s.id)
    : [];

  const generatedCode = generateDeviceCode(plot?.name, plotId);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    try {
      const device = await createDeviceMutation.mutateAsync({ code: generatedCode });

      if (!isActive) {
        await updateDeviceMutation.mutateAsync({
          deviceId: device.id,
          data: { is_active: false },
        });
      }

      if (selectedSensorIds.length > 0) {
        await assignSensorsMutation.mutateAsync({
          deviceId: device.id,
          sensorIds: selectedSensorIds,
        });
      }

      setSuccessMsg("Dispositivo registrado correctamente.");
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 409) {
        setErrorMsg("Esta parcela ya tiene un dispositivo emparejado.");
      } else {
        setErrorMsg("Error al crear el dispositivo.");
      }
    }
  };

  const toggleSensor = (id: string) => {
    setDeselectedSensorIds((prev) =>
      prev.includes(id) ? prev.filter((sid) => sid !== id) : [...prev, id],
    );
  };

  const isPending =
    createDeviceMutation.isPending ||
    updateDeviceMutation.isPending ||
    assignSensorsMutation.isPending;

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

      {/* Content */}
      <div className="py-1">
        <p className="text-xs text-[#8a978d] leading-relaxed m-0 mb-4">
          Esta parcela aún no tiene un nodo IoT emparejado.
        </p>

        {errorMsg && (
          <div className="mb-4 p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-600">
            {errorMsg}
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-700">
            {successMsg}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-bold text-[#6b7a70] uppercase mb-1">
              código generado:
            </label>
            <div className="w-full h-10 border border-[#e2dcd0] bg-[#fcfbfa] rounded-lg px-3 text-sm text-[#4b5550] flex items-center font-mono select-all">
              {generatedCode}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="isActive"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              disabled={isPending}
              className="w-4 h-4 rounded border-[#d9d3c5] text-[#2f5d3f] focus:ring-[#2f5d3f]/30"
            />
            <label
              htmlFor="isActive"
              className="text-xs font-semibold text-[#3a4a42] cursor-pointer"
            >
              Dispositivo activo
            </label>
          </div>

          <div className="space-y-2">
            <label className="block text-[10px] font-bold text-[#6b7a70] uppercase mb-1">
              selección de sensores:
            </label>
            {isSensorsLoading ? (
              <p className="text-[10px] text-[#8a978d]">Cargando sensores...</p>
            ) : (
              <div className="space-y-1.5 bg-[#fcfbfa] border border-[#e2dcd0] rounded-lg p-2.5">
                {sensors?.map((sensor) => (
                  <div key={sensor.id} className="flex items-center gap-2.5">
                    <input
                      type="checkbox"
                      id={sensor.id}
                      checked={!deselectedSensorIds.includes(sensor.id)}
                      onChange={() => toggleSensor(sensor.id)}
                      disabled={isPending}
                      className="w-3.5 h-3.5 rounded border-[#d9d3c5] text-[#2f5d3f] focus:ring-[#2f5d3f]/30"
                    />
                    <label
                      htmlFor={sensor.id}
                      className="text-xs text-[#4b5550] cursor-pointer select-none"
                    >
                      {getSensorLabel(sensor.sensor_type, sensor.name)}
                    </label>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={isPending || isSensorsLoading}
            className="w-full h-10 border-none rounded-lg bg-[#2f5d3f] text-white text-[13.5px] font-semibold cursor-pointer hover:bg-[#264b33] disabled:opacity-60 inline-flex items-center justify-center gap-[7px]"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#fff"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12h14" />
              <path d="M12 5v14" />
            </svg>
            {isPending ? "Creando..." : "Crear dispositivo"}
          </button>
        </form>
      </div>
    </div>
  );
}
