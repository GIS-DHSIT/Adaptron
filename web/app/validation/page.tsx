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
      const poll = setInterval(async () => {
        try {
          const resp = await fetch('/api/validate/status')
          const data = await resp.json()
          if (data.status === 'complete' || data.status === 'idle') {
            clearInterval(poll)
            const reportResp = await fetch('/api/validate/report')
            if (reportResp.ok) setReport(await reportResp.json())
            setValidating(false)
          }
        } catch {
          clearInterval(poll)
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
        <GradeBadge grade={report.overall_grade} size="lg" />
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

          {/* Empty states for missing data */}
          {activeTab === 'benchmark' && !report.benchmark && (
            <EmptyState icon={BarChart3} title="No benchmark data" description="Benchmark evaluation was not run for this validation." />
          )}
          {activeTab === 'comparison' && !report.comparison && (
            <EmptyState icon={GitCompare} title="No comparison data" description="Run validation with a baseline model to see comparison results." />
          )}
          {activeTab === 'readiness' && !report.readiness && (
            <EmptyState icon={Gauge} title="No readiness data" description="Readiness checks were not run for this validation." />
          )}
          {activeTab === 'hallucination' && !report.hallucination && (
            <EmptyState icon={BrainCircuit} title="No hallucination data" description="Hallucination detection was not run for this validation." />
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
