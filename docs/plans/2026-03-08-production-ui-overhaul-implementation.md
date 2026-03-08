# Production UI Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Adaptron web UI from a basic prototype into a production-grade Modern SaaS application with shadcn/ui, Inter font, glassmorphism, persistent navigation, and a new Validation page.

**Architecture:** Next.js 14 app with shadcn/ui (Radix UI + Tailwind) component library. Persistent Navbar layout with DHS branding. Five pages: Home, Wizard, Dashboard, Playground, Validation. Dark theme with glass-card styling. Backend on separate GPU VM via API_URL env var.

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS 3.4, shadcn/ui, Radix UI, next/font/google (Inter), Lucide React icons

---

### Task 1: Install shadcn/ui and Dependencies

**Files:**
- Modify: `web/package.json`
- Modify: `web/tailwind.config.ts`
- Modify: `web/app/globals.css`
- Create: `web/components.json`
- Create: `web/lib/utils.ts`

**Step 1: Install shadcn/ui CLI and initialize**

Run from `web/` directory:

```bash
npx shadcn@latest init
```

When prompted:
- Style: Default
- Base color: Slate
- CSS variables: Yes

This creates `components.json`, `lib/utils.ts`, and updates `tailwind.config.ts` and `globals.css`.

**Step 2: Install shadcn/ui components**

```bash
npx shadcn@latest add button card badge tabs select slider dialog separator sheet progress dropdown-menu
```

This creates files under `web/components/ui/`.

**Step 3: Install Lucide React for icons**

```bash
npm install lucide-react
```

**Step 4: Verify build succeeds**

```bash
npx next build
```

Expected: Build succeeds with no errors.

**Step 5: Commit**

```bash
git add web/
git commit -m "feat(web): initialize shadcn/ui with component library"
```

---

### Task 2: Theme, Font, and Layout Foundation

**Files:**
- Modify: `web/app/layout.tsx`
- Modify: `web/app/globals.css`
- Modify: `web/tailwind.config.ts`
- Create: `web/public/dhs-logo.png` (copy from `C:\Users\MuthuSubramanian\Downloads\home_logo-C66cuoiK.png`)

**Step 1: Copy DHS logo to public directory**

```bash
mkdir -p web/public
cp "C:\Users\MuthuSubramanian\Downloads\home_logo-C66cuoiK.png" web/public/dhs-logo.png
```

**Step 2: Update layout.tsx with Inter font**

Replace the entire `web/app/layout.tsx`:

```tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Adaptron - LLM Fine-tuning Framework',
  description: 'Build, validate, and deploy production-ready language models. A product of DHS IT Solutions.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans bg-background text-foreground min-h-screen antialiased`}>
        {children}
      </body>
    </html>
  )
}
```

**Step 3: Update globals.css**

Replace `web/app/globals.css` — remove grid background, add radial gradient mesh:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 222 47% 4%;
    --foreground: 210 40% 98%;
    --card: 222 47% 6%;
    --card-foreground: 210 40% 98%;
    --popover: 222 47% 6%;
    --popover-foreground: 210 40% 98%;
    --primary: 217 91% 64%;
    --primary-foreground: 222 47% 4%;
    --secondary: 217 33% 17%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 55%;
    --accent: 217 91% 64%;
    --accent-foreground: 222 47% 4%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 210 40% 98%;
    --border: 217 33% 17%;
    --input: 217 33% 17%;
    --ring: 217 91% 64%;
    --radius: 0.75rem;
    --success: 162 74% 50%;
    --warning: 36 91% 55%;
    --danger: 0 84% 60%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
    background-image:
      radial-gradient(ellipse 80% 50% at 50% -20%, rgba(79, 142, 247, 0.15), transparent),
      radial-gradient(ellipse 60% 40% at 80% 50%, rgba(155, 135, 245, 0.08), transparent);
  }
}
```

**Step 4: Update tailwind.config.ts**

Replace `web/tailwind.config.ts` to integrate shadcn/ui CSS variable theme:

```ts
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        success: 'hsl(var(--success))',
        warning: 'hsl(var(--warning))',
        danger: 'hsl(var(--danger))',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
export default config
```

**Step 5: Verify build**

```bash
npx next build
```

Expected: Build succeeds.

**Step 6: Commit**

```bash
git add web/
git commit -m "feat(web): Inter font, dark theme with CSS variables, DHS logo"
```

---

### Task 3: Navbar Component

**Files:**
- Create: `web/components/navbar.tsx`
- Modify: `web/app/layout.tsx` (add Navbar to layout)

**Step 1: Create Navbar component**

Create `web/components/navbar.tsx`:

```tsx
'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'

const NAV_LINKS = [
  { href: '/wizard', label: 'Wizard' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/playground', label: 'Playground' },
  { href: '/validation', label: 'Validation' },
]

function StatusDot() {
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const check = () => {
      fetch('/api/health')
        .then(r => { setConnected(r.ok) })
        .catch(() => setConnected(false))
    }
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <div className={`w-2 h-2 rounded-full ${connected ? 'bg-success animate-pulse' : 'bg-danger'}`} />
      {connected ? 'Connected' : 'Disconnected'}
    </div>
  )
}

export function Navbar() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Left: Logo + Brand */}
        <Link href="/" className="flex items-center gap-3">
          <Image src="/dhs-logo.png" alt="DHS" width={36} height={36} className="rounded" />
          <span className="text-lg font-semibold tracking-tight">Adaptron</span>
        </Link>

        {/* Center: Nav links (desktop) */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(link => (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                pathname === link.href
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right: Status + Mobile menu */}
        <div className="flex items-center gap-4">
          <StatusDot />
          <div className="md:hidden">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-64 bg-background border-white/10">
                <nav className="flex flex-col gap-2 mt-8">
                  {NAV_LINKS.map(link => (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setOpen(false)}
                      className={`px-3 py-2 rounded-md text-sm font-medium ${
                        pathname === link.href
                          ? 'bg-primary/10 text-primary'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      {link.label}
                    </Link>
                  ))}
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  )
}
```

**Step 2: Add Navbar to layout**

Update `web/app/layout.tsx` — add `<Navbar />` inside body:

```tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Navbar } from '@/components/navbar'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Adaptron - LLM Fine-tuning Framework',
  description: 'Build, validate, and deploy production-ready language models. A product of DHS IT Solutions.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans bg-background text-foreground min-h-screen antialiased`}>
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  )
}
```

**Step 3: Verify build**

```bash
npx next build
```

Expected: Build succeeds.

**Step 4: Commit**

```bash
git add web/
git commit -m "feat(web): persistent Navbar with DHS logo and connection status"
```

---

### Task 4: Shared Components (GradeBadge, MetricCard, EmptyState)

**Files:**
- Create: `web/components/grade-badge.tsx`
- Create: `web/components/metric-card.tsx`
- Create: `web/components/empty-state.tsx`

**Step 1: Create GradeBadge**

Create `web/components/grade-badge.tsx`:

```tsx
import { Badge } from '@/components/ui/badge'

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-success/20 text-success border-success/30',
  B: 'bg-primary/20 text-primary border-primary/30',
  C: 'bg-warning/20 text-warning border-warning/30',
  D: 'bg-danger/20 text-danger border-danger/30',
  F: 'bg-danger/20 text-danger border-danger/30',
}

interface GradeBadgeProps {
  grade: string
  size?: 'sm' | 'lg'
}

export function GradeBadge({ grade, size = 'sm' }: GradeBadgeProps) {
  const colors = GRADE_COLORS[grade] || GRADE_COLORS.F
  if (size === 'lg') {
    return (
      <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl text-3xl font-bold border ${colors}`}>
        {grade}
      </div>
    )
  }
  return (
    <Badge variant="outline" className={`${colors} font-bold`}>
      {grade}
    </Badge>
  )
}
```

**Step 2: Create MetricCard**

Create `web/components/metric-card.tsx`:

```tsx
import { Card, CardContent } from '@/components/ui/card'
import { type LucideIcon } from 'lucide-react'

interface MetricCardProps {
  icon: LucideIcon
  label: string
  value: string | number
  subtitle?: string
  className?: string
}

export function MetricCard({ icon: Icon, label, value, subtitle, className }: MetricCardProps) {
  return (
    <Card className={`bg-white/5 border-white/10 backdrop-blur-sm ${className || ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{label}</p>
            <p className="text-xl font-bold mt-0.5">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Step 3: Create EmptyState**

Create `web/components/empty-state.tsx`:

```tsx
import { type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import Link from 'next/link'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  actionLabel?: string
  actionHref?: string
}

export function EmptyState({ icon: Icon, title, description, actionLabel, actionHref }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="p-4 rounded-2xl bg-white/5 border border-white/10 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-4">{description}</p>
      {actionLabel && actionHref && (
        <Button asChild>
          <Link href={actionHref}>{actionLabel}</Link>
        </Button>
      )}
    </div>
  )
}
```

**Step 4: Verify build**

```bash
npx next build
```

**Step 5: Commit**

```bash
git add web/
git commit -m "feat(web): shared components - GradeBadge, MetricCard, EmptyState"
```

---

### Task 5: Home Page Redesign

**Files:**
- Modify: `web/app/page.tsx`

**Step 1: Rewrite Home page**

Replace `web/app/page.tsx`:

```tsx
import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Wand2, LayoutDashboard, FlaskConical, ShieldCheck, ArrowRight } from 'lucide-react'

const FEATURES = [
  {
    icon: Wand2,
    title: 'Strategy Wizard',
    desc: 'Configure your fine-tuning strategy with guided recommendations.',
    href: '/wizard',
  },
  {
    icon: LayoutDashboard,
    title: 'Dashboard',
    desc: 'Monitor training pipelines, jobs, and model deployments.',
    href: '/dashboard',
  },
  {
    icon: FlaskConical,
    title: 'Playground',
    desc: 'Test and compare your fine-tuned models interactively.',
    href: '/playground',
  },
  {
    icon: ShieldCheck,
    title: 'Validation',
    desc: 'Prove model fitness with benchmarks and hallucination detection.',
    href: '/validation',
  },
]

export default function Home() {
  return (
    <div className="flex flex-col items-center">
      {/* Hero */}
      <section className="w-full max-w-4xl mx-auto px-4 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-muted-foreground mb-6">
          <Image src="/dhs-logo.png" alt="DHS" width={16} height={16} className="rounded" />
          A product of DHS IT Solutions
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-4">
          <span className="bg-gradient-to-r from-primary via-purple-400 to-primary bg-clip-text text-transparent">
            Adaptron
          </span>
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
          Build, validate, and deploy production-ready language models from your enterprise data.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Button size="lg" asChild>
            <Link href="/wizard">
              Start Wizard <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button size="lg" variant="outline" asChild className="border-white/10 hover:bg-white/5">
            <Link href="/dashboard">View Dashboard</Link>
          </Button>
        </div>
      </section>

      {/* Feature Cards */}
      <section className="w-full max-w-5xl mx-auto px-4 pb-24">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.map(f => (
            <Link key={f.href} href={f.href} className="group">
              <Card className="h-full bg-white/5 border-white/10 backdrop-blur-sm transition-all duration-200 group-hover:bg-white/8 group-hover:border-white/20 group-hover:-translate-y-0.5">
                <CardContent className="p-5">
                  <div className="p-2 rounded-lg bg-primary/10 w-fit mb-3">
                    <f.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-1">{f.title}</h3>
                  <p className="text-sm text-muted-foreground">{f.desc}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full border-t border-white/10 py-6 text-center text-xs text-muted-foreground">
        DHS IT Solutions &middot; Adaptron v0.2.0
      </footer>
    </div>
  )
}
```

**Step 2: Verify build**

```bash
npx next build
```

**Step 3: Commit**

```bash
git add web/app/page.tsx
git commit -m "feat(web): production home page with hero and feature cards"
```

---

### Task 6: Wizard Page Redesign

**Files:**
- Modify: `web/app/wizard/page.tsx`

**Step 1: Rewrite Wizard page**

Replace `web/app/wizard/page.tsx` with the same 7-step logic but using shadcn components:

```tsx
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { ArrowLeft, ArrowRight, Check, RotateCcw } from 'lucide-react'

const QUESTIONS = [
  {
    id: 'primary_goal', title: 'What is your primary goal?',
    subtitle: 'Select the outcome that best describes what you need from your SLM.',
    options: [
      { id: 'qa_docs', label: 'Domain Q&A', desc: 'Answer questions from my documents accurately', icon: '\u{1F4C4}' },
      { id: 'erp_edw', label: 'ERP / EDW Intelligence', desc: 'Query and reason over ERP or data warehouse data', icon: '\u{1F5C4}\uFE0F' },
      { id: 'report_gen', label: 'Report & Content Generation', desc: 'Generate structured reports, summaries, and outputs', icon: '\u{1F4CA}' },
      { id: 'specialist', label: 'Deep Domain Specialist', desc: 'Build a model that truly thinks in my domain language', icon: '\u{1F3AF}' },
    ],
  },
  {
    id: 'data_sources', title: 'What data sources will you connect?', multi: true,
    subtitle: 'Select all that apply.',
    options: [
      { id: 'docs', label: 'Documents', desc: 'PDF, DOCX, XLSX, HTML files', icon: '\u{1F4C1}' },
      { id: 'erp', label: 'ERP System', desc: 'SAP, Oracle, MS Dynamics', icon: '\u2699\uFE0F' },
      { id: 'edw', label: 'Data Warehouse', desc: 'Snowflake, Redshift, BigQuery', icon: '\u{1F3DB}\uFE0F' },
      { id: 'db', label: 'Database', desc: 'PostgreSQL, MySQL, SQL Server', icon: '\u{1F5C3}\uFE0F' },
    ],
  },
  {
    id: 'data_freshness', title: 'How often does your data change?',
    subtitle: 'This determines whether knowledge should be baked into weights or retrieved at runtime.',
    options: [
      { id: 'static', label: 'Mostly Static', desc: 'Data changes rarely', icon: '\u{1F5FF}' },
      { id: 'monthly', label: 'Periodic Updates', desc: 'Data changes monthly or quarterly', icon: '\u{1F4C5}' },
      { id: 'daily', label: 'Frequently Changing', desc: 'Data changes daily', icon: '\u26A1' },
      { id: 'realtime', label: 'Real-Time', desc: 'Operational data that changes by the minute', icon: '\u{1F534}' },
    ],
  },
  {
    id: 'hardware', title: 'What GPU hardware do you have available?',
    subtitle: 'VRAM determines which training modes and base models are feasible.',
    options: [
      { id: 'low', label: '\u2264 8GB VRAM', desc: 'RTX 3070/4060 or equivalent', icon: '\u{1F4BB}' },
      { id: 'mid', label: '12\u201316GB VRAM', desc: 'RTX 3080/4080', icon: '\u{1F5A5}\uFE0F' },
      { id: 'high', label: '24GB+ VRAM', desc: 'RTX 4090 / A100', icon: '\u{1F680}' },
      { id: 'cloud', label: 'Cloud GPU Burst', desc: 'RunPod, Lambda Labs, or similar', icon: '\u2601\uFE0F' },
    ],
  },
  {
    id: 'timeline', title: 'What is your acceptable build time?',
    subtitle: 'Training duration varies significantly by mode and hardware.',
    options: [
      { id: 'fast', label: 'Under 2 Hours', desc: 'Need results quickly', icon: '\u23F1\uFE0F' },
      { id: 'medium', label: '2\u20138 Hours', desc: 'Acceptable for overnight builds', icon: '\u{1F550}' },
      { id: 'long', label: '8\u201324 Hours', desc: 'Can run extended training', icon: '\u{1F4C6}' },
      { id: 'unlimited', label: 'No Constraint', desc: 'Quality is the priority', icon: '\u267E\uFE0F' },
    ],
  },
  {
    id: 'accuracy', title: 'What accuracy level do your users require?',
    subtitle: 'Higher accuracy requirements demand more sophisticated strategies.',
    options: [
      { id: 'exploratory', label: 'Exploratory / Prototype', desc: '70\u201380% accuracy is fine', icon: '\u{1F9EA}' },
      { id: 'professional', label: 'Professional Grade', desc: '80\u201390% accuracy', icon: '\u{1F4BC}' },
      { id: 'enterprise', label: 'Enterprise Production', desc: '90%+ accuracy', icon: '\u{1F3E2}' },
      { id: 'mission', label: 'Mission Critical', desc: 'Near-perfect accuracy required', icon: '\u{1F396}\uFE0F' },
    ],
  },
  {
    id: 'model_size', title: 'What is your target model size?',
    subtitle: 'Smaller models are faster and cheaper but have lower reasoning ceilings.',
    options: [
      { id: 'tiny', label: 'Tiny (1\u20133B)', desc: 'Fastest inference, basic tasks', icon: '\u{1F43E}' },
      { id: 'small', label: 'Small (3\u20137B)', desc: 'Best quality/speed balance', icon: '\u2696\uFE0F' },
      { id: 'medium', label: 'Medium (7\u201313B)', desc: 'Strong reasoning, more VRAM', icon: '\u{1F4AA}' },
      { id: 'large', label: 'Large (13B+)', desc: 'Near-frontier quality locally', icon: '\u{1F9BE}' },
    ],
  },
]

interface WizardResult {
  training_modes: string[]
  base_model: string
  deploy_targets: string[]
}

export default function WizardPage() {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({})
  const [result, setResult] = useState<WizardResult | null>(null)
  const [loading, setLoading] = useState(false)

  const q = QUESTIONS[step]
  const isMulti = 'multi' in q && q.multi
  const currentAnswer = answers[q?.id]
  const isAnswered = isMulti ? Array.isArray(currentAnswer) && currentAnswer.length > 0 : !!currentAnswer

  const handleSelect = (optId: string) => {
    if (isMulti) {
      const cur = (answers[q.id] as string[]) || []
      setAnswers({ ...answers, [q.id]: cur.includes(optId) ? cur.filter(x => x !== optId) : [...cur, optId] })
    } else {
      setAnswers({ ...answers, [q.id]: optId })
    }
  }

  const isSelected = (optId: string) => {
    if (isMulti) return Array.isArray(currentAnswer) && currentAnswer.includes(optId)
    return currentAnswer === optId
  }

  const handleNext = async () => {
    if (step < QUESTIONS.length - 1) {
      setStep(step + 1)
    } else {
      setLoading(true)
      try {
        const resp = await fetch('/api/wizard/recommend', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(answers),
        })
        setResult(await resp.json())
      } catch {
        setResult({ training_modes: ['qlora'], base_model: 'Qwen/Qwen2.5-7B-Instruct', deploy_targets: ['gguf', 'ollama'] })
      }
      setLoading(false)
    }
  }

  if (result) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <Badge variant="outline" className="bg-success/10 text-success border-success/30 mb-4">Analysis Complete</Badge>
        <h1 className="text-3xl font-bold mb-1">Recommended Strategy</h1>
        <p className="text-muted-foreground mb-8">Based on your {Object.keys(answers).length} selections.</p>

        <div className="space-y-4">
          <Card className="bg-white/5 border-white/10 backdrop-blur-sm">
            <CardContent className="p-6">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-3">Training Modes</p>
              <div className="flex gap-2 flex-wrap">
                {result.training_modes.map(mode => (
                  <Badge key={mode} className="bg-primary/10 text-primary border-primary/30 text-sm px-3 py-1">{mode}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/5 border-white/10 backdrop-blur-sm">
            <CardContent className="p-6">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-2">Base Model</p>
              <p className="text-xl font-bold text-primary">{result.base_model}</p>
            </CardContent>
          </Card>

          <Card className="bg-white/5 border-white/10 backdrop-blur-sm">
            <CardContent className="p-6">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-3">Deploy Targets</p>
              <div className="flex gap-2">
                {result.deploy_targets.map(t => (
                  <Badge key={t} className="bg-success/10 text-success border-success/30 text-sm px-3 py-1">{t}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <Button onClick={() => { setResult(null); setStep(0); setAnswers({}) }} className="mt-6">
          <RotateCcw className="mr-2 h-4 w-4" /> New Analysis
        </Button>
      </div>
    )
  }

  const progress = ((step + 1) / QUESTIONS.length) * 100

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      {/* Progress */}
      <div className="mb-10">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-muted-foreground">Step {step + 1} of {QUESTIONS.length}</span>
          <span className="text-xs text-muted-foreground">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-1.5" />
      </div>

      {/* Question */}
      <h1 className="text-2xl font-bold mb-1">{q.title}</h1>
      <p className="text-sm text-muted-foreground mb-6">{q.subtitle}</p>
      {isMulti && (
        <Badge variant="outline" className="mb-4 text-xs border-white/10">Select all that apply</Badge>
      )}

      {/* Options */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
        {q.options.map(opt => (
          <button
            key={opt.id}
            onClick={() => handleSelect(opt.id)}
            className={`text-left p-4 rounded-xl border transition-all duration-200 ${
              isSelected(opt.id)
                ? 'bg-primary/10 border-primary/40 shadow-lg shadow-primary/10'
                : 'bg-white/5 border-white/10 hover:bg-white/8 hover:border-white/20 hover:-translate-y-0.5'
            }`}
          >
            <div className="flex items-start gap-3">
              <span className="text-xl mt-0.5">{opt.icon}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${isSelected(opt.id) ? 'text-primary' : 'text-foreground'}`}>{opt.label}</span>
                  {isSelected(opt.id) && <Check className="h-3.5 w-3.5 text-primary" />}
                </div>
                <span className="text-xs text-muted-foreground mt-0.5 block">{opt.desc}</span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <Button variant="ghost" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back
        </Button>
        <Button onClick={handleNext} disabled={!isAnswered || loading}>
          {loading ? 'Analyzing...' : step === QUESTIONS.length - 1 ? 'Analyze' : 'Next'}
          {!loading && <ArrowRight className="ml-2 h-4 w-4" />}
        </Button>
      </div>
    </div>
  )
}
```

**Step 2: Verify build**

```bash
npx next build
```

**Step 3: Commit**

```bash
git add web/app/wizard/page.tsx
git commit -m "feat(web): production wizard page with shadcn/ui components"
```

---

### Task 7: Dashboard Page Redesign

**Files:**
- Modify: `web/app/dashboard/page.tsx`

**Step 1: Rewrite Dashboard page**

Replace `web/app/dashboard/page.tsx`:

```tsx
'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { MetricCard } from '@/components/metric-card'
import { EmptyState } from '@/components/empty-state'
import { Activity, Layers, Cpu, Rocket, CheckCircle2, XCircle, Loader2 } from 'lucide-react'

interface Pipeline {
  id: string
  name: string
  status: string
  progress?: number
  created_at?: string
}

const STATUS_CONFIG: Record<string, { color: string; icon: typeof CheckCircle2 }> = {
  running: { color: 'bg-primary/10 text-primary border-primary/30', icon: Loader2 },
  completed: { color: 'bg-success/10 text-success border-success/30', icon: CheckCircle2 },
  failed: { color: 'bg-danger/10 text-danger border-danger/30', icon: XCircle },
}

export default function DashboardPage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPipelines = () => {
      fetch('/api/pipelines')
        .then(r => r.json())
        .then(data => {
          setPipelines(Array.isArray(data) ? data : [])
          setLoading(false)
        })
        .catch(() => setLoading(false))
    }
    fetchPipelines()
    const interval = setInterval(fetchPipelines, 10000)
    return () => clearInterval(interval)
  }, [])

  const running = pipelines.filter(p => p.status === 'running').length
  const completed = pipelines.filter(p => p.status === 'completed').length
  const failed = pipelines.filter(p => p.status === 'failed').length

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-1">Dashboard</h1>
      <p className="text-muted-foreground mb-8">Monitor your fine-tuning pipelines and deployments.</p>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard icon={Layers} label="Total Pipelines" value={pipelines.length} />
        <MetricCard icon={Activity} label="Running" value={running} />
        <MetricCard icon={Cpu} label="Completed" value={completed} />
        <MetricCard icon={Rocket} label="Failed" value={failed} />
      </div>

      {/* Pipeline list */}
      <Card className="bg-white/5 border-white/10 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-medium uppercase tracking-wider text-muted-foreground">Pipelines</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : pipelines.length === 0 ? (
            <EmptyState
              icon={Layers}
              title="No pipelines yet"
              description="Start a fine-tuning pipeline from the wizard to see it here."
              actionLabel="Go to Wizard"
              actionHref="/wizard"
            />
          ) : (
            <div className="space-y-3">
              {pipelines.map(p => {
                const cfg = STATUS_CONFIG[p.status] || STATUS_CONFIG.failed
                const StatusIcon = cfg.icon
                return (
                  <div key={p.id} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
                    <div className="flex items-center gap-3">
                      <StatusIcon className={`h-4 w-4 ${p.status === 'running' ? 'animate-spin text-primary' : cfg.color.includes('success') ? 'text-success' : 'text-danger'}`} />
                      <div>
                        <p className="text-sm font-medium">{p.name}</p>
                        {p.created_at && <p className="text-xs text-muted-foreground">{p.created_at}</p>}
                      </div>
                    </div>
                    <Badge variant="outline" className={cfg.color}>{p.status}</Badge>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

**Step 2: Verify build**

```bash
npx next build
```

**Step 3: Commit**

```bash
git add web/app/dashboard/page.tsx
git commit -m "feat(web): production dashboard with metric cards and pipeline list"
```

---

### Task 8: Playground Page Redesign

**Files:**
- Modify: `web/app/playground/page.tsx`

**Step 1: Rewrite Playground page**

Replace `web/app/playground/page.tsx`:

```tsx
'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Send, Trash2, Settings2, Bot, User, Columns2 } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  model?: string
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
        isUser ? 'bg-primary/10' : 'bg-white/10'
      }`}>
        {isUser ? <User className="h-4 w-4 text-primary" /> : <Bot className="h-4 w-4 text-muted-foreground" />}
      </div>
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
        isUser
          ? 'bg-primary/10 border border-primary/20'
          : 'bg-white/5 border border-white/10'
      }`}>
        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{msg.content}</pre>
      </div>
    </div>
  )
}

function StreamingBubble({ content }: { content: string }) {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-white/10">
        <Bot className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="max-w-[75%] rounded-2xl px-4 py-3 text-sm bg-white/5 border border-white/10">
        <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{content}<span className="inline-block w-2 h-4 bg-primary/60 animate-pulse ml-0.5 rounded-sm" /></pre>
      </div>
    </div>
  )
}

export default function PlaygroundPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [compareMessages, setCompareMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [model, setModel] = useState('')
  const [compareModel, setCompareModel] = useState('')
  const [models, setModels] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [temperature, setTemperature] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [ragEnabled, setRagEnabled] = useState(false)
  const [compareMode, setCompareMode] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch('/api/playground/models')
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          const names = data.map((m: any) => m.name)
          setModels(names)
          if (names.length > 0) setModel(names[0])
          if (names.length > 1) setCompareModel(names[1])
        }
      })
      .catch(() => setModels([]))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const sendMessage = async () => {
    if (!input.trim() || !model || loading) return
    const userMsg: Message = { role: 'user', content: input.trim() }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setStreamingContent('')

    const apiMessages = newMessages.map(m => ({ role: m.role, content: m.content }))

    try {
      const resp = await fetch('/api/playground/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, messages: apiMessages, temperature, max_tokens: maxTokens, stream: true, rag_enabled: ragEnabled }),
      })
      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const lines = decoder.decode(value).split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') continue
              try {
                const parsed = JSON.parse(data)
                if (parsed.token) { fullContent += parsed.token; setStreamingContent(fullContent) }
              } catch {}
            }
          }
        }
      }
      setMessages(prev => [...prev, { role: 'assistant', content: fullContent, model }])
      setStreamingContent('')
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e}`, model }])
      setStreamingContent('')
    }

    if (compareMode && compareModel && compareModel !== model) {
      try {
        const resp = await fetch('/api/playground/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: compareModel, messages: apiMessages, temperature, max_tokens: maxTokens, stream: false, rag_enabled: ragEnabled }),
        })
        const data = await resp.json()
        setCompareMessages(prev => [...prev, userMsg, { role: 'assistant', content: data.content || data.error || 'No response', model: compareModel }])
      } catch (e) {
        setCompareMessages(prev => [...prev, userMsg, { role: 'assistant', content: `Error: ${e}`, model: compareModel }])
      }
    }
    setLoading(false)
  }

  const ChatPanel = ({ msgs, streaming, modelName }: { msgs: Message[]; streaming: string; modelName: string }) => (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3 px-1">
        <Bot className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-medium text-primary">{modelName || 'No model'}</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {msgs.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
        {streaming && <StreamingBubble content={streaming} />}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 bg-white/5 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <select value={model} onChange={e => setModel(e.target.value)}
            className="bg-background border border-white/10 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary">
            {models.length === 0 && <option value="">No models</option>}
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <Button variant={compareMode ? 'default' : 'ghost'} size="sm"
            onClick={() => { setCompareMode(!compareMode); setCompareMessages([]) }}>
            <Columns2 className="mr-1.5 h-3.5 w-3.5" /> Compare
          </Button>
          {compareMode && (
            <select value={compareModel} onChange={e => setCompareModel(e.target.value)}
              className="bg-background border border-white/10 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary">
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant={ragEnabled ? 'default' : 'ghost'} size="sm" onClick={() => setRagEnabled(!ragEnabled)}>
            RAG {ragEnabled ? 'ON' : 'OFF'}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setShowSettings(!showSettings)}>
            <Settings2 className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => { setMessages([]); setCompareMessages([]); setStreamingContent('') }}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Settings panel */}
      {showSettings && (
        <div className="px-4 py-3 border-b border-white/10 bg-white/5 flex items-center gap-8">
          <label className="flex items-center gap-3 text-xs text-muted-foreground">
            Temperature
            <input type="range" min="0" max="2" step="0.1" value={temperature} onChange={e => setTemperature(parseFloat(e.target.value))}
              className="w-28 accent-primary" />
            <span className="text-primary font-semibold w-8">{temperature}</span>
          </label>
          <label className="flex items-center gap-3 text-xs text-muted-foreground">
            Max Tokens
            <input type="range" min="256" max="8192" step="256" value={maxTokens} onChange={e => setMaxTokens(parseInt(e.target.value))}
              className="w-28 accent-primary" />
            <span className="text-primary font-semibold w-12">{maxTokens}</span>
          </label>
        </div>
      )}

      {/* Chat area */}
      <div className="flex-1 overflow-hidden flex">
        <div className={`flex-1 p-4 ${compareMode ? 'border-r border-white/10' : ''}`}>
          <ChatPanel msgs={messages} streaming={streamingContent} modelName={model} />
        </div>
        {compareMode && (
          <div className="flex-1 p-4">
            <ChatPanel msgs={compareMessages} streaming="" modelName={compareModel} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-white/10 bg-white/5 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Type your message..."
            disabled={loading || !model}
            className="flex-1 bg-background border border-white/10 rounded-xl px-4 py-3 text-sm placeholder-muted-foreground focus:outline-none focus:border-primary disabled:opacity-50 transition-colors"
          />
          <Button onClick={sendMessage} disabled={loading || !input.trim() || !model} size="lg">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: Verify build**

```bash
npx next build
```

**Step 3: Commit**

```bash
git add web/app/playground/page.tsx
git commit -m "feat(web): production playground with chat bubbles and settings panel"
```

---

### Task 9: Validation Page (New)

**Files:**
- Create: `web/app/validation/page.tsx`

**Step 1: Create Validation page**

Create `web/app/validation/page.tsx`:

```tsx
'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { GradeBadge } from '@/components/grade-badge'
import { MetricCard } from '@/components/metric-card'
import { EmptyState } from '@/components/empty-state'
import { ShieldCheck, BarChart3, GitCompare, Gauge, BrainCircuit, Play, Loader2, AlertTriangle } from 'lucide-react'

interface ValidationReport {
  model_info: Record<string, any>
  benchmark: { task_type: string; metrics: Record<string, number>; grade: string; per_sample: any[] } | null
  comparison: { wins: number; losses: number; ties: number; improvement_pct: Record<string, number> } | null
  readiness: { latency: Record<string, number>; consistency_score: number; format_compliance: number; checks: Record<string, string> } | null
  hallucination: { mode: string; faithfulness_score: number | null; consistency_score: number | null; hallucination_rate: number; flagged_samples: any[] } | null
  overall_grade: string
  summary: string
  timestamp: string
}

const TABS = ['benchmark', 'comparison', 'readiness', 'hallucination'] as const
type TabId = typeof TABS[number]
const TAB_LABELS: Record<TabId, { label: string; icon: typeof BarChart3 }> = {
  benchmark: { label: 'Benchmark', icon: BarChart3 },
  comparison: { label: 'Comparison', icon: GitCompare },
  readiness: { label: 'Readiness', icon: Gauge },
  hallucination: { label: 'Hallucination', icon: BrainCircuit },
}

export default function ValidationPage() {
  const [report, setReport] = useState<ValidationReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [activeTab, setActiveTab] = useState<TabId>('benchmark')
  const [modelPath, setModelPath] = useState('')
  const [testDataPath, setTestDataPath] = useState('')

  useEffect(() => {
    fetch('/api/validate/report')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setReport(data) })
      .catch(() => {})
  }, [])

  const startValidation = async () => {
    if (!modelPath) return
    setValidating(true)
    try {
      await fetch('/api/validate/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_path: modelPath, test_data_path: testDataPath || undefined }),
      })
      // Poll for completion
      const poll = setInterval(async () => {
        const resp = await fetch('/api/validate/status')
        const data = await resp.json()
        if (data.status === 'complete' || data.status === 'idle') {
          clearInterval(poll)
          const reportResp = await fetch('/api/validate/report')
          if (reportResp.ok) setReport(await reportResp.json())
          setValidating(false)
        }
      }, 3000)
    } catch {
      setValidating(false)
    }
  }

  if (!report) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold mb-1">Model Validation</h1>
        <p className="text-muted-foreground mb-8">Prove your model is fit for production with automated benchmarks.</p>

        <Card className="bg-white/5 border-white/10 backdrop-blur-sm">
          <CardContent className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">Model Path</label>
              <input
                value={modelPath}
                onChange={e => setModelPath(e.target.value)}
                placeholder="./output/my-model"
                className="w-full bg-background border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Test Data Path <span className="text-muted-foreground">(optional)</span></label>
              <input
                value={testDataPath}
                onChange={e => setTestDataPath(e.target.value)}
                placeholder="./test.jsonl"
                className="w-full bg-background border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
              />
            </div>
            <Button onClick={startValidation} disabled={!modelPath || validating}>
              {validating ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Validating...</> : <><Play className="mr-2 h-4 w-4" /> Run Validation</>}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-1">Validation Report</h1>
          <p className="text-muted-foreground text-sm">{report.summary}</p>
        </div>
        <div className="flex items-center gap-4">
          <GradeBadge grade={report.overall_grade} size="lg" />
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {report.benchmark && (
          <MetricCard icon={BarChart3} label="Benchmark" value={`F1: ${(report.benchmark.metrics.f1 ?? report.benchmark.metrics.accuracy ?? 0).toFixed(2)}`} subtitle={`Grade: ${report.benchmark.grade}`} />
        )}
        {report.hallucination && (
          <MetricCard icon={BrainCircuit} label="Hallucination Rate" value={`${(report.hallucination.hallucination_rate * 100).toFixed(1)}%`} subtitle={`${report.hallucination.flagged_samples.length} flagged`} />
        )}
        {report.readiness && (
          <MetricCard icon={Gauge} label="Latency (p50)" value={`${(report.readiness.latency.p50 ?? 0).toFixed(0)}ms`} subtitle={`Consistency: ${(report.readiness.consistency_score * 100).toFixed(0)}%`} />
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-white/10 pb-px">
        {TABS.map(tab => {
          const cfg = TAB_LABELS[tab]
          const Icon = cfg.icon
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab
                  ? 'bg-white/5 text-primary border-b-2 border-primary -mb-px'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="h-4 w-4" />
              {cfg.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <Card className="bg-white/5 border-white/10 backdrop-blur-sm">
        <CardContent className="p-6">
          {activeTab === 'benchmark' && report.benchmark && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <Badge variant="outline" className="border-white/10">{report.benchmark.task_type}</Badge>
                <GradeBadge grade={report.benchmark.grade} />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                {Object.entries(report.benchmark.metrics).map(([k, v]) => (
                  <div key={k} className="p-3 rounded-lg bg-white/5 border border-white/10">
                    <p className="text-xs text-muted-foreground uppercase">{k}</p>
                    <p className="text-lg font-bold">{typeof v === 'number' ? v.toFixed(3) : v}</p>
                  </div>
                ))}
              </div>
              {report.benchmark.per_sample.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left py-2 px-3 text-xs text-muted-foreground">#</th>
                        <th className="text-left py-2 px-3 text-xs text-muted-foreground">Prediction</th>
                        <th className="text-left py-2 px-3 text-xs text-muted-foreground">Reference</th>
                        <th className="text-left py-2 px-3 text-xs text-muted-foreground">Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.benchmark.per_sample.slice(0, 20).map((s: any, i: number) => (
                        <tr key={i} className="border-b border-white/5">
                          <td className="py-2 px-3 text-muted-foreground">{s.index}</td>
                          <td className="py-2 px-3 max-w-xs truncate">{s.prediction}</td>
                          <td className="py-2 px-3 max-w-xs truncate">{s.reference}</td>
                          <td className="py-2 px-3">
                            {s.correct
                              ? <Badge className="bg-success/10 text-success border-success/30">Pass</Badge>
                              : <Badge className="bg-danger/10 text-danger border-danger/30">Fail</Badge>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === 'comparison' && report.comparison && (
            <div>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-4 rounded-lg bg-success/5 border border-success/20 text-center">
                  <p className="text-2xl font-bold text-success">{report.comparison.wins}</p>
                  <p className="text-xs text-muted-foreground">Wins</p>
                </div>
                <div className="p-4 rounded-lg bg-white/5 border border-white/10 text-center">
                  <p className="text-2xl font-bold">{report.comparison.ties}</p>
                  <p className="text-xs text-muted-foreground">Ties</p>
                </div>
                <div className="p-4 rounded-lg bg-danger/5 border border-danger/20 text-center">
                  <p className="text-2xl font-bold text-danger">{report.comparison.losses}</p>
                  <p className="text-xs text-muted-foreground">Losses</p>
                </div>
              </div>
              {Object.keys(report.comparison.improvement_pct).length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Improvement vs Baseline</p>
                  {Object.entries(report.comparison.improvement_pct).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between py-2 border-b border-white/5">
                      <span className="text-sm">{k}</span>
                      <span className={`text-sm font-bold ${v >= 0 ? 'text-success' : 'text-danger'}`}>{v >= 0 ? '+' : ''}{v.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'comparison' && !report.comparison && (
            <EmptyState icon={GitCompare} title="No comparison data" description="Run validation with a baseline model to see comparison results." />
          )}

          {activeTab === 'readiness' && report.readiness && (
            <div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                {Object.entries(report.readiness.latency).map(([k, v]) => (
                  <div key={k} className="p-3 rounded-lg bg-white/5 border border-white/10">
                    <p className="text-xs text-muted-foreground uppercase">{k}</p>
                    <p className="text-lg font-bold">{typeof v === 'number' ? `${v.toFixed(1)}ms` : v}</p>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                {Object.entries(report.readiness.checks).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between py-2 border-b border-white/5">
                    <span className="text-sm">{k}</span>
                    <Badge variant="outline" className={
                      v === 'pass' ? 'bg-success/10 text-success border-success/30'
                        : v === 'warning' ? 'bg-warning/10 text-warning border-warning/30'
                        : 'bg-danger/10 text-danger border-danger/30'
                    }>{v}</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'readiness' && !report.readiness && (
            <EmptyState icon={Gauge} title="No readiness data" description="Readiness checks were not run for this validation." />
          )}

          {activeTab === 'hallucination' && report.hallucination && (
            <div>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                  <p className="text-xs text-muted-foreground uppercase">Mode</p>
                  <p className="text-sm font-bold capitalize">{report.hallucination.mode}</p>
                </div>
                {report.hallucination.faithfulness_score !== null && (
                  <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                    <p className="text-xs text-muted-foreground uppercase">Faithfulness</p>
                    <p className="text-lg font-bold">{(report.hallucination.faithfulness_score * 100).toFixed(1)}%</p>
                  </div>
                )}
                {report.hallucination.consistency_score !== null && (
                  <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                    <p className="text-xs text-muted-foreground uppercase">Consistency</p>
                    <p className="text-lg font-bold">{(report.hallucination.consistency_score * 100).toFixed(1)}%</p>
                  </div>
                )}
              </div>
              {report.hallucination.flagged_samples.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-warning" /> Flagged Samples
                  </p>
                  <div className="space-y-2">
                    {report.hallucination.flagged_samples.map((s: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg bg-warning/5 border border-warning/20">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className="bg-warning/10 text-warning border-warning/30 text-xs">#{s.index}</Badge>
                          {s.overlap !== undefined && <span className="text-xs text-muted-foreground">Overlap: {(s.overlap * 100).toFixed(1)}%</span>}
                          {s.avg_similarity !== undefined && <span className="text-xs text-muted-foreground">Similarity: {(s.avg_similarity * 100).toFixed(1)}%</span>}
                        </div>
                        {s.prediction && <p className="text-xs text-muted-foreground mt-1 truncate">Prediction: {s.prediction}</p>}
                        {s.reference && <p className="text-xs text-muted-foreground truncate">Reference: {s.reference}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'hallucination' && !report.hallucination && (
            <EmptyState icon={BrainCircuit} title="No hallucination data" description="Hallucination detection was not run for this validation." />
          )}

          {activeTab === 'benchmark' && !report.benchmark && (
            <EmptyState icon={BarChart3} title="No benchmark data" description="Benchmark evaluation was not run for this validation." />
          )}
        </CardContent>
      </Card>

      {/* Run again */}
      <div className="mt-6 flex justify-end">
        <Button variant="outline" className="border-white/10" onClick={() => setReport(null)}>
          Run New Validation
        </Button>
      </div>
    </div>
  )
}
```

**Step 2: Verify build**

```bash
npx next build
```

**Step 3: Commit**

```bash
git add web/app/validation/
git commit -m "feat(web): validation page with grade badges, metrics, and tabbed detail view"
```

---

### Task 10: Build, Deploy, and Verify

**Files:**
- Modify: `web/next.config.js` (already has standalone output)

**Step 1: Full build**

```bash
cd web && npx next build
```

Expected: Build succeeds with all 5 pages + layout.

**Step 2: Create deployment zip**

```bash
node -e "
const yazl = require('yazl');
const fs = require('fs');
const path = require('path');
const zipfile = new yazl.ZipFile();
const base = path.join(__dirname, '.next', 'standalone');
function addDir(dir, b) {
  for (const e of fs.readdirSync(dir, {withFileTypes:true})) {
    const fp = path.join(dir, e.name);
    const ap = path.relative(b, fp).split(path.sep).join('/');
    if (e.isDirectory()) addDir(fp, b); else zipfile.addFile(fp, ap);
  }
}
addDir(base, base);
zipfile.outputStream.pipe(fs.createWriteStream('deploy.zip')).on('close', () => console.log('Created deploy.zip'));
zipfile.end();
"
```

**Step 3: Deploy to Azure**

```bash
az webapp deploy --resource-group rg-dhs-sap --name adaptron-app --src-path deploy.zip --type zip --clean true
```

Expected: Deployment succeeds, site starts.

**Step 4: Verify site is live**

```bash
curl -s -o /dev/null -w "%{http_code}" https://adaptron-app.azurewebsites.net/
```

Expected: `200`

**Step 5: Clean up and commit**

```bash
rm -f deploy.zip
git add web/
git commit -m "chore(web): production build and deploy to Azure"
```

---

## Summary

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | Install shadcn/ui and dependencies | package.json, components/ui/* |
| 2 | Theme, font, layout foundation | layout.tsx, globals.css, tailwind.config.ts |
| 3 | Navbar component | components/navbar.tsx, layout.tsx |
| 4 | Shared components | grade-badge, metric-card, empty-state |
| 5 | Home page redesign | app/page.tsx |
| 6 | Wizard page redesign | app/wizard/page.tsx |
| 7 | Dashboard page redesign | app/dashboard/page.tsx |
| 8 | Playground page redesign | app/playground/page.tsx |
| 9 | Validation page (new) | app/validation/page.tsx |
| 10 | Build, deploy, verify | Azure deployment |
