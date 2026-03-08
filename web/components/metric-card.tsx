import { Card, CardContent } from '@/components/ui/card'
import { type LucideIcon } from 'lucide-react'

interface MetricCardProps {
  icon: LucideIcon
  label: string
  value: string | number
  subtitle?: string
  className?: string
}

export function MetricCard({ icon: Icon, label, value, subtitle, className }: MetricCardProps) {
  return (
    <Card className={`bg-white/5 border-white/10 backdrop-blur-sm ${className || ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{label}</p>
            <p className="text-xl font-bold mt-0.5">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
