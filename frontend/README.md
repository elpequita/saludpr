# SaludPR Frontend

Public health dashboard for Puerto Rico — the interface the community actually sees.

## Design philosophy

This isn't a generic dashboard. SaludPR's UI needs to:

- Feel **editorial**, not enterprise — closer to NYT data journalism or The Pudding than a corporate BI tool
- Communicate **trust and credibility** through typography and clarity
- Be **bilingual from the ground up** (EN/ES), never feel like an afterthought translation
- Respect **low-bandwidth users** — snappy on a 4G connection from a rural municipality
- Be **accessible** (WCAG AA minimum)

Dark by default. Data-dense but never cluttered. Every pixel earns its place.

## Stack

- **Next.js 15** (App Router) — SSR for SEO, fast page loads, Vercel-native
- **TypeScript** (strict mode, no `any`)
- **Tailwind CSS 4** + **shadcn/ui** — accessible, composable components
- **Mapbox GL JS** + **react-map-gl** — smooth choropleth animations
- **Visx** (D3-based, composable) for custom charts · **Recharts** as fallback for standard charts
- **Motion** (formerly Framer Motion) for animations
- **TanStack Query** — data fetching, caching, loading states
- **Zod** — runtime validation of API responses
- **next-intl** — i18n for EN/ES (better than i18next for App Router)
- **MDX** for the `/methodology` page
- Deployed on **Vercel**

## Local development

```bash
cd frontend
pnpm install          # pnpm preferred, npm also works
cp .env.example .env.local
# Edit .env.local with your API URL + Mapbox token

pnpm dev
```

App runs at http://localhost:3000

## Project layout (Next.js App Router)

```
frontend/
├── app/
│   ├── [locale]/              # i18n routing (en/es)
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Home / main dashboard
│   │   ├── about/
│   │   │   └── page.tsx       # Dataurea attribution + mission
│   │   ├── methodology/
│   │   │   └── page.mdx       # Data sources — MDX
│   │   └── municipio/
│   │       └── [id]/
│   │           └── page.tsx   # Municipality detail view
│   ├── api/                   # Next.js route handlers (thin proxy layer if needed)
│   ├── layout.tsx             # Root layout
│   └── globals.css
├── components/
│   ├── ui/                    # shadcn/ui primitives
│   ├── map/
│   │   ├── PRMap.tsx
│   │   ├── ChoroplethLayer.tsx
│   │   └── HospitalPins.tsx
│   ├── charts/
│   │   ├── TrendLine.tsx
│   │   └── DiseaseComparison.tsx
│   ├── panels/
│   │   └── MunicipalityPanel.tsx
│   └── layout/
│       ├── Header.tsx
│       └── Footer.tsx         # "Built by Dataurea" footer
├── lib/
│   ├── api.ts                 # typed API client (with Zod schemas)
│   ├── schemas.ts             # Zod schemas mirroring backend
│   └── utils.ts
├── messages/                  # next-intl translation files
│   ├── en.json
│   └── es.json
├── public/
│   ├── fonts/                 # self-hosted display + body fonts
│   └── logo-dataurea.svg
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json              # strict: true
├── package.json
└── .env.example
```

## Code quality (for Codex audit readiness)

- TypeScript `strict: true`, `noUncheckedIndexedAccess: true`, `noImplicitReturns: true`
- ESLint with `typescript-eslint/strict-type-checked`
- Prettier with Tailwind plugin
- Vitest for component + unit tests
- Playwright for E2E (post-MVP)
- Conventional commits enforced via `commitlint`

## Build

```bash
pnpm build
pnpm start      # production server
pnpm lint       # ESLint
pnpm typecheck  # tsc --noEmit
pnpm test       # Vitest
```

## Performance targets

- Lighthouse Performance ≥ 90
- First Contentful Paint < 1.5s on 4G
- Largest Contentful Paint < 2.5s
- Cumulative Layout Shift < 0.1
- Bundle size budget: 200KB initial JS (gzipped)
