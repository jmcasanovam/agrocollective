"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateDevice } from "../api/create-device";

const pairSchema = z.object({
  code: z.string().min(1, "El código del dispositivo es obligatorio"),
});

type PairFormData = z.infer<typeof pairSchema>;

interface DevicePairCardProps {
  plotId: string;
}

export function DevicePairCard({ plotId }: DevicePairCardProps) {
  const createDeviceMutation = useCreateDevice(plotId);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<PairFormData>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(pairSchema as any),
    defaultValues: { code: "" },
  });

  const onSubmit = (data: PairFormData) => {
    createDeviceMutation.mutate(
      { code: data.code },
      {
        onSuccess: () => {
          reset();
        },
      },
    );
  };

  return (
    <div className="p-6 bg-white rounded-2xl border border-[#d9d3c5]/60">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-[#f4f2eb] flex items-center justify-center text-[#6b7a70]">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </div>
        <h3 className="text-md font-bold text-[#24302a]">Dispositivo IoT</h3>
      </div>

      <p className="text-xs text-[#6b7a70] mb-5 leading-relaxed">
        No hay ningún dispositivo IoT emparejado a esta parcela. Introduce el código identificador
        para empezar a recibir lecturas de humedad y temperatura en tiempo real.
      </p>

      {createDeviceMutation.isError && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-600">
          El dispositivo no existe o ya está emparejado a otra parcela.
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-[#3a4a42] mb-1.5">
            Código del dispositivo
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Ej. AGRO-P00-001"
              disabled={createDeviceMutation.isPending}
              {...register("code")}
              className="flex-1 h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={createDeviceMutation.isPending}
              className="h-10 px-4 border-none rounded-lg bg-[#2f5d3f] text-white text-xs font-semibold cursor-pointer hover:bg-[#264b33] disabled:opacity-60"
            >
              {createDeviceMutation.isPending ? "Vinculando..." : "Vincular"}
            </button>
          </div>
          {errors.code && <p className="mt-1 text-xs text-red-500">{errors.code.message}</p>}
        </div>
      </form>
    </div>
  );
}
