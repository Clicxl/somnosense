import { Link, useParams } from 'react-router'
import { CartesianGrid, Line, LineChart, ReferenceArea, XAxis, YAxis } from 'recharts'
import { ScoreGauge } from '@/components/ScoreGauge'
import { Label, Stamp } from '@/components/sheet'
import { Badge } from '@/components/ui/badge'
import { ChartContainer } from '@/components/ui/chart'
import type { Gap, Reading, SessionDetail } from '@/lib/api'
import { between, clock, day, PART_LABELS, PART_NAMES, sensorsIn } from '@/lib/sleep'
import { useApi } from '@/lib/use-api'

// On the local hour, about four per chart, so labels never crowd.
function hourTicks(from: number, to: number) {
  const step = Math.max(1, Math.round((to - from) / 3600e3 / 4)) * 3600e3
  const t = new Date(from)
  t.setMinutes(0, 0, 0)
  const ticks = []
  for (let x = t.getTime(); x <= to; x += step) if (x >= from) ticks.push(x)
  return ticks
}

function SensorChart({ label, unit, rows, gaps, from, to }: {
  label: string
  unit: string
  rows: Reading[]
  gaps: Gap[]
  from: number
  to: number
}) {
  const points: { t: number; v: number | null }[] = rows.map((r) => ({ t: Date.parse(r.recorded_at), v: r.value }))
  // a null at each Data Gap's midpoint breaks the line there instead of drawing across it
  for (const g of gaps) points.push({ t: (Date.parse(g.start) + Date.parse(g.end)) / 2, v: null })
  points.sort((a, b) => a.t - b.t)

  return (
    <figure className="border-b px-5 py-5 md:odd:border-r">
      <figcaption className="flex items-baseline justify-between gap-4">
        <span className="font-medium">{label}</span>
        <Label>{unit}</Label>
      </figcaption>
      {/* Recharts draws no Data Gap shading on a chart without data, so a silent Sensor gets a plain shaded box */}
      {!rows.length ? (
        <p className="mt-3 flex h-36 items-center justify-center bg-destructive/[.08] text-sm text-destructive">No Readings in this Sleep Session</p>
      ) : (
        <ChartContainer config={{ v: { color: 'var(--chart-1)' } }} className="mt-3 aspect-auto h-36 w-full" aria-hidden>
          <LineChart data={points} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="t" type="number" domain={[from, to]} ticks={hourTicks(from, to)} tickFormatter={clock} tickLine={false} axisLine={false} />
            <YAxis width={32} domain={['auto', 'auto']} tickCount={3} tickLine={false} axisLine={false} />
            {gaps.map((g) => (
              <ReferenceArea key={g.start} x1={Date.parse(g.start)} x2={Date.parse(g.end)} fill="var(--destructive)" fillOpacity={0.08} />
            ))}
            <Line dataKey="v" stroke="var(--color-v)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          </LineChart>
        </ChartContainer>
      )}
      <ul className="mt-2 space-y-0.5 text-xs text-destructive">
        {gaps.map((g) => (
          <li key={g.start}>
            Data Gap {clock(g.start)}–{clock(g.end)}
          </li>
        ))}
      </ul>
    </figure>
  )
}

function Notice({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="px-5 py-6">
      <h1 className="font-heading text-3xl font-semibold">{title}</h1>
      <p className="mt-2 text-muted-foreground">{children}</p>
    </section>
  )
}

export default function MorningReport() {
  const { id } = useParams()
  const detail = useApi<SessionDetail>(`/api/sessions/${id}`)
  const readings = useApi<Reading[]>(`/api/sessions/${id}/readings`)
  const s = detail.data
  const error = detail.error ?? readings.error

  if (detail.error?.status === 404)
    return (
      <Notice title="No such Sleep Session">
        <Link to="/history" className="text-foreground underline underline-offset-4">
          Pick one from History
        </Link>
        .
      </Notice>
    )
  if (error) return <Notice title="Cannot load the Morning Report">{error.message}</Notice>
  if (!s || !readings.data) return <Notice title="Loading the Morning Report…">Fetching the Sleep Session and its Readings.</Notice>
  if (!s.ended_at)
    return (
      <Notice title="This Sleep Session is still running">
        The Morning Report is ready once it ends. Follow it on the{' '}
        <Link to="/" className="text-foreground underline underline-offset-4">
          Live View
        </Link>
        .
      </Notice>
    )

  const score = s.score
  const parts = score && PART_NAMES.map((name) => ({ name, got: score.parts.find((p) => p.name === name) }))
  const raw = score?.parts.reduce((a, p) => a + p.points, 0) ?? 0
  const rawMax = score?.parts.reduce((a, p) => a + p.max, 0) ?? 0
  const base = (name: string) => s.baseline?.parts.find((p) => p.name === name)?.points

  return (
    <>
      <section className="relative border-b px-5 py-6">
        <h1 className="font-heading text-3xl font-semibold">{day(s.started_at)}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {clock(s.started_at)}–{clock(s.ended_at)} · {between(s.started_at, s.ended_at)}
        </p>
        {s.auto_closed && (
          <Badge variant="outline" className="mt-2" title="Nobody pressed Woke up; it ended 14 hours after it was opened">
            Auto-closed Session
          </Badge>
        )}
        {s.simulated && <Stamp className="absolute top-5 right-5" />}

        <ScoreGauge className="mt-5" score={score?.total ?? null} baseline={s.baseline} baselineReason={s.baseline_reason} />
        {!score && <p className="mt-2 text-sm">No Sensor had Readings for at least half of this Sleep Session, so it is not scored.</p>}
      </section>

      {parts && score && (
        <table className="w-full border-collapse">
          <caption className="sr-only">How the Sleep Score is made</caption>
          <thead>
            <tr className="border-b border-foreground text-left text-[11px] tracking-[.06em] text-muted-foreground uppercase">
              <th className="px-2 pt-3 pb-2 first:pl-5 last:pr-5 font-medium">Part</th>
              <th className="px-2 pt-3 pb-2 first:pl-5 last:pr-5 font-medium">Remark</th>
              <th className="px-2 pt-3 pb-2 first:pl-5 last:pr-5 text-right font-medium">Points</th>
            </tr>
          </thead>
          <tbody>
            {parts.map(({ name, got }) => (
              <tr key={name} className="border-b align-top">
                <th scope="row" className="px-2 py-4 first:pl-5 last:pr-5 text-left font-medium">
                  {PART_LABELS[name]}
                </th>
                <td className="px-2 py-4 first:pl-5 last:pr-5 text-sm text-muted-foreground">{got ? got.detail : 'Not enough data: left out of the Sleep Score'}</td>
                <td className="px-2 py-4 first:pl-5 last:pr-5 text-right whitespace-nowrap">
                  <span className="font-heading text-2xl font-semibold">{got ? got.points : '—'}</span>
                  {got && <span className="text-xs text-muted-foreground"> / {got.max}</span>}
                  {got && base(name) !== undefined && <span className="block text-xs text-muted-foreground">Baseline {base(name)}</span>}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-b-2 border-foreground">
              <th scope="row" className="px-2 py-4 first:pl-5 last:pr-5 text-left font-semibold">
                Total
              </th>
              <td className="px-2 py-4 first:pl-5 last:pr-5 text-sm text-muted-foreground">
                {score.excluded.length
                  ? `${Math.round(raw * 10) / 10} of ${rawMax}, scaled to 100 because ${score.excluded.map((n) => PART_LABELS[n]).join(' and ')} had too little data`
                  : `${Math.round(raw * 10) / 10} of ${rawMax}, rounded`}
              </td>
              <td className="px-2 py-4 first:pl-5 last:pr-5 text-right font-heading text-2xl font-semibold">{score.total}</td>
            </tr>
          </tfoot>
        </table>
      )}

      <h2 className="px-5 pt-8 pb-2 text-[11px] tracking-[.06em] text-muted-foreground uppercase">Readings behind the parts</h2>
      <div className="grid border-t border-foreground md:grid-cols-2">
        {sensorsIn(readings.data).map(({ name, label, unit, part }) => (
          <SensorChart
            key={name}
            label={part ? `${label} · ${PART_LABELS[part]} part` : `${label} · not in the Sleep Score`}
            unit={unit}
            rows={readings.data!.filter((r) => r.sensor === name)}
            gaps={s.gaps?.filter((g) => g.sensor === name) ?? []}
            from={Date.parse(s.started_at)}
            to={Date.parse(s.ended_at!)}
          />
        ))}
      </div>
    </>
  )
}
