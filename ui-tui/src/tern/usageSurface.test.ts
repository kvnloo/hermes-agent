import { describe, expect, it } from 'vitest'

import {
  TERN_COMPOSER_ID,
  TERN_SURFACE_ID,
  TernComposerTransport
} from './composerSurface.js'
import { parseTspApc } from './protocol.js'
import {
  TERN_USAGE_ID,
  formatUsageSurfaceText,
  usageSurfaceNodes,
  type UsageNetworkSnapshot
} from './usageSurface.js'

const hello = {
  r: 'hello' as const,
  v: 1,
  term: 'tern',
  kinds: ['col', 'editor', 'text'],
  features: ['edit', 'send'],
  credits: 1
}

const fixture: UsageNetworkSnapshot = {
  savings: { solPi: 1240, rlm: 880, z0intOffload: 1860 },
  models: [
    { id: 'laya_421m', tok_s: 117.147, ttft_ms: 57.955, source: 'receipt' },
    { id: 'openjev_06b', tok_s: 87.93, ttft_ms: 49.951, source: 'receipt' },
    { id: 'frontier', tok_s: 42, ttft_ms: 210, source: 'derived' }
  ]
}

const messages = (writes: string[]) =>
  writes.map(wire => {
    const payload = wire.slice(2, -2)
    const envelope = parseTspApc(payload)

    return envelope ? { ...envelope, json: JSON.parse(envelope.body) } : null
  })

describe('usage surface text', () => {
  it('prints /usage savings and every model tok/s', () => {
    const lines = formatUsageSurfaceText(fixture)

    expect(lines[0]).toBe('/usage')
    expect(lines).toContain('SoL-Pi 1240 tok saved')
    expect(lines).toContain('RLM 880 tok saved')
    expect(lines).toContain('z0int 1860 tok saved')
    expect(lines.some(line => line.startsWith('laya_421m 117 tok/s'))).toBe(true)
    expect(lines.some(line => line.startsWith('openjev_06b 88 tok/s'))).toBe(true)
    expect(lines.some(line => line.startsWith('frontier 42 tok/s'))).toBe(true)
  })

  it('builds one text node per line under hermes:usage', () => {
    const nodes = usageSurfaceNodes(fixture)
    const joined = JSON.stringify(nodes)

    expect(nodes[0]?.id).toBe(TERN_USAGE_ID)
    expect(joined).toContain('/usage')
    expect(joined).toContain('SoL-Pi 1240 tok saved')
    expect(joined).toContain('RLM 880 tok saved')
    expect(joined).toContain('z0int 1860 tok saved')
  })
})

describe('Tern composer opens the usage column', () => {
  it('docks /usage with SoL-Pi, RLM, z0int, and every model tok/s', () => {
    const writes: string[] = []
    const transport = new TernComposerTransport(data => writes.push(data), hello, fixture)

    transport.start({ cursor: 0, text: '' }, true)

    const decoded = messages(writes)
    const wire = JSON.stringify(decoded)

    expect(wire).toContain(TERN_COMPOSER_ID)
    expect(wire).toContain(TERN_SURFACE_ID)
    expect(wire).toContain(TERN_USAGE_ID)
    expect(wire).toContain('/usage')
    expect(wire).toContain('SoL-Pi 1240 tok saved')
    expect(wire).toContain('RLM 880 tok saved')
    expect(wire).toContain('z0int 1860 tok saved')
    expect(wire).toContain('laya_421m 117 tok/s')
    expect(wire).toContain('openjev_06b 88 tok/s')
    expect(wire).toContain('frontier 42 tok/s')
  })
})
