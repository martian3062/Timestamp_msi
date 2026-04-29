import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'MSI Prediction Platform',
  description: 'Pathology AI Research Dashboard',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground flex flex-col antialiased">
        <header className="border-b border-border bg-card px-6 py-4 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded flex items-center justify-center font-bold text-primary-foreground">
              M
            </div>
            <span className="font-semibold text-lg tracking-tight">MSI Platform</span>
          </div>
          <nav className="flex gap-6 text-sm font-medium text-muted-foreground">
            <a href="/" className="hover:text-foreground transition-colors">Overview</a>
            <a href="/datasets" className="hover:text-foreground transition-colors">Datasets</a>
            <a href="/training" className="hover:text-foreground transition-colors">Training</a>
            <a href="/experiments" className="hover:text-foreground transition-colors">Experiments</a>
            <a href="/predictions" className="hover:text-foreground transition-colors">Inference</a>
            <a href="http://34.55.157.128:6080/vnc.html" target="_blank" rel="noopener noreferrer" className="text-secondary-foreground font-semibold hover:text-white transition-colors bg-secondary/80 px-2 py-0.5 rounded ml-2">Studio ↗</a>
          </nav>
        </header>
        <main className="flex-1 flex overflow-hidden">
          {children}
        </main>
      </body>
    </html>
  )
}
