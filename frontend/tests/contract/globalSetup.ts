import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

export const BASE_URL = 'http://127.0.0.1:5055'

const root = resolve(import.meta.dirname, '../../..')
const venvPython = join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')

// no stack: vitest 5 crashes symbolicating errors thrown from globalSetup and hides the message
const fail = (msg: string) => Object.assign(new Error(msg), { stack: msg })

// timeout so a server that accepts but never replies can't hang setup past the deadline
const answers = () =>
  fetch(`${BASE_URL}/api/health`, { signal: AbortSignal.timeout(1000) }).then(() => true, () => false)

export default async function setup() {
  if (await answers()) throw fail('port 5055 already in use; stop the other server first')

  const python = process.env.PYTHON || (existsSync(venvPython) ? venvPython : 'python')
  const dir = mkdtempSync(join(tmpdir(), 'somnosense-'))
  const child = spawn(python, ['-m', 'flask', '--app', 'backend', 'run', '--port', '5055', '--no-reload'], {
    cwd: root,
    env: { ...process.env, SOMNOSENSE_DB: join(dir, 'test.db') },
    stdio: ['ignore', 'ignore', 'pipe'],
  })
  let stderr = ''
  let exited = false
  child.stderr.on('data', (d) => (stderr += d))
  child.on('exit', () => (exited = true))
  child.on('error', (e) => ((stderr += String(e)), (exited = true)))

  const stop = () => {
    // taskkill /T because child.kill() on Windows can leave grandchildren holding the port
    if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'])
    else child.kill()
    rmSync(dir, { recursive: true, force: true, maxRetries: 5 })
  }

  const deadline = Date.now() + 15_000
  while (!(await answers())) {
    if (exited || Date.now() > deadline) {
      stop()
      throw fail(`Flask did not start (${exited ? 'exited' : 'timed out'}):\n${stderr}`)
    }
    await new Promise((r) => setTimeout(r, 200))
  }

  // 3 finished Sleep Sessions of Simulated Readings ending this morning, so a new one has a Baseline
  const start = new Date(Date.now() - 3 * 864e5).toLocaleDateString('en-CA')
  const sim = spawnSync(
    python,
    [join(root, 'simulator', 'simulator.py'), '--start', start, '--nights', '3', '--speed', '0', '--seed', '1', '--api', BASE_URL],
    { cwd: root, encoding: 'utf8' },
  )
  if (sim.status !== 0) {
    stop()
    throw fail(`Simulator could not seed Sleep Sessions:\n${sim.stderr || sim.error}`)
  }
  return stop
}
