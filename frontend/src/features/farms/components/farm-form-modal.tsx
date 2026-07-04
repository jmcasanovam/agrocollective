"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateFarm } from "../api/create-farm";
import { useRegions } from "../api/get-regions";

const farmSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, "El nombre debe tener al menos 2 caracteres")
    .max(150, "El nombre no puede superar los 150 caracteres"),
  region_id: z.string().min(1, "La región es obligatoria"),
  latitude: z
    .string()
    .min(1, "La latitud es obligatoria")
    .refine(
      (v) => !Number.isNaN(Number(v)) && Number(v) >= -90 && Number(v) <= 90,
      "Debe estar entre -90 y 90",
    ),
  longitude: z
    .string()
    .min(1, "La longitud es obligatoria")
    .refine(
      (v) => !Number.isNaN(Number(v)) && Number(v) >= -180 && Number(v) <= 180,
      "Debe estar entre -180 y 180",
    ),
  area_ha: z
    .string()
    .min(1, "La superficie es obligatoria")
    .refine(
      (v) => !Number.isNaN(Number(v)) && Number(v) > 0 && Number(v) <= 100000,
      "Debe ser un número entre 0 y 100.000 ha",
    ),
});

type FarmFormInput = z.infer<typeof farmSchema>;

interface FarmFormModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FarmFormModal({ isOpen, onClose }: FarmFormModalProps) {
  const createFarmMutation = useCreateFarm();
  const { data: regions } = useRegions();

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    reset,
  } = useForm<FarmFormInput>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(farmSchema as any),
    defaultValues: {
      name: "",
      region_id: "",
      latitude: "",
      longitude: "",
      area_ha: "",
    },
    mode: "onChange",
  });

  const canSubmit = isValid;

  const onSubmit = (data: FarmFormInput) => {
    if (!canSubmit) return;
    createFarmMutation.mutate(
      {
        name: data.name,
        region_id: data.region_id,
        latitude: Number(data.latitude),
        longitude: Number(data.longitude),
        area_ha: Number(data.area_ha),
      },
      {
        onSuccess: () => {
          reset();
          onClose();
        },
      },
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(22,34,26,0.45)] p-6">
      <div className="relative w-[460px] max-w-[92vw] bg-white rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.22)] p-[26px]">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-[18px] right-[18px] w-[30px] h-[30px] rounded-lg flex items-center justify-center cursor-pointer bg-transparent border-none text-[#8a978d] hover:bg-[#f0ede4] hover:text-[#3a4a42] transition-colors"
        >
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>

        <h2 className="text-[19px] font-bold text-[#24302a] m-0 mb-1">Nueva finca</h2>
        <p className="text-[13px] text-[#8a978d] m-0 mb-5">Registra una explotación en tu red.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Name + Region */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
                Nombre <span className="text-[#c0453d]">*</span>
              </label>
              <input
                type="text"
                placeholder="Finca La Vega"
                maxLength={150}
                {...register("name")}
                className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
              />
              {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
            </div>

            <div>
              <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
                Región <span className="text-[#c0453d]">*</span>
              </label>
              <select
                {...register("region_id")}
                defaultValue=""
                className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2.5 text-sm text-[#24302a] outline-none cursor-pointer focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
              >
                <option value="" disabled>
                  Selecciona región…
                </option>
                {regions?.map((reg) => (
                  <option key={reg.id} value={reg.id}>
                    {reg.name} ({reg.code})
                  </option>
                ))}
              </select>
              {errors.region_id && (
                <p className="mt-1 text-xs text-red-500">{errors.region_id.message}</p>
              )}
            </div>
          </div>

          {/* Lat/Lon/Area */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            <div>
              <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
                Latitud <span className="text-[#c0453d]">*</span>
              </label>
              <input
                type="number"
                step="0.0001"
                min="-90"
                max="90"
                placeholder="39.3610"
                {...register("latitude")}
                className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
              />
              {errors.latitude && (
                <p className="mt-1 text-xs text-red-500">{errors.latitude.message}</p>
              )}
            </div>
            <div>
              <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
                Longitud <span className="text-[#c0453d]">*</span>
              </label>
              <input
                type="number"
                step="0.0001"
                min="-180"
                max="180"
                placeholder="-0.5120"
                {...register("longitude")}
                className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
              />
              {errors.longitude && (
                <p className="mt-1 text-xs text-red-500">{errors.longitude.message}</p>
              )}
            </div>
            <div>
              <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
                Superficie (ha) <span className="text-[#c0453d]">*</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="100000"
                placeholder="12.4"
                {...register("area_ha")}
                className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
              />
              {errors.area_ha && (
                <p className="mt-1 text-xs text-red-500">{errors.area_ha.message}</p>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2.5 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="h-[42px] px-[18px] border border-[#d9d3c5] bg-white rounded-[9px] text-sm font-semibold text-[#3a4a42] cursor-pointer hover:bg-[#f4f2ea] transition-colors font-[inherit]"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!canSubmit || createFarmMutation.isPending}
              className={`h-[42px] px-5 border-none rounded-[9px] text-sm font-semibold text-white font-[inherit] transition-colors ${
                canSubmit
                  ? "bg-[#2f5d3f] cursor-pointer hover:bg-[#264b33]"
                  : "bg-[#c3ccbf] cursor-not-allowed"
              }`}
            >
              {createFarmMutation.isPending ? "Creando..." : "Crear finca"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
