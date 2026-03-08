# Production UI Overhaul Design

**Date:** 2026-03-08
**Status:** Approved

## Overview

Overhaul the Adaptron web UI from a basic prototype to a production-grade Modern SaaS application. Replace monospace fonts, grid backgrounds, and basic styling with a polished Inter-font, glassmorphism, shadcn/ui component library, persistent navigation, and a new Validation page. The frontend is deployed to Azure Web App; the backend runs on a separate GPU VM accessed via `API_URL` environment variable.

**Brand:** A product of DHS IT Solutions. DHS logo in navbar.

## Architecture

- **Framework:** Next.js 14 + TypeScript (unchanged)
- **Components:** shadcn/ui (Radix UI + Tailwind CSS)
- **Font:** Inter via `next/font/google` (replace `font-mono`)
- **Theme:** Dark theme with glassmorphism cards, subtle radial gradient background
- **Pages:** Home, Wizard, Dashboard, Playground, Validation (new)
- **Deployment:** Azure Web App (standalone output), API on separate GPU VM

## Navigation & Layout

Persistent top navbar across all pages:

- **Left:** DHS logo (`public/dhs-logo.png`) + "Adaptron" brand text
- **Center:** Page links (Wizard, Dashboard, Playground, Validation) with active indicator
- **Right:** Backend connection status dot (green=connected, red=disconnected, pings `/api/health`)
- **Style:** Sticky top, `backdrop-blur-xl`, glass background (`bg-white/5 border-white/10`)
- **Mobile:** Sheet/hamburger menu via shadcn Sheet component

## Pages

### Home (`/`)

- Hero section with gradient text "Adaptron" title
- Tagline: "A product of DHS IT Solutions"
- Description: "Build, validate, and deploy production-ready language models from your enterprise data."
- Two CTA buttons: Start Wizard (primary), View Dashboard (secondary)
- Four feature cards linking to each page (Wizard, Dashboard, Playground, Validation) with glass-card styling
- Footer: "DHS IT Solutions" + version number
- Animated gradient mesh background (no grid lines)

### Wizard (`/wizard`)

Same 7-step questionnaire flow, polished:

- Segmented progress bar with step checkmarks
- Larger option cards with hover scale effect and accent glow on selection
- Slide animation between steps
- Result page with animated metric cards (shadcn Card + Badge)

### Dashboard (`/dashboard`)

- Stats row: metric cards for total pipelines, active jobs, models deployed
- Pipeline cards with color-coded status badges (running/complete/failed)
- Empty state with illustration and CTA to wizard
- Auto-refresh: polls `/api/pipelines` every 10 seconds

### Playground (`/playground`)

- Chat bubbles with avatar indicators
- shadcn Select for model selector
- Collapsible settings sidebar (Temperature, Max Tokens as shadcn Sliders)
- Clean split view for compare mode
- Typing indicator animation during streaming

### Validation (`/validation`) — New

- Overall grade badge (large letter, color-coded: A=green, B=blue, C=amber, D/F=red)
- Summary cards: one per validator (Benchmark, Hallucination, Production Readiness) with key metric + grade
- Tabbed detail view (shadcn Tabs): Benchmark, Comparison, Readiness, Hallucination
- Per-sample results table with pass/fail indicators
- Flagged samples highlighted in amber
- Trigger validation button: POST `/api/validate/start`
- Status polling while validation runs

## Component Library

### shadcn/ui Components

Button, Card, Badge, Tabs, Select, Slider, Dialog, Toast, Progress, Separator, DropdownMenu, Sheet

### Custom Shared Components

| Component | Purpose |
|-----------|---------|
| `Navbar` | Persistent top nav with DHS logo, links, status |
| `StatusDot` | Animated green/red backend connectivity indicator |
| `GradeBadge` | Letter grade with color mapping (A-F) |
| `MetricCard` | Reusable stat card (icon, label, value) |
| `EmptyState` | Placeholder with CTA |

## Theme

| Token | Value |
|-------|-------|
| Font | Inter (via next/font/google) |
| Background | `#0a0c10` with radial gradient mesh |
| Surface glass | `bg-white/5 backdrop-blur-xl border-white/10` |
| Accent | `#4f8ef7` |
| Success | `#2dd4a0` |
| Warning | `#f5a623` |
| Danger | `#ef4444` |
| Purple | `#9b87f5` |
| Transitions | `transition-all duration-200` on interactive elements |

## Assets

- `public/dhs-logo.png` — DHS IT Solutions logo (provided by user)

## API Contract

No backend changes. Frontend consumes existing endpoints:
- `/api/health` — connectivity check
- `/api/wizard/recommend` — wizard recommendations
- `/api/pipelines` — pipeline listing
- `/api/playground/models`, `/api/playground/chat` — playground
- `/api/validate/start`, `/api/validate/status`, `/api/validate/report` — validation

## Deployment

- Build: `next build` (standalone output)
- Deploy: `az webapp deploy` to `adaptron-app` in `rg-dhs-sap`
- Backend URL: `API_URL` environment variable in Azure Web App settings
