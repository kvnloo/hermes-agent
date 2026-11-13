import { describe, expect, it } from 'vitest'

import {
  EPHEMERAL_KINDS,
  ephemeralFrameDocument,
  INTENT_PREFIX,
  isTraceKind,
  kitTheme,
  MAX_CARDS,
  parseEphemeralFence
} from './ephemeral-ui-model'

describe('ephemeral-ui card.v0 fence', () => {
  it('takes the 50 kinds from the vendored card.v0.json', () => {
    expect(EPHEMERAL_KINDS).toHaveLength(50)
    expect(EPHEMERAL_KINDS).toContain('inbox')
    expect(EPHEMERAL_KINDS).toContain('trace-frustration')
    expect(EPHEMERAL_KINDS).toContain('infra-models')
  })

  it('accepts every kind as a single card, an array and a cards object', () => {
    for (const kind of EPHEMERAL_KINDS) {
      expect(parseEphemeralFence(JSON.stringify({ kind, app: 'github' }))).toEqual({ kind: 'ready', cards: [{ kind, app: 'github' }] })
    }

    expect(parseEphemeralFence('[{"kind":"ride","app":"uber"},{"kind":"route"}]')).toEqual({
      kind: 'ready',
      cards: [{ kind: 'ride', app: 'uber' }, { kind: 'route' }]
    })
    expect(parseEphemeralFence('{"cards":[{"kind":"merge","app":"github","wide":true}]}')).toEqual({
      kind: 'ready',
      cards: [{ kind: 'merge', app: 'github', wide: true }]
    })
  })

  it('rejects unknown kinds, bad app ids, broken JSON and oversized boards before rendering', () => {
    expect(parseEphemeralFence('{"kind":"sculpt"}')).toEqual({ kind: 'invalid', reason: 'card', detail: 'sculpt' })
    expect(parseEphemeralFence('{"kind":"inbox","app":"javascript:alert(1)"}')).toMatchObject({ kind: 'invalid', reason: 'card' })
    expect(parseEphemeralFence('{"kind":"inbox"')).toEqual({ kind: 'invalid', reason: 'json' })
    expect(parseEphemeralFence('[]')).toEqual({ kind: 'invalid', reason: 'empty' })
    expect(parseEphemeralFence(JSON.stringify(Array.from({ length: MAX_CARDS + 1 }, () => ({ kind: 'ci' }))))).toEqual({
      kind: 'invalid',
      reason: 'tooMany'
    })
    expect(parseEphemeralFence(JSON.stringify({ kind: 'ci', note: 'x'.repeat(9000) }))).toEqual({ kind: 'invalid', reason: 'oversized' })
  })

  it('marks only trace kinds as needing the trace fixture', () => {
    expect(EPHEMERAL_KINDS.filter(isTraceKind)).toEqual([
      'trace', 'trace-span', 'trace-summary', 'trace-usage', 'trace-tools', 'trace-errors', 'trace-compare', 'trace-frustration'
    ])
  })

  it('builds a frame that embeds data safely and runs the host chrome last', () => {
    const doc = ephemeralFrameDocument({
      cards: [{ kind: 'inbox', app: 'gmail' }],
      chrome: '<script>/*chrome*/</script>',
      css: '.x{} </style><script>bad()</script>',
      files: { 'data/apps.json': '{"apps":[{"name":"</script><script>bad()</script>"}]}' },
      runtime: 'var s="</script>";',
      scheme: 'dark'
    })

    expect(doc.startsWith('<!doctype html>')).toBe(true)
    expect(doc).not.toContain('</script><script>bad()')
    expect(doc).not.toContain('</style><script>bad()')
    expect(doc).toContain('data-eui-file="data/apps.json"')
    expect(doc).toContain('"theme":"hermes-mono"')
    expect(doc).toContain(JSON.stringify(INTENT_PREFIX).slice(1, 20))
    expect(doc.indexOf('/*chrome*/')).toBeGreaterThan(doc.indexOf('var s='))
    expect(kitTheme('light')).toBe('hermes-nous')
  })

  it('matches the kit theme to the active desktop skin', () => {
    expect(kitTheme('dark', 'nous')).toBe('hermes-nous-dark')
    expect(kitTheme('dark', 'midnight')).toBe('hermes-midnight')
    expect(kitTheme('dark', 'unknown-skin')).toBe('hermes-mono')
    expect(kitTheme('light', 'midnight')).toBe('hermes-nous')
  })
})
