// Response shapes the pages read from the backend; contract tests check them against the live API.
// No React or `@/` imports: tsconfig.node type-checks this file through the tests.
export type Health = { status: 'ok' }

export type SensorName = 'heart_rate' | 'temperature' | 'humidity' | 'motion' | 'sound'
export type PartName = 'duration' | 'restlessness' | 'heart_rate' | 'environment'
export type ScorePart = { name: PartName; points: number; max: number; detail: string }
export type Score = { total: number; parts: ScorePart[]; excluded: PartName[] }
export type Session = {
  id: number
  started_at: string
  ended_at: string | null
  auto_closed: boolean
  score: Score | null
  simulated: boolean
}
export type Gap = { sensor: SensorName; start: string; end: string }
export type Baseline = { total: number; parts: { name: PartName; points: number }[]; sessions_used: number }
export type SessionDetail = Session & { gaps: Gap[] | null; baseline: Baseline | null; baseline_reason: string | null }
export type Reading = { sensor: SensorName; value: number; recorded_at: string; simulated: boolean }
export type ErrorBody = { error: string }

export type ApiError = Error & { status: number }

// Throws the backend's own error message so pages can show it as is.
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  const body = await res.json().catch(() => null)
  if (!res.ok) throw Object.assign(new Error((body as ErrorBody | null)?.error ?? `${res.status} ${res.statusText}`), { status: res.status })
  return body as T
}
