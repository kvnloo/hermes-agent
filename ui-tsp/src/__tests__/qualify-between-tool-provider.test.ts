import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { GatewayEvent, ReasoningPresentation } from '@hermes/shared/gateway-events'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { answerText } from '../answer-actions.js'
import { App } from '../app.js'
import type { TurnEntry } from '../model.js'
import { Transcript } from '../transcript.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const previous = process.env.HERMES_HOME
  const home = mkdtempSync(join(tmpdir(), 'hermes-narration-'))
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }
  rmSync(isolated.home, { recursive: true, force: true })
})
const paint = () => new Promise<void>(resolve => setImmediate(resolve))

const presentation: ReasoningPresentation[] = [
  { text: 'Private deliberation.', narration: false },
  { text: 'I found the cause.', narration: true }
]

async function mounted(run: (app: App, send: (type: GatewayEvent['type'], payload?: unknown) => Promise<void>, view: () => View | undefined) => Promise<void>) {
  const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockResolvedValue({})
  const app = new App(tern, gw, 'test')
  app.sid = 's'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = view => { latest = View.from(view); render(view) }

  try {
    await run(app, async (type, payload) => {
      gw.emit('event', { type, session_id: 's', payload } as GatewayEvent)
      await paint()
    }, () => latest)
  } finally { app.quit(); await running }
}

function descendants(view: View | undefined) {
  const visit = (tree: NonNullable<View['regions'][number]>): NonNullable<View['regions'][number]>[] => [tree, ...tree.children.flatMap(visit)]

  return view?.regions.flatMap(tree => tree ? visit(tree) : []) ?? []
}

describe('qualified provider narration', () => {
  it('renders qualified prose before and after tools as answer text, while thoughts stay folded', async () => {
    await mounted(async (app, send, view) => {
      await send('message.start')
      await send('reasoning.delta', { text: presentation.map(p => p.text).join('') })
      await send('reasoning.available', { text: '', presentation })
      await send('tool.start', { tool_id: 'read', name: 'read_file' })
      await send('tool.complete', { tool_id: 'read', name: 'read_file', result: { content: 'ok' } })
      await send('reasoning.available', { text: '', presentation: [{ text: 'The check passed.', narration: true }] })
      await send('message.complete', { status: 'complete', text: 'Fixed.' })
      const nodes = descendants(view())
      expect(nodes.filter(n => n.kind === 'md').map(n => n.props.text)).toContain('I found the cause.')
      expect(nodes.find(n => n.props.role === 'omp.thinking')?.props.collapsed).toBe(true)
      const turn = app.transcript.entries.find(e => e.kind === 'turn') as TurnEntry
      expect(answerText(turn)).toBe('I found the cause.\n\nThe check passed.\n\nFixed.')
    })
  })

  it('reconciles streamed/final reasoning idempotently without overwriting narration with final text', () => {
    const t = new Transcript()
    t.reasoning('Private deliberation.I found the cause.', 0)
    t.text('Fi', 1)
    t.reasoningBlock('', 2, presentation)
    t.reasoningBlock('', 3, presentation)
    t.complete({ status: 'complete', text: 'Fixed.' }, 4)
    const turn = t.entries[0] as TurnEntry
    expect(turn.blocks.filter(b => b.kind === 'thinking')).toHaveLength(1)
    expect(answerText(turn)).toBe('I found the cause.\n\nFixed.')
  })

  it('reconstructs the same display after resume without mutating canonical signed sidecars', () => {
    const messages = [{ role: 'assistant', text: 'Fixed.', reasoning: 'Private deliberation.I found the cause.',
      reasoning_presentation: presentation, reasoning_details: [{ signature: 'opaque-original', thinking: 'I found the cause.' }] }]

    const before = structuredClone(messages)
    const t = new Transcript()
    t.load(messages)
    expect(answerText(t.entries[0] as TurnEntry)).toBe('I found the cause.\n\nFixed.')
    expect(messages).toEqual(before)
  })

  it('never promotes unqualified ordinary thoughts', () => {
    const t = new Transcript()
    t.reasoning('I will inspect this.', 0)
    t.reasoningBlock('I will inspect this.', 1)
    t.complete({ status: 'complete' }, 2)
    expect(answerText(t.entries[0] as TurnEntry)).toBe('')
    expect((t.entries[0] as TurnEntry).blocks[0]?.kind).toBe('thinking')
  })
})
