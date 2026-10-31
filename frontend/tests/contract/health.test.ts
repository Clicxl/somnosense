import { expect, test } from 'vitest'
import type { Health } from '../../src/lib/api.ts'
import { BASE_URL } from './globalSetup.ts'

test('GET /api/health returns 200 JSON', async () => {
  const res = await fetch(`${BASE_URL}/api/health`)
  expect(res.status).toBe(200)
  expect(res.headers.get('content-type')).toContain('application/json')
})

test('GET /api/health has exactly the Health fields', async () => {
  const body = await (await fetch(`${BASE_URL}/api/health`)).json()
  // strict: a renamed, missing or extra backend field fails here
  expect(body).toStrictEqual({ status: 'ok' } satisfies Health)
})
