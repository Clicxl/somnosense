import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts'
import { Stamp } from '@/components/sheet'
import { Badge } from '@/components/ui/badge'
import { ChartContainer } from '@/components/ui/chart'
import { api, type Session, type SessionDetail } from '@/lib/api'
import { between, day } from '@/lib/sleep'
import { useApi } from '@/lib/use-api'

const config = { score: { label: 'Sleep Score', color: 'var(--chart-1)' }, baseline: { label: 'Baseline', color: 'var(--chart-2)' } }

function Key({ dashed, children }: { dashed?: boolean; children: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <svg width="20" height="6" aria-hidden>
        <line x1="0" y1="3" x2="20" y2="3" stroke={dashed ? 'var(--chart-2)' : 'var(--chart-1)'} strokeWidth="2" strokeDasharray={dashed ? '4 3' : undefined} />
      </svg>
      {children}
    </span>
  )
}

export default function History() {
  const sessions = useApi<Session[]>('/api/sessions')
  const list = sessions.data
  const [details, setDetails] = useState<SessionDetail[]>()
  const [detailError, setDetailError] = useState<string>()

  // shortcut: one detail fetch per finished Sleep Session for its Baseline; put the Baseline in the list if History grows past ~50
  useEffect(() => {
    if (!list) return
    let live = true
    Promise.all(list.filter((s) => s.ended_at).map((s) => api<SessionDetail>(`/api/sessions/${s.id}`))).then(
      (d) => live && setDetails(d),
      (e: Error) => live && setDetailError(e.message),
    )
    return () => {
      live = false
    }
  }, [list])

  if (sessions.error)
    return (
      <section className="px-5 py-6">
        <h1 className="font-heading text-3xl font-semibold">Cannot load History</h1>
        <p role="alert" className="mt-2 text-destructive">
          {sessions.error.message}
        </p>
      </section>
    )
  if (!list) return <p className="px-5 py-6 text-muted-foreground">Loading History…</p>
  if (!list.length)
    return (
      <section className="px-5 py-6">
        <h1 className="font-heading text-3xl font-semibold">No Sleep Sessions yet</h1>
        <p className="mt-2 text-muted-foreground">
          Start one from the{' '}
          <Link to="/" className="text-foreground underline underline-offset-4">
            Live View
          </Link>{' '}
          tonight, or backfill nights with the Simulator.
        </p>
      </section>
    )

  const baselineOf = (id: number) => details?.find((d) => d.id === id)?.baseline?.total
  // Sleep Scores come with the list; Baselines fill in when the slower detail fetches land
  const points = list
    .filter((s) => s.ended_at)
    .toReversed()
    .map((s) => ({ day: day(s.started_at), score: s.score?.total ?? null, baseline: baselineOf(s.id) ?? null }))
  const building =details && !details.some((d) => d.baseline) ? details[0]?.baseline_reason : undefined

  return (
    <>
      <section className="relative border-b px-5 py-6">
        <h1 className="font-heading text-3xl font-semibold">Sleep Score over time</h1>
        {/* in flow on phones, where the heading is too wide to share the row */}
        {list.some((s) => s.simulated) && <Stamp className="mt-3 sm:absolute sm:top-5 sm:right-5 sm:mt-0" />}
        <div className="mt-4 flex gap-5 text-xs text-muted-foreground">
          <Key>Sleep Score</Key>
          <Key dashed>Baseline</Key>
        </div>
        {detailError ? (
          <p role="alert" className="mt-3 text-sm text-destructive">
            Cannot load the Baselines: {detailError}
          </p>
        ) : (
          <ChartContainer config={config} className="mt-3 aspect-auto h-56 w-full" aria-hidden>
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="day" tickLine={false} axisLine={false} minTickGap={16} />
              <YAxis width={28} domain={[0, 100]} ticks={[0, 50, 100]} tickLine={false} axisLine={false} />
              <Line dataKey="score" stroke="var(--color-score)" strokeWidth={2} dot={{ r: 3, fill: 'var(--color-score)' }} isAnimationActive={false} />
              <Line dataKey="baseline" stroke="var(--color-baseline)" strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
            </LineChart>
          </ChartContainer>
        )}
        {(building || !details) && !detailError && (
          <p className="mt-2 text-sm text-muted-foreground">{building ?? 'Loading Baselines…'}</p>
        )}
      </section>

      <table className="w-full border-collapse">
        <caption className="sr-only">Sleep Sessions, newest first</caption>
        <thead>
          <tr className="border-b border-foreground text-left text-[11px] tracking-[.06em] text-muted-foreground uppercase">
            <th className="px-2 pt-3 pb-2 font-medium first:pl-5 last:pr-5">Date</th>
            <th className="px-2 pt-3 pb-2 font-medium first:pl-5 last:pr-5">Duration</th>
            <th className="px-2 pt-3 pb-2 text-right font-medium first:pl-5 last:pr-5">Sleep Score</th>
          </tr>
        </thead>
        <tbody>
          {list.map((s) => (
            <tr key={s.id} className="border-b">
              <th scope="row" className="px-2 py-4 text-left font-medium first:pl-5 last:pr-5">
                <Link to={s.ended_at ? `/sessions/${s.id}` : '/'} className="underline underline-offset-4">
                  {day(s.started_at)}
                </Link>
                {s.auto_closed && (
                  <Badge variant="outline" className="ml-2">
                    Auto-closed
                  </Badge>
                )}
              </th>
              <td className="px-2 py-4 text-sm whitespace-nowrap text-muted-foreground first:pl-5 last:pr-5">
                {s.ended_at ? between(s.started_at, s.ended_at) : 'running'}
              </td>
              <td className="px-2 py-4 text-right whitespace-nowrap first:pl-5 last:pr-5">
                <span className="font-heading text-2xl font-semibold">{s.score?.total ?? '—'}</span>
                {baselineOf(s.id) !== undefined && <span className="block text-xs text-muted-foreground">Baseline {baselineOf(s.id)}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
