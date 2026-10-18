import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { GatewayEvent } from '@hermes/shared/gateway-events'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { answerText } from '../answer-actions.js'
import { App } from '../app.js'
import type { TurnEntry } from '../model.js'
import { analyzeTable, type ChartKind, type ChartMode, chartSvg, TableCharts, tableSlices } from '../view/table-charts.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const previous = process.env.HERMES_HOME
  const home = mkdtempSync(join(tmpdir(), 'hermes-table-charts-'))
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }
  rmSync(isolated.home, { recursive: true, force: true })
})
const paint = () => new Promise<void>(resolve => setImmediate(resolve))
const table = '| Category | Revenue |\n| --- | ---: |\n| Alpha | 10 |\n| Beta | 25 |'

function controller(mode: ChartMode, plan = vi.fn(async (): Promise<ChartKind> => 'line')) {
  const changed = vi.fn()
  const charts = new TableCharts({ policy: async () => mode, plan }, changed)
  charts.configure(mode)

  return { charts, changed, plan }
}

async function mounted(mode: ChartMode, run: (app: App, send: (type: GatewayEvent['type'], payload?: unknown) => Promise<void>, markdown: () => string[], plans: string[]) => Promise<void>) {
  const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
  const gw = new GatewayClient()
  const plans: string[] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'table_chart.policy') { return { mode } }

    if (method === 'table_chart.plan') {
      plans.push(String((params as { source: string }).source))

      return { kind: 'line' }
    }

    return {}
  })
  const app = new App(tern, gw, 'test')
  app.sid = 's'
  app.tableCharts.session('s')
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = view => { latest = View.from(view); render(view) }

  const markdown = () => {
    const visit = (tree: NonNullable<View['regions'][number]>): string[] => [
      ...(tree.kind === 'md' ? [String(tree.props.text)] : []), ...tree.children.flatMap(visit)
    ]

    return latest?.regions.flatMap(tree => tree ? visit(tree) : []) ?? []
  }

  try {
    app.changed()
    await paint(); await paint()
    await run(app, async (type, payload) => {
      gw.emit('event', { type, session_id: 's', payload } as GatewayEvent)
      await paint(); await paint()
    }, markdown, plans)
  } finally { app.quit(); await running }
}

describe('automatic numeric table charts after artifact projection', () => {
  it.each([
    table.replace('25', 'unknown'), table.replace('| Beta | 25 |', '| Beta |'),
    table.replace('Beta', 'Alpha'), table.replace('Alpha', '2025'),
    table.replace('25', '25%'), table.replace('25', '1,234'),
    table.replace('25', 'Infinity'), table.replace('25', '1e99'),
    table.replace('25', '0').replace('10', '0'), table.replace('Beta', 'bad\\pipe'),
    '| Label | A | B |\n| --- | --- | --- |\n| x | 1 | 2 |\n| y | 2 | 3 |'
  ])('leaves nonnumeric, malformed, ambiguous or unsupported source intact: %s', source => {
    const { charts, plan } = controller('smart')
    expect(analyzeTable(source)).toBeUndefined()
    expect(charts.markdown(source, true)).toBe(source)
    expect(plan).not.toHaveBeenCalled()
  })

  it('does not chart code fences, streaming blocks, or oversized tables', () => {
    const { charts, plan } = controller('smart')
    expect(tableSlices('```md\n' + table + '\n```')).toEqual([])
    expect(charts.markdown(table, false)).toBe(table)
    expect(analyzeTable(table + '\n' + '| X | 2 |\n'.repeat(25))).toBeUndefined()
    expect(charts.markdown('x'.repeat(65537), true)).toHaveLength(65537)
    expect(plan).not.toHaveBeenCalled()
  })

  it('uses one smart plan for repeated identical source, retaining both original tables', async () => {
    const { charts, plan } = controller('smart')
    const source = table + '\n\n' + table
    charts.markdown(source, true)
    await paint()
    const projected = charts.markdown(source, true)
    expect(plan).toHaveBeenCalledOnce()
    expect(projected.split(table)).toHaveLength(3)
    expect(projected.match(/```svg/g)).toHaveLength(2)
    expect(projected).toContain('<polyline')
  })

  it('uses terminal semantic palette tokens across theme changes without model work', () => {
    const { charts, plan } = controller('always')
    const light = charts.markdown(table, true)
    const dark = charts.markdown(table, true)
    expect(light).toBe(dark)
    expect(light).toContain('var(--accent)')
    expect(light).toContain('var(--text)')
    expect(plan).not.toHaveBeenCalled()
    const parsed = analyzeTable(table)!
    expect(Object.isFrozen(parsed)).toBe(true)
    expect(chartSvg(parsed, 'bar')).not.toContain('#')
  })

  it('falls back locally on smart failure and cancels stale results on policy/session changes', async () => {
    const plan = vi.fn(async (): Promise<ChartKind> => { throw new Error('offline') })
    const { charts } = controller('smart', plan)
    charts.markdown(table, true)
    await paint()
    expect(charts.markdown(table, true)).toContain('<rect')
    expect(plan).toHaveBeenCalledOnce()
    const gate = Promise.withResolvers<ChartKind>()
    const stale = controller('smart', vi.fn(() => gate.promise)).charts
    stale.markdown(table, true)
    stale.configure('off')
    gate.resolve('line')
    await paint()
    expect(stale.markdown(table, true)).toBe(table)
    stale.configure('always')
    expect(stale.markdown(table, true)).not.toContain('<polyline')
  })

  it('bounds model calls per session with local fallback after the budget', async () => {
    const { charts, plan } = controller('smart')

    for (let i = 0; i < 12; i++) {
      charts.markdown(table.replace('Revenue', `Revenue ${i}`), true)
      await paint()
    }

    expect(plan).toHaveBeenCalledTimes(8)
  })

  it('keeps off as zero model calls and does not alter source/copy, even on resume', async () => {
    await mounted('off', async (app, send, markdown, plans) => {
      await send('message.start')
      await send('message.delta', { text: table })
      await send('message.complete', { status: 'complete', text: table })
      expect(markdown()).toContain(table)
      expect(markdown().join('')).not.toContain('```svg')
      app.transcript.load([{ role: 'assistant', text: table }])
      app.changed()
      await paint()
      expect(plans).toEqual([])
      expect(answerText(app.transcript.entries.find(e => e.kind === 'turn') as TurnEntry)).toBe(table)
    })
  })

  it('mounts App, waits until completion, uses native SVG fences, and restores charts on resume', async () => {
    await mounted('smart', async (app, send, markdown, plans) => {
      await send('message.start')
      await send('message.delta', { text: table })
      expect(markdown().join('')).not.toContain('```svg')
      expect(plans).toEqual([])
      await send('message.complete', { status: 'complete', text: table })
      expect(markdown().join('')).toContain('```svg')
      expect(markdown().join('')).toContain('<polyline')
      expect(plans).toHaveLength(1)
      await send('skin.changed', { name: 'dark', colors: {} })
      expect(plans).toHaveLength(1)
      app.transcript.load([{ role: 'assistant', text: table }])
      app.changed()
      await paint()
      expect(markdown().join('')).toContain('<polyline')
      expect(plans).toHaveLength(1)
      expect(answerText(app.transcript.entries.find(e => e.kind === 'turn') as TurnEntry)).toBe(table)
      await send('table_chart.policy', { mode: 'off' })
      expect(markdown().join('')).not.toContain('```svg')
    })
  })
})
