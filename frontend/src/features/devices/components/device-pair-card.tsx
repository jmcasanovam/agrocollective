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

      {/* Empty state */}
      <div className="text-center py-2.5 px-1">
        <div className="w-[46px] h-[46px] rounded-xl bg-[#f2efe6] flex items-center justify-center mx-auto mb-3">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#a3aca2"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M2 2l20 20" />
            <rect x="4" y="4" width="16" height="16" rx="2" />
          </svg>
        </div>
        <div className="text-sm font-semibold text-[#3a4a42] mb-1">Sin dispositivo</div>
        <p className="text-xs text-[#8a978d] leading-relaxed m-0 mb-3.5">
          Esta parcela aún no tiene un nodo ESP32 emparejado.
        </p>

        {createDeviceMutation.isError && (
          <div className="mb-3.5 p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-600 text-left">
            El dispositivo no existe o ya está emparejado a otra parcela.
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <div>
            <input
              type="text"
              placeholder="Código, ej. AGRO-P00-001"
              disabled={createDeviceMutation.isPending}
              {...register("code")}
              className="w-full h-10 border border-[#d9d3c5] rounded-lg px-3 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/30 disabled:opacity-60 font-[inherit]"
            />
            {errors.code && <p className="mt-1 text-xs text-red-500">{errors.code.message}</p>}
          </div>
          <button
            type="submit"
            disabled={createDeviceMutation.isPending}
            className="h-[38px] px-4 border-none rounded-[9px] bg-[#2f5d3f] text-white text-[13.5px] font-semibold cursor-pointer hover:bg-[#264b33] disabled:opacity-60 inline-flex items-center gap-[7px] font-[inherit]"
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
            {createDeviceMutation.isPending ? "Vinculando..." : "Emparejar dispositivo"}
          </button>
        </form>
      </div>
    </div>
  );
}
