import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url("NEXT_PUBLIC_API_URL debe ser una URL válida"),
});

const _env = envSchema.safeParse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
});

if (!_env.success) {
  console.error("❌ Variables de entorno inválidas:", _env.error.flatten().fieldErrors);
  throw new Error("Variables de entorno requeridas no configuradas. Revisar .env.local");
}

export const env = _env.data;
