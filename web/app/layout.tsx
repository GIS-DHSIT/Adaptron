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
