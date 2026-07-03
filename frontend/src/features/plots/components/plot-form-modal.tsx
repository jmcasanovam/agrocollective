/* eslint-disable react-hooks/incompatible-library */
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { isAxiosError } from "axios";
import { useCreatePlot } from "../api/create-plot";
import { useCrops, useSoils } from "../api/get-catalog";

const plotSchema = z.object({
  name: z.string().min(1, "El nombre es obligatorio"),
  crop_id: z.string().min(1, "El cultivo es obligatorio"),
  soil_id: z.string().min(1, "El tipo de suelo es obligatorio"),
  area_ha: z.string().optional(),
  management_profile: z.string().optional(),
});

type PlotFormInput = z.infer<typeof plotSchema>;

interface PlotFormModalProps {
  farmId: string | null;
  farmName?: string;
  isOpen: boolean;
  onClose: () => void;
}

export function PlotFormModal({ farmId, farmName, isOpen, onClose }: PlotFormModalProps) {
  const createPlotMutation = useCreatePlot(farmId);
  const { data: crops } = useCrops();
  const { data: soils } = useSoils();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<PlotFormInput>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(plotSchema as any),
    defaultValues: {
      name: "",
      crop_id: "",
      soil_id: "",
      area_ha: "",
      management_profile: "Riego deficitario controlado",
    },
    mode: "onChange",
  });

  const cropValue = watch("crop_id");
  const soilValue = watch("soil_id");
  const nameValue = watch("name");
  const canSubmit = !!(cropValue && soilValue && nameValue);

  const onSubmit = (data: PlotFormInput) => {
    if (!canSubmit) return;
    setSubmitError(null);
    createPlotMutation.mutate(
      {
        name: data.name,
        crop_id: data.crop_id,
        soil_id: data.soil_id,
        area_ha: data.area_ha ? Number(data.area_ha) : null,
        management_profile: data.management_profile || null,
      },
      {
        onSuccess: () => {
          reset();
          onClose();
        },
        onError: (error) => {
          if (isAxiosError(error) && error.response?.status === 409) {
            setSubmitError("Ya existe una parcela con ese nombre en esta finca.");
            return;
          }
          setSubmitError("No se pudo crear la parcela. Inténtalo de nuevo.");
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

        <h2 className="text-[19px] font-bold text-[#24302a] m-0 mb-1">Nueva parcela</h2>
        <p className="text-[13px] text-[#8a978d] m-0 mb-5">
          Añade una parcela a {farmName || "tu finca"}.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Name (required, unico por finca) */}
          <div>
            <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
              Nombre <span className="text-[#c0453d]">*</span>
            </label>
            <input
              type="text"
              placeholder="Parcela Oeste"
              {...register("name")}
              className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
            />
            {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
          </div>

          {/* Crop + Soil (both required) */}
          <div className="grid grid-cols-2 gap-3.5">
            <div>
              <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
                Cultivo <span className="text-[#c0453d]">*</span>
              </label>
              <select
                {...register("crop_id")}
                className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2.5 text-sm text-[#24302a] outline-none cursor-pointer focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
              >
                <option value="">Selecciona cultivo…</option>
                {crops?.map((crop) => (
                  <option key={crop.id} value={crop.id}>
                    {crop.name}
                  </option>
                ))}
              </select>
              {errors.crop_id && (
                <p className="mt-1 text-xs text-red-500">{errors.crop_id.message}</p>
              )}
            </div>
            <div>
              <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
                Tipo de suelo <span className="text-[#c0453d]">*</span>
              </label>
              <select
                {...register("soil_id")}
                className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2.5 text-sm text-[#24302a] outline-none cursor-pointer focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
              >
                <option value="">Selecciona suelo…</option>
                {soils?.map((soil) => (
                  <option key={soil.id} value={soil.id}>
                    {soil.name}
                  </option>
                ))}
              </select>
              {errors.soil_id && (
                <p className="mt-1 text-xs text-red-500">{errors.soil_id.message}</p>
              )}
            </div>
          </div>

          {/* Profile (optional) */}
          <div>
            <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
              Perfil de gestión <span className="text-[#9aa79d] font-normal">(opcional)</span>
            </label>
            <select
              {...register("management_profile")}
              className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2.5 text-sm text-[#24302a] outline-none cursor-pointer focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
            >
              <option value="Riego deficitario controlado">Seco eficiente</option>
              <option value="Estándar SiAR">Moderado</option>
              <option value="Riego por goteo optimizado">Húmedo intensivo</option>
              <option value="Secano">Secano</option>
            </select>
          </div>

          {/* Area (optional) */}
          <div>
            <label className="block text-[13px] font-medium text-[#3a4a42] mb-1.5">
              Superficie (ha) <span className="text-[#9aa79d] font-normal">(opcional)</span>
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="4.2"
              {...register("area_ha")}
              className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 font-[inherit]"
            />
          </div>

          {submitError && <p className="text-xs text-red-500">{submitError}</p>}

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
              disabled={!canSubmit || createPlotMutation.isPending}
              className={`h-[42px] px-5 border-none rounded-[9px] text-sm font-semibold text-white font-[inherit] transition-colors ${
                canSubmit
                  ? "bg-[#2f5d3f] cursor-pointer hover:bg-[#264b33]"
                  : "bg-[#c3ccbf] cursor-not-allowed"
              }`}
            >
              {createPlotMutation.isPending ? "Creando..." : "Crear parcela"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
