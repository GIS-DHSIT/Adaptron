'use client'

import { useState } from 'react'

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
      { id: 'mid', label: '12-16GB VRAM', desc: 'RTX 3080/4080', icon: '\u{1F5A5}\uFE0F' },
      { id: 'high', label: '24GB+ VRAM', desc: 'RTX 4090 / A100', icon: '\u{1F680}' },
      { id: 'cloud', label: 'Cloud GPU Burst', desc: 'RunPod, Lambda Labs, or similar', icon: '\u2601\uFE0F' },
    ],
  },
  {
    id: 'timeline', title: 'What is your acceptable build time?',
    subtitle: 'Training duration varies significantly by mode and hardware.',
    options: [
      { id: 'fast', label: 'Under 2 Hours', desc: 'Need results quickly', icon: '\u23F1\uFE0F' },
      { id: 'medium', label: '2-8 Hours', desc: 'Acceptable for overnight builds', icon: '\u{1F550}' },
      { id: 'long', label: '8-24 Hours', desc: 'Can run extended training', icon: '\u{1F4C6}' },
      { id: 'unlimited', label: 'No Constraint', desc: 'Quality is the priority', icon: '\u267E\uFE0F' },
    ],
  },
  {
    id: 'accuracy', title: 'What accuracy level do your users require?',
    subtitle: 'Higher accuracy requirements demand more sophisticated strategies.',
    options: [
      { id: 'exploratory', label: 'Exploratory / Prototype', desc: '70-80% accuracy is fine', icon: '\u{1F9EA}' },
      { id: 'professional', label: 'Professional Grade', desc: '80-90% accuracy', icon: '\u{1F4BC}' },
      { id: 'enterprise', label: 'Enterprise Production', desc: '90%+ accuracy', icon: '\u{1F3E2}' },
      { id: 'mission', label: 'Mission Critical', desc: 'Near-perfect accuracy required', icon: '\u{1F396}\uFE0F' },
    ],
  },
  {
    id: 'model_size', title: 'What is your target model size?',
    subtitle: 'Smaller models are faster and cheaper but have lower reasoning ceilings.',
    options: [
      { id: 'tiny', label: 'Tiny (1-3B)', desc: 'Fastest inference, basic tasks', icon: '\u{1F43E}' },
      { id: 'small', label: 'Small (3-7B)', desc: 'Best quality/speed balance', icon: '\u2696\uFE0F' },
      { id: 'medium', label: 'Medium (7-13B)', desc: 'Strong reasoning, more VRAM', icon: '\u{1F4AA}' },
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
          body: JSON.stringify({
            primary_goal: answers.primary_goal,
            data_sources: answers.data_sources || [],
            data_freshness: answers.data_freshness,
            hardware: answers.hardware,
            timeline: answers.timeline,
            accuracy: answers.accuracy,
            model_size: answers.model_size,
          }),
        })
        const data = await resp.json()
        setResult(data)
      } catch {
        setResult({
          training_modes: ['qlora'],
          base_model: 'Qwen/Qwen2.5-7B-Instruct',
          deploy_targets: ['gguf', 'ollama'],
        })
      }
      setLoading(false)
    }
  }

  if (result) {
    return (
      <div className="max-w-3xl mx-auto p-8">
        <div className="text-accent text-xs uppercase tracking-widest mb-2">Analysis Complete</div>
        <h1 className="text-3xl font-bold mb-2">Recommended Strategy</h1>
        <p className="text-gray-400 mb-8">Based on your {Object.keys(answers).length} selections.</p>

        <div className="bg-surface border border-border rounded-xl p-6 mb-4">
          <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Training Modes</h2>
          <div className="flex gap-3 flex-wrap">
            {result.training_modes.map(mode => (
              <span key={mode} className="px-4 py-2 bg-accent/10 border border-accent/30 rounded-lg text-accent font-bold uppercase text-sm">
                {mode}
              </span>
            ))}
          </div>
        </div>

        <div className="bg-surface border border-border rounded-xl p-6 mb-4">
          <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-2">Base Model</h2>
          <p className="text-accent text-lg font-bold">{result.base_model}</p>
        </div>

        <div className="bg-surface border border-border rounded-xl p-6 mb-4">
          <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Deploy Targets</h2>
          <div className="flex gap-3">
            {result.deploy_targets.map(t => (
              <span key={t} className="px-4 py-2 bg-green/10 border border-green/30 rounded-lg text-green font-bold uppercase text-sm">
                {t}
              </span>
            ))}
          </div>
        </div>

        <button onClick={() => { setResult(null); setStep(0); setAnswers({}) }} className="mt-4 px-6 py-3 bg-green text-black rounded-lg font-bold uppercase text-sm">
          New Analysis &rarr;
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto p-8">
      {/* Progress */}
      <div className="flex gap-1.5 mb-12">
        {QUESTIONS.map((_, i) => (
          <div key={i} className={`h-1 flex-1 rounded ${i < step ? 'bg-accent' : i === step ? 'bg-accent/40' : 'bg-border'}`} />
        ))}
      </div>

      {/* Question */}
      <div className="text-xs text-gray-400 uppercase tracking-widest mb-2">
        Question {step + 1} of {QUESTIONS.length}
      </div>
      <h1 className="text-2xl font-bold mb-2">{q.title}</h1>
      <p className="text-sm text-gray-400 mb-6">{q.subtitle}</p>
      {isMulti && <div className="text-xs text-gray-500 border border-border rounded px-3 py-1 inline-block mb-4 uppercase">Select all that apply</div>}

      {/* Options */}
      <div className="grid grid-cols-2 gap-3 mb-8">
        {q.options.map(opt => (
          <button
            key={opt.id}
            onClick={() => handleSelect(opt.id)}
            className={`text-left p-4 rounded-xl border transition-all ${isSelected(opt.id) ? 'bg-accent/10 border-accent shadow-lg shadow-accent/10' : 'bg-surface border-border hover:bg-surface-hover hover:border-border-active'}`}
          >
            <div className="flex gap-3">
              <span className="text-xl">{opt.icon}</span>
              <div>
                <div className={`text-xs font-bold uppercase tracking-wide ${isSelected(opt.id) ? 'text-accent' : 'text-gray-400'}`}>{opt.label}</div>
                <div className="text-xs text-gray-500 mt-1">{opt.desc}</div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => setStep(Math.max(0, step - 1))}
          disabled={step === 0}
          className="px-5 py-2 border border-border text-gray-400 rounded-lg text-sm uppercase disabled:opacity-30"
        >
          &larr; Back
        </button>
        <button
          onClick={handleNext}
          disabled={!isAnswered || loading}
          className="px-5 py-2 bg-accent text-white rounded-lg font-bold text-sm uppercase disabled:bg-border disabled:text-gray-600 shadow-lg shadow-accent/20"
        >
          {loading ? 'Analyzing...' : step === QUESTIONS.length - 1 ? 'Analyze \u2192' : 'Next \u2192'}
        </button>
      </div>
    </div>
  )
}
