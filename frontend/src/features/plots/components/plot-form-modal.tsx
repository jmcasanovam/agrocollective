"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
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
  isOpen: boolean;
  onClose: () => void;
}

export function PlotFormModal({ farmId, isOpen, onClose }: PlotFormModalProps) {
  const createPlotMutation = useCreatePlot(farmId);
  const { data: crops } = useCrops();
  const { data: soils } = useSoils();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
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
  });

  const onSubmit = (data: PlotFormInput) => {
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
      },
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 backdrop-blur-xs p-4">
      <div className="w-full max-w-md bg-white rounded-2xl p-6 shadow-xl border border-[#d9d3c5]/60 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex justify-between items-center mb-5">
          <h3 className="text-lg font-bold text-[#24302a]">Nueva Parcela</h3>
          <button
            onClick={onClose}
            className="text-[#6b7a70] hover:text-[#24302a] cursor-pointer bg-transparent border-none text-xl"
          >
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#3a4a42] mb-1">
              Nombre de la parcela
            </label>
            <input
              type="text"
              placeholder="Ej. Sector 1 Olivos"
              {...register("name")}
              className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
            />
            {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#3a4a42] mb-1">Cultivo</label>
              <select
                {...register("crop_id")}
                className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2 text-sm outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
              >
                <option value="">Selecciona cultivo</option>
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
              <label className="block text-xs font-semibold text-[#3a4a42] mb-1">
                Tipo de suelo
              </label>
              <select
                {...register("soil_id")}
                className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2 text-sm outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
              >
                <option value="">Selecciona suelo</option>
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

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#3a4a42] mb-1">
                Superficie (ha)
              </label>
              <input
                type="number"
                step="0.1"
                placeholder="Ej. 3.2"
                {...register("area_ha")}
                className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#3a4a42] mb-1">
                Perfil de Gestión
              </label>
              <select
                {...register("management_profile")}
                className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2 text-sm outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
              >
                <option value="Riego deficitario controlado">Deficitario controlado</option>
                <option value="Estándar SiAR">Estándar SiAR</option>
                <option value="Riego por goteo optimizado">Goteo optimizado</option>
                <option value="Secano">Secano</option>
              </select>
            </div>
          </div>

          <div className="flex gap-3 justify-end mt-6">
            <button
              type="button"
              onClick={onClose}
              className="h-10 px-4 border border-[#d9d3c5] rounded-lg text-sm font-semibold text-[#3a4a42] bg-white cursor-pointer hover:bg-zinc-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createPlotMutation.isPending}
              className="h-10 px-4 border-none rounded-lg bg-[#2f5d3f] text-white text-sm font-semibold cursor-pointer hover:bg-[#264b33] disabled:opacity-60"
            >
              {createPlotMutation.isPending ? "Creando..." : "Crear Parcela"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
