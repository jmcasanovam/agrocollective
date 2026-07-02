"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";

import { useLogin } from "../api/login";
import { useRegister } from "../api/register";

const loginSchema = z.object({
  email: z.string().email("Debe introducir un correo electrónico válido"),
  password: z.string().min(1, "La contraseña es requerida"),
});

const registerSchema = z.object({
  email: z.string().email("Debe introducir un correo electrónico válido"),
  password: z.string().min(6, "La contraseña debe tener al menos 6 caracteres"),
});

type AuthFormData = z.infer<typeof registerSchema>;

export function LoginForm() {
  const [isLoginView, setIsLoginView] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const router = useRouter();

  const loginMutation = useLogin();
  const registerMutation = useRegister();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<AuthFormData>({
    resolver: (data, context, options) => {
      const schema = isLoginView ? loginSchema : registerSchema;
      return zodResolver(schema)(data, context, options);
    },
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (data: AuthFormData) => {
    setErrorMessage(null);
    if (isLoginView) {
      loginMutation.mutate(data, {
        onSuccess: () => {
          router.push("/farms");
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onError: (err: any) => {
          const isUnauthorized = err.response?.status === 401;
          const detail = isUnauthorized
            ? "El usuario y/o contraseña son incorrectos"
            : err.response?.data?.detail || "Error al iniciar sesión";
          setErrorMessage(detail);
        },
      });
    } else {
      registerMutation.mutate(data, {
        onSuccess: () => {
          // Auto login after registration
          loginMutation.mutate(data, {
            onSuccess: () => {
              router.push("/farms");
            },
            onError: () => {
              // Redirect to login if autologin fails
              setIsLoginView(true);
              setErrorMessage("Cuenta creada con éxito. Por favor, inicia sesión.");
            },
          });
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onError: (err: any) => {
          const detail = err.response?.data?.detail || "Error al registrar la cuenta";
          setErrorMessage(detail);
        },
      });
    }
  };

  const toggleView = () => {
    setIsLoginView(!isLoginView);
    setErrorMessage(null);
    reset();
  };

  const isLoading = loginMutation.isPending || registerMutation.isPending;

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight text-[#24302a] mb-1.5">
        {isLoginView ? "¡Bienvenido!" : "Crear cuenta"}
      </h2>
      <p className="text-sm text-[#6b7a70] mb-7">
        {isLoginView
          ? "Inicia sesión para gestionar tus explotaciones"
          : "Regístrate para empezar a digitalizar tus parcelas"}
      </p>

      {errorMessage && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-600">
          {errorMessage}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-[#3a4a42] mb-1.5">
            Correo electrónico
          </label>
          <input
            type="email"
            placeholder="ejemplo@correo.com"
            disabled={isLoading}
            {...register("email")}
            className="w-full h-11 border border-[#d9d3c5] rounded-lg px-3.5 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40 disabled:opacity-60"
          />
          {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
        </div>

        <div>
          <label className="block text-xs font-semibold text-[#3a4a42] mb-1.5">Contraseña</label>
          <input
            type="password"
            placeholder="••••••••"
            disabled={isLoading}
            {...register("password")}
            className="w-full h-11 border border-[#d9d3c5] rounded-lg px-3.5 text-sm text-[#24302a] bg-white outline-none focus:ring-2 focus:ring-[#2f5d3f]/40 disabled:opacity-60"
          />
          {errors.password && (
            <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full h-11 mt-2 border-none rounded-lg bg-[#2f5d3f] text-white text-sm font-semibold cursor-pointer hover:bg-[#264b33] active:scale-[0.99] transition-all disabled:opacity-60"
        >
          {isLoading ? "Cargando..." : isLoginView ? "Iniciar sesión" : "Registrarse"}
        </button>
      </form>

      <div className="text-center mt-5 text-sm text-[#6b7a70]">
        {isLoginView ? "¿No tienes cuenta? " : "¿Ya tienes cuenta? "}
        <span
          onClick={toggleView}
          className="text-[#2f5d3f] font-semibold cursor-pointer hover:underline"
        >
          {isLoginView ? "Regístrate" : "Inicia sesión"}
        </span>
      </div>
    </div>
  );
}
