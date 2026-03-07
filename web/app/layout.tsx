import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Adaptron - LLM Fine-tuning Framework',
  description: 'End-to-end LLM fine-tuning made simple',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg text-white min-h-screen font-mono">{children}</body>
    </html>
  )
}
