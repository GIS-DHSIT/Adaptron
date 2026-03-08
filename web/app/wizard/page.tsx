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
                : 'bg-white/5 border-white/10 hover:bg-white/[0.08] hover:border-white/20 hover:-translate-y-0.5'
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
