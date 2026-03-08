import { Badge } from '@/components/ui/badge'

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-success/20 text-success border-success/30',
  B: 'bg-primary/20 text-primary border-primary/30',
  C: 'bg-warning/20 text-warning border-warning/30',
  D: 'bg-danger/20 text-danger border-danger/30',
  F: 'bg-danger/20 text-danger border-danger/30',
}

interface GradeBadgeProps {
  grade: string
  size?: 'sm' | 'lg'
}

export function GradeBadge({ grade, size = 'sm' }: GradeBadgeProps) {
  const colors = GRADE_COLORS[grade] || GRADE_COLORS.F
  if (size === 'lg') {
    return (
      <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl text-3xl font-bold border ${colors}`}>
        {grade}
      </div>
    )
  }
  return (
    <Badge variant="outline" className={`${colors} font-bold`}>
      {grade}
    </Badge>
  )
}
