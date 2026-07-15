# AgroCollective: Frontend

Next.js 16 (App Router) · React 19 · TypeScript strict · Tailwind CSS

Arquitectura basada en [bulletproof-react](https://github.com/alan2207/bulletproof-react).

---

## Arranque rápido

```bash
cp .env.example .env.local   # ajustar NEXT_PUBLIC_API_URL
pnpm install
pnpm dev                      # http://localhost:3000
```

### Con Docker (junto al backend)

```bash
docker compose up frontend    # imagen de producción
```

---

## Variables de entorno

| Variable              | Descripción                  | Ejemplo                 |
| --------------------- | ---------------------------- | ----------------------- |
| `NEXT_PUBLIC_API_URL` | URL base del backend FastAPI | `http://localhost:8000` |

El módulo `src/config/env.ts` valida con Zod al arrancar: si la variable falta, la app aborta con un mensaje claro.

---

## Estructura de carpetas

```
frontend/src/
├── app/              # App Router: layouts, pages, route groups, provider.tsx
│   └── (app)/        # Rutas autenticadas
├── components/       # Compartidos: ui/, layouts/, errors/, seo/
├── config/           # env.ts (validación Zod), paths.ts (rutas centralizadas)
├── features/         # Módulos por dominio (ver más abajo)
├── hooks/            # Hooks compartidos
├── lib/              # api-client.ts (Axios), react-query.ts (QueryClient)
├── stores/           # Stores globales Zustand
├── testing/          # test-utils.tsx, mocks/ (handlers MSW)
├── types/            # Tipos TypeScript compartidos
└── utils/            # Utilidades compartidas
```

### Anatomía de una feature

```
features/plots/
├── api/          # Funciones de fetch + hooks useQuery/useMutation
├── components/   # Componentes propios de la feature
├── hooks/        # Hooks internos de la feature
├── stores/       # Estado Zustand local (si aplica)
├── types/        # Tipos del dominio (Plot, Farm...)
└── utils/        # Helpers internos
```

---

## Flujo de importaciones (UNIDIRECCIONAL)

```
shared (components / hooks / lib / utils / types / config)
        ↓
    features/<nombre>
        ↓
       app/
```

- Una **feature no puede importar de otra feature**.
- Los módulos **shared no pueden importar de features ni de app**.
- Las **rutas de `app/`** solo componen componentes de features; la lógica vive en la feature.

ESLint (`eslint-plugin-import`) hace cumplir estos límites en CI y en pre-commit.

---

## Cómo crear una nueva feature

1. Crear `src/features/<nombre>/` con las subcarpetas necesarias.
2. Añadir la zona de restricción en `eslint.config.mjs` (copiar el bloque de `plots`).
3. Definir tipos en `types/index.ts`.
4. Crear la función de fetch + hook en `api/`.
5. Construir componentes en `components/`.
6. Añadir la ruta en `src/app/(app)/<nombre>/page.tsx`.

---

## Scripts

| Comando           | Descripción                   |
| ----------------- | ----------------------------- |
| `pnpm dev`        | Servidor de desarrollo        |
| `pnpm build`      | Build de producción           |
| `pnpm start`      | Servidor de producción local  |
| `pnpm lint`       | ESLint (0 warnings tolerados) |
| `pnpm lint:fix`   | ESLint con autofix            |
| `pnpm format`     | Prettier                      |
| `pnpm typecheck`  | TypeScript sin emitir         |
| `pnpm test`       | Vitest (single run)           |
| `pnpm test:watch` | Vitest en modo watch          |

---

## Testing

- **Vitest** + **Testing Library** con `jsdom`.
- **MSW** intercepta las llamadas HTTP en tests, sin mocks de módulos.
- `src/testing/test-utils.tsx` exporta un `render` envuelto en `QueryClientProvider`.
- Los handlers MSW están en `src/testing/mocks/handlers.ts`.

---

## Git hooks

Husky + lint-staged corren en cada commit sobre los archivos staged:

- `*.{ts,tsx}` → `eslint --fix` + `prettier --write`
- `*.{json,md,css}` → `prettier --write`

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
