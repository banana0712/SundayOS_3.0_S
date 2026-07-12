# Sunday OS · Console

The visual operating system of an intelligent cognitive architecture.
Built to the **Sunday OS Design Language 1.0** — calm, intelligent, precise, alive.

## Run

```bash
cd console
npm install
npm run dev      # http://localhost:3000
npm run build    # production build (type + lint checked)
```

## Stack

Next.js 15 (App Router) · React 19 · TypeScript · TailwindCSS · Framer Motion · lucide-react.

## What's built

- **App shell** — three-column layout (Sidebar 280px / Content / Inspector) + collapsible
  bottom Console, per the Console design doc.
- **⌘K Command Palette** — fuzzy jump across all 21 modules, full keyboard nav.
- **Dashboard** — System Overview: 8 metric cards with sparklines, 24h activity chart,
  live Emotion radar, System Health (CPU/RAM/services), current Goal (Planner task tree),
  Recent Events timeline.
- **Brain Visualization** — the signature page: central Sunday Core with breathing glow,
  8 orbiting cognitive nodes (Attention · Planner · Memory · Reflection · Goal ·
  Relationship · Emotion · Tool Runtime), animated signal packets along connection lines,
  per-node load rings, and a live inspector.
- **Console dock** — streaming log with token/latency/memory stats.

Remaining sidebar modules render a design-consistent placeholder and are the next build queue.

## Design tokens

All tokens live in `src/app/globals.css` (CSS variables) and `tailwind.config.ts`:
colors (`#0B0B0C` bg / `#151518` surface / `#0A84FF` accent + semantic), 8pt spacing,
unified radii (10/16/24/28/32), extremely light shadows, subtle glassmorphism, and
spring motion (150–300ms). Light/dark themes and `prefers-reduced-motion` are respected.

## Structure

```
src/
  app/            layout, globals.css, page
  components/
    shell/        sidebar, topbar, inspector, console-dock, command-palette, app-shell
    views/        dashboard, brain, coming-soon
    ui/           primitives (Card, Sparkline, Donut, Radar, Badge)
  config/nav.ts   sidebar / palette navigation model
  store/ui.tsx    UI state + live-signal hooks
  lib/cn.ts       className helper
```
