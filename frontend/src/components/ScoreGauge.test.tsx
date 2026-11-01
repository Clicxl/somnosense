import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ScoreGauge } from '@/components/ScoreGauge'

const html = (p: Partial<Parameters<typeof ScoreGauge>[0]>) =>
  renderToStaticMarkup(<ScoreGauge score={null} baseline={null} baselineReason={null} {...p} />)
// the closing quote keeps stroke-muted from matching stroke-muted-foreground
const path = (h: string, cls: string) => h.match(new RegExp(`<path[^>]*class="${cls}"[^>]*>`))?.[0]
const b = (total: number) => ({ total, parts: [], sessions_used: 7 })

describe('ScoreGauge', () => {
  it('fills the score arc and the Baseline arc in proportion (D1, D2)', () => {
    const h = html({ score: 50, baseline: b(75) })
    expect(path(h, 'stroke-chart-1')).toContain('pathLength="100"')
    expect(path(h, 'stroke-chart-1')).toContain('stroke-dasharray="50 100"')
    expect(path(h, 'stroke-muted-foreground')).toContain('pathLength="100"')
    expect(path(h, 'stroke-muted-foreground')).toContain('stroke-dasharray="75 100"')
    expect(h).toContain('>50</text>')
    expect(h).toContain('>Baseline 75</text>')
    expect(h).toContain('role="img"')
    expect(h).toContain('aria-label="Sleep Score 50 of 100, Baseline 75"')
    expect(h).toContain('from the last 7 Sleep Sessions · −25 against it')
  })

  it('has no Baseline arc and shows the reason without a Baseline (D3)', () => {
    const reason = 'Baseline still building: 2 of 3 past Sleep Sessions'
    const h = html({ score: 50, baselineReason: reason })
    expect(path(h, 'stroke-muted-foreground')).toBeUndefined()
    expect(h).not.toMatch(/>Baseline \d/)
    expect(h).toContain(reason)
    expect(h).toContain('aria-label="Sleep Score 50 of 100"')
  })

  it('shows an empty track and a dash with no score, keeping the Baseline (D4)', () => {
    const h = html({ score: null, baseline: b(71) })
    expect(path(h, 'stroke-chart-1')).toBeUndefined()
    // no Baseline, so the only track is the outer one
    expect(path(html({}), 'stroke-border dark:stroke-muted')).toContain('stroke-width="12"')
    expect(h).toContain('>—</text>')
    expect(path(h, 'stroke-muted-foreground')).toContain('stroke-dasharray="71 100"')
    expect(h).toContain('>Baseline 71</text>')
    expect(h).toContain('aria-label="Sleep Score not available, Baseline 71"')
    expect(h).not.toContain('against it')
  })

  it('uses the same colour whatever the score (D5)', () => {
    for (const score of [30, 60, 90]) expect(path(html({ score }), 'stroke-chart-1')).toContain(`stroke-dasharray="${score} 100"`)
  })
})
