import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { Line, LineChart, XAxis, YAxis } from 'recharts'
import { Label, Stamp } from '@/components/sheet'
import { Button } from '@/components/ui/button'
import { ChartContainer } from '@/components/ui/chart'
import { api, type Reading, type SensorName, type Session } from '@/lib/api'
import { between, clock, SENSORS } from '@/lib/sleep'
import { useApi } from '@/lib/use-api'
import { cn } from '@/lib/utils'

const POLL_MS = 5000 // issue #18: poll, no WebSockets
const STALE_MS = 5 * 60_000 // same 5 min the backend uses for a Data Gap
const TREND_MS = 30 * 60_000

// What a Sleeper would want to know about a Sensor's latest Reading; `warn` prints it in red.
function remark(sensor: SensorName, rows: Reading[], newest: number): { text: string; warn?: boolean } {
  const last = rows.at(-1)
  if (!last) return { text: 'no Readings yet', warn: true }
  const at = Date.parse(last.recorded_at)
  if (newest - at > STALE_MS) return { text: `no Reading since ${clock(at)}`, warn: true }
  const v = last.value
  switch (sensor) {
    case 'temperature':
      return 13 <= v && v <= 23 ? { text: 'in range 13–23 °C' } : { text: 'outside 13–23 °C', warn: true }
    case 'humidity':
      return 40 <= v && v <= 60 ? { text: 'in range 40–60%' } : { text: 'outside 40–60%', warn: true }
    case 'motion':
      return { text: v > 0 ? 'moving' : 'still' }
    default: {
      const t0 = Date.parse(rows[0].recorded_at)
      const first = rows.filter((r) => Date.parse(r.recorded_at) - t0 < TREND_MS)
      const awake = first.reduce((a, r) => a + r.value, 0) / first.length
      const drop = Math.round(((awake - v) / awake) * 100)
      return { text: drop >= 0 ? `${drop}% below first 30 min` : `${-drop}% above first 30 min` }
    }
  }
}

function Trend({ rows }: { rows: Reading[] }) {
  const end = Date.parse(rows.at(-1)!.recorded_at)
  const data = rows.map((r) => ({ t: Date.parse(r.recorded_at), v: r.value })).filter((p) => end - p.t <= TREND_MS)
  return (
    <ChartContainer config={{ v: { color: 'var(--chart-1)' } }} className="mt-2 aspect-auto h-8 w-full max-w-40" aria-hidden>
      <LineChart data={data} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
        <XAxis dataKey="t" type="number" domain={[end - TREND_MS, end]} hide />
        <YAxis domain={['dataMin - 1', 'dataMax + 1']} hide />
        <Line dataKey="v" stroke="var(--color-v)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ChartContainer>
  )
}

export default function LiveView() {
  const navigate = useNavigate()
  const current = useApi<Session>('/api/sessions/current', POLL_MS)
  const none = current.error?.status === 404
  const session = none ? null : current.data
  // shortcut: re-downloads every Reading each poll (~300 KB by hour 8); add a since= parameter to the API if that gets slow
  const readings = useApi<Reading[]>(session ? `/api/sessions/${session.id}/readings` : null, POLL_MS)
  const rows = readings.data ?? []

  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState<string>()
  const [watched, setWatched] = useState<number>()
  const [endedElsewhere, setEndedElsewhere] = useState<number>()

  // A Sleep Session that stops running without this page's Woke up ended elsewhere: Simulator, another tab, auto-close.
  // Adjusted during render (React's "store information from previous renders"), not in an effect.
  const runningId = session?.id
  if (runningId !== watched && (runningId !== undefined || none)) {
    if (watched !== undefined) setEndedElsewhere(watched)
    setWatched(runningId)
  }

  async function act() {
    setBusy(true)
    setFailed(undefined)
    try {
      if (session) {
        await api(`/api/sessions/${session.id}/stop`, { method: 'POST' })
        navigate(`/sessions/${session.id}`)
        return
      }
      await api('/api/sessions', { method: 'POST' })
      setEndedElsewhere(undefined)
    } catch (e) {
      setFailed((e as Error).message)
    }
    current.reload()
    setBusy(false)
  }

  const newest = rows.length ? Date.parse(rows.at(-1)!.recorded_at) : undefined
  const pollError = current.error && !none ? current.error.message : readings.error?.message

  return (
    <>
      {endedElsewhere !== undefined && (
        <div role="status" className="mx-5 mt-5 flex flex-wrap items-center gap-x-4 gap-y-2 border-2 border-destructive p-4">
          <p className="grow">This Sleep Session ended outside this page.</p>
          <Link to={`/sessions/${endedElsewhere}`} className="font-medium underline underline-offset-4">
            Open its Morning Report
          </Link>
          <Button variant="ghost" size="sm" onClick={() => setEndedElsewhere(undefined)}>
            Dismiss
          </Button>
        </div>
      )}

      <section className="relative border-b px-5 py-6">
        {session ? (
          <>
            <h1 className="text-xs tracking-[.06em] text-muted-foreground uppercase">
              Sleep Session since {clock(session.started_at)}
            </h1>
            <p className="my-2 font-heading text-5xl leading-none font-semibold">
              {newest ? between(session.started_at, rows.at(-1)!.recorded_at) : '0 h 0 min'}
            </p>
            <Label>{newest ? `Latest Readings ${clock(newest)}` : 'Waiting for the first Readings'}</Label>
            {rows.some((r) => r.simulated) && <Stamp className="absolute top-5 right-5" />}
          </>
        ) : none ? (
          <>
            <h1 className="font-heading text-3xl font-semibold">No Sleep Session running</h1>
            <p className="mt-2 max-w-prose text-muted-foreground">
              Press Going to bed as you lie down. Readings from the Sensors, or the Simulator, show here every few seconds.
            </p>
          </>
        ) : (
          <h1 className="text-muted-foreground">{pollError ? 'Cannot load the Live View' : 'Loading the Live View…'}</h1>
        )}

        <Button className="mt-5 h-12 w-full text-base" disabled={busy || (!session && !none)} onClick={act}>
          {session ? 'Woke up' : 'Going to bed'}
        </Button>
        {(failed || pollError) && (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {failed ?? `Cannot reach the backend: ${pollError}`}
          </p>
        )}
      </section>

      {session && (
        // one tab stop for the whole table, so the keyboard can scroll it
        <div role="region" aria-label="Latest Readings" tabIndex={0} className="focus-visible:outline-2 focus-visible:outline-ring">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-foreground text-left text-[11px] font-medium tracking-[.06em] text-muted-foreground uppercase">
                <th className="px-2 pt-3 pb-2 first:pl-5 last:pr-5 font-medium">Sensor</th>
                <th className="px-2 pt-3 pb-2 first:pl-5 last:pr-5 font-medium">Remark</th>
                <th className="px-2 pt-3 pb-2 first:pl-5 last:pr-5 text-right font-medium">Latest</th>
              </tr>
            </thead>
            <tbody>
              {SENSORS.map(({ name, label, unit }) => {
                const mine = rows.filter((r) => r.sensor === name)
                const last = mine.at(-1)
                const note = remark(name, mine, newest ?? 0)
                return (
                  <tr key={name} className="border-b">
                    <th scope="row" className="px-2 py-4 first:pl-5 last:pr-5 text-left font-medium">
                      {label}
                    </th>
                    <td className="px-2 py-4 first:pl-5 last:pr-5 align-middle">
                      <span className={cn('text-xs', note.warn ? 'text-destructive' : 'text-remark')}>{note.text}</span>
                      {last && <Trend rows={mine} />}
                    </td>
                    <td className="px-2 py-4 first:pl-5 last:pr-5 text-right font-heading text-[28px] font-semibold whitespace-nowrap">
                      {last ? last.value : '—'} <small className="font-sans text-xs font-normal text-muted-foreground">{unit}</small>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
