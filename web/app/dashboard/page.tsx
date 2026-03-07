'use client'

export default function DashboardPage() {
  return (
    <div className="max-w-5xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
      <p className="text-gray-400 mb-8">Monitor your fine-tuning pipelines.</p>

      <div className="bg-surface border border-border rounded-xl p-6">
        <h2 className="text-xs text-gray-400 uppercase tracking-wider mb-4">Active Pipelines</h2>
        <p className="text-gray-500 text-sm">No active pipelines. Start one from the <a href="/wizard" className="text-accent hover:underline">wizard</a>.</p>
      </div>
    </div>
  )
}
