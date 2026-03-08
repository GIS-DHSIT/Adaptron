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
              <Card className="h-full bg-white/5 border-white/10 backdrop-blur-sm transition-all duration-200 group-hover:bg-white/[0.08] group-hover:border-white/20 group-hover:-translate-y-0.5">
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
