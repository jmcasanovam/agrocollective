import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import importPlugin from "eslint-plugin-import";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,

  // Flujo unidireccional: shared → features → app
  // Una feature no puede importar de otra feature.
  // Los módulos compartidos no pueden importar de features ni de app.
  {
    plugins: { import: importPlugin },
    rules: {
      "import/no-restricted-paths": [
        "error",
        {
          zones: [
            {
              target: "./src/features/plots",
              from: "./src/features",
              except: ["./plots"],
              message: "Las features no deben importarse entre sí.",
            },
            {
              target: [
                "./src/components",
                "./src/hooks",
                "./src/lib",
                "./src/utils",
                "./src/types",
                "./src/config",
              ],
              from: ["./src/features", "./src/app"],
              message:
                "Los módulos compartidos no pueden depender de features ni de app.",
            },
          ],
        },
      ],
      "import/no-relative-packages": "error",
    },
  },

  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "node_modules/**",
  ]),
]);

export default eslintConfig;
