import { Label } from '@/components/sheet'
import type { Baseline } from '@/lib/api'
import { cn } from '@/lib/utils'

const arc = (r: number) => `M ${100 - r} 100 A ${r} ${r} 0 0 1 ${100 + r} 100`

export function ScoreGauge({ score, baseline, baselineReason, className }: {
  score: number | null
  baseline: Baseline | null
  baselineReason: string | null
  className?: string
}) {
  const vs = score !== null && baseline ? Math.round(score - baseline.total) : null
  const label = `${score === null ? 'Sleep Score not available' : `Sleep Score ${score} of 100`}${baseline ? `, Baseline ${baseline.total}` : ''}`
  return (
    <div className={cn('flex items-end gap-5', className)}>
      <svg viewBox="0 0 200 104" role="img" aria-label={label} fill="none" className="w-40 shrink-0">
        <path d={arc(90)} strokeWidth={12} className="stroke-border dark:stroke-muted" />
        {score !== null && <path d={arc(90)} strokeWidth={12} pathLength={100} strokeDasharray={`${score} 100`} className="stroke-chart-1" />}
        {baseline && (
          <>
            <path d={arc(72)} strokeWidth={5} className="stroke-border dark:stroke-muted" />
            <path d={arc(72)} strokeWidth={5} pathLength={100} strokeDasharray={`${baseline.total} 100`} className="stroke-muted-foreground" />
          </>
        )}
        <text x={100} y={80} textAnchor="middle" className="fill-foreground font-heading text-[44px] font-semibold">
          {score ?? '—'}
        </text>
        {baseline && (
          <text x={100} y={100} textAnchor="middle" className="fill-muted-foreground text-[15px]">
            {`Baseline ${baseline.total}`}
          </text>
        )}
      </svg>
      <div className="min-w-0 pb-1">
        <Label>Sleep Score</Label>
        <p className="mt-1 text-sm text-muted-foreground">
          {baseline
            ? `Baseline from the last ${baseline.sessions_used} Sleep Sessions${vs === null ? '' : ` · ${vs >= 0 ? '+' : '−'}${Math.abs(vs)} against it`}`
            : baselineReason}
        </p>
      </div>
    </div>
  )
}
