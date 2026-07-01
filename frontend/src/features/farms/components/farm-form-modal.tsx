"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateFarm } from "../api/create-farm";
import { useRegions } from "../api/get-regions";

const farmSchema = z.object({
  name: z.string().min(1, "El nombre es obligatorio"),
  region_id: z.string().optional(),
  latitude: z.string().optional(),
  longitude: z.string().optional(),
  area_ha: z.string().optional(),
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
    formState: { errors },
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
  });

  const onSubmit = (data: FarmFormInput) => {
    createFarmMutation.mutate(
      {
        name: data.name,
        region_id: data.region_id || null,
        latitude: data.latitude ? Number(data.latitude) : null,
        longitude: data.longitude ? Number(data.longitude) : null,
        area_ha: data.area_ha ? Number(data.area_ha) : null,
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
          <h3 className="text-lg font-bold text-[#24302a]">Nueva Finca</h3>
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
              Nombre de la finca
            </label>
            <input
              type="text"
              placeholder="Ej. Finca El Alamillo"
              {...register("name")}
              className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
            />
            {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#3a4a42] mb-1">
              Región Agroclimática (SiAR)
            </label>
            <select
              {...register("region_id")}
              className="w-full h-10 border border-[#d9d3c5] bg-white rounded-lg px-2 text-sm outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
            >
              <option value="">Selecciona una región</option>
              {regions?.map((reg) => (
                <option key={reg.id} value={reg.id}>
                  {reg.name} ({reg.code})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#3a4a42] mb-1">Latitud</label>
              <input
                type="number"
                step="0.000001"
                placeholder="Ej. 37.17"
                {...register("latitude")}
                className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#3a4a42] mb-1">Longitud</label>
              <input
                type="number"
                step="0.000001"
                placeholder="Ej. -3.60"
                {...register("longitude")}
                className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#3a4a42] mb-1">
              Superficie Total (ha)
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="Ej. 14.5"
              {...register("area_ha")}
              className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40"
            />
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
              disabled={createFarmMutation.isPending}
              className="h-10 px-4 border-none rounded-lg bg-[#2f5d3f] text-white text-sm font-semibold cursor-pointer hover:bg-[#264b33] disabled:opacity-60"
            >
              {createFarmMutation.isPending ? "Creando..." : "Crear Finca"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
