// One file so these run in order: test 5 starts a Sleep Session the earlier tests must not see.
import { expect, test } from 'vitest'
import type { ErrorBody, Reading, SensorName, Session, SessionDetail } from '../../src/lib/api.ts'
import { BASE_URL } from './globalSetup.ts'

const ISO = expect.stringMatching(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/)
const get = async (path: string) => {
  const res = await fetch(BASE_URL + path)
  return { status: res.status, body: await res.json() }
}
const post = (path: string, body?: unknown) =>
  fetch(BASE_URL + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) })
const part = { name: expect.any(String), points: expect.any(Number), max: expect.any(Number), detail: expect.any(String) }
const session = {
  id: expect.any(Number),
  started_at: ISO,
  ended_at: ISO,
  auto_closed: false,
  score: { total: expect.any(Number), parts: [part, part, part, part], excluded: [] },
  simulated: true,
} satisfies Session
const ago = (min: number) => new Date(Date.now() - min * 60_000).toISOString().replace(/\.\d+Z$/, 'Z')

test('GET /api/sessions/current is 404 with an error when none runs', async () => {
  const { status, body } = await get('/api/sessions/current')
  expect(status).toBe(404)
  expect(body).toStrictEqual({ error: 'no Sleep Session is running' } satisfies ErrorBody)
})

test('GET /api/sessions lists the 3 seeded Sleep Sessions newest first', async () => {
  const { status, body } = await get('/api/sessions')
  expect(status).toBe(200)
  expect(body).toStrictEqual([session, session, session])
  const starts = (body as Session[]).map((s) => s.started_at)
  expect(starts).toStrictEqual([...starts].sort().reverse())
})

test('GET /api/sessions/<oldest> has gaps, null baseline and a reason', async () => {
  const oldest = (await get('/api/sessions')).body.at(-1) as Session
  const { body } = await get(`/api/sessions/${oldest.id}`)
  expect(body).toStrictEqual({
    ...session,
    gaps: [],
    baseline: null,
    baseline_reason: 'Baseline still building: 0 of 3 past Sleep Sessions',
  } satisfies SessionDetail)
})

test('GET /api/sessions/<id>/readings?sensor=heart_rate is ordered and simulated', async () => {
  const [newest] = (await get('/api/sessions')).body as Session[]
  const { status, body } = await get(`/api/sessions/${newest.id}/readings?sensor=heart_rate`)
  expect(status).toBe(200)
  expect(body).toHaveLength(960) // 8 h of 30 s steps
  for (const r of body) {
    expect(r).toStrictEqual({ sensor: 'heart_rate', value: expect.any(Number), recorded_at: ISO, simulated: true } satisfies Reading)
  }
  const times = (body as Reading[]).map((r) => r.recorded_at)
  expect(times).toStrictEqual([...times].sort())
})

test('a running Sleep Session has null gaps; once stopped it has Data Gaps and a Baseline', async () => {
  const started = await post('/api/sessions', { started_at: ago(10) })
  expect(started.status).toBe(201)
  const { id } = (await started.json()) as Session
  const sent = await post('/api/readings', [{ sensor: 'heart_rate', value: 60, recorded_at: ago(9), simulated: true }])
  expect(await sent.json()).toStrictEqual({ accepted: 1, rejected: [] })

  expect((await get('/api/sessions/current')).status).toBe(200)
  const live = (await get(`/api/sessions/${id}`)).body as SessionDetail
  expect(live.ended_at).toBeNull()
  expect(live.gaps).toBeNull()

  expect((await post(`/api/sessions/${id}/stop`)).status).toBe(200)
  const { body } = await get(`/api/sessions/${id}`)
  const gap = (sensor: SensorName) => ({ sensor, start: ISO, end: ISO })
  expect(body).toStrictEqual({
    id,
    started_at: ISO,
    ended_at: ISO,
    auto_closed: false,
    score: null, // 9 of 10 min is a Data Gap, so no Sensor is usable
    simulated: true,
    gaps: [gap('heart_rate'), gap('temperature'), gap('humidity'), gap('motion')],
    baseline: { total: expect.any(Number), parts: Array(4).fill({ name: expect.any(String), points: expect.any(Number) }), sessions_used: 3 },
    baseline_reason: null,
  } satisfies SessionDetail)
})

test('GET /api/sessions/999 is 404 with an error', async () => {
  const { status, body } = await get('/api/sessions/999')
  expect(status).toBe(404)
  expect(body).toStrictEqual({ error: 'no such Sleep Session' } satisfies ErrorBody)
})
