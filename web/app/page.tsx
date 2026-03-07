import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-8">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 bg-gradient-to-br from-accent to-purple rounded-xl flex items-center justify-center text-2xl shadow-lg shadow-accent/20">
          &#x26A1;
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Adaptron</h1>
          <p className="text-sm text-gray-400 tracking-wide uppercase">LLM Fine-tuning Framework</p>
        </div>
      </div>
      <div className="flex gap-4">
        <Link href="/wizard" className="px-6 py-3 bg-accent text-white rounded-lg font-bold uppercase text-sm tracking-wider hover:opacity-90 shadow-lg shadow-accent/20">
          Start Wizard &rarr;
        </Link>
        <Link href="/dashboard" className="px-6 py-3 border border-border text-gray-400 rounded-lg font-bold uppercase text-sm tracking-wider hover:border-border-active hover:text-white">
          Dashboard
        </Link>
      </div>
    </div>
  )
}
