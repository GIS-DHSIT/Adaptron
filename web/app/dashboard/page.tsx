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
