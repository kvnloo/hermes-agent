import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const insert = vi.hoisted(() => vi.fn(async () => true))
vi.mock('@/app/chat/composer/focus', () => ({ requestComposerInsertAcked: insert }))

import { ephemeralCardsDocument } from './ephemeral-cards-document'
import {
  ephemeralCardApp,
  ephemeralCardsProblem,
  ephemeralIntentContext,
  parseEphemeralMessage
} from './ephemeral-cards-model'
import { EPHEMERAL_UI_APPS_BY_KIND, EPHEMERAL_UI_KINDS, EPHEMERAL_UI_REVISION } from './ephemeral-ui-kinds.generated'
import { inspectOpenUiBoard } from './openui-catalog'
import { RichCodeBlock } from './registry'

const board = [
  'root = Board("ephemeral-ui cards", "Mail, CI and a session trace. Sample data.", [kit])',
  'kit = EphemeralCards("Kit cards", [{kind: "inbox", app: "gmail"}, {kind: "ci", app: "github"}, {kind: "trace"}])'
].join('\n')

const embed = (code: string) =>
  <RichCodeBlock code={code} fallback={<pre data-testid="fence">{code}</pre>} language="openui-v2" streaming={false} />

afterEach(() => {
  cleanup()
  insert.mockClear()
})

describe('ephemeral-ui kit', () => {
  it('vendors all 50 card.v0 kinds, each with a default catalog app', () => {
    expect(EPHEMERAL_UI_KINDS).toHaveLength(50)
    expect(new Set(EPHEMERAL_UI_KINDS).size).toBe(50)
    expect(EPHEMERAL_UI_REVISION).toMatch(/^[0-9a-f]{40}$/)

    for (const kind of EPHEMERAL_UI_KINDS) {
      expect(EPHEMERAL_UI_APPS_BY_KIND[kind]?.length, kind).toBeGreaterThan(0)
    }
  })

  it('keeps a named app only when the catalog lists it for that kind', () => {
    expect(ephemeralCardApp('inbox', 'gmail')).toBe('gmail')
    expect(ephemeralCardApp('inbox', 'uber')).toBe(EPHEMERAL_UI_APPS_BY_KIND.inbox[0])
    expect(ephemeralCardApp('ride')).toBe(EPHEMERAL_UI_APPS_BY_KIND.ride[0])
  })

  it('accepts input only on trace kinds, within the size limit', () => {
    expect(ephemeralCardsProblem({ title: 'x', cards: [{ kind: 'trace', input: { a: 1 } }] })).toBeNull()
    expect(ephemeralCardsProblem({ title: 'x', cards: [{ kind: 'inbox', input: {} }] })).toMatch(/takes no input/)
    expect(ephemeralCardsProblem({ title: 'x', cards: [{ kind: 'trace', input: 'x'.repeat(40_000) }] })).toMatch(/exceeds/)
  })

  it('reads only its own channel and bounds what a card reports', () => {
    expect(parseEphemeralMessage({ source: 'hermes-eui', channel: 'b', type: 'ready' }, 'a')).toBeNull()
    expect(parseEphemeralMessage({ type: 'eui:intent', detail: { label: 'raw kit post' } }, 'a')).toBeNull()
    expect(parseEphemeralMessage({ source: 'hermes-eui', channel: 'a', type: 'height', value: 1e9 }, 'a'))
      .toEqual({ type: 'height', value: 20_000 })

    const intent = parseEphemeralMessage({
      source: 'hermes-eui',
      channel: 'a',
      type: 'intent',
      detail: { kind: 'inbox', app: 'gmail', action: 'select', label: '  Q3   budget ', ids: ['mail:m1', 'not an id', 7] }
    }, 'a')

    expect(intent).toEqual({
      type: 'intent',
      intent: { kind: 'inbox', app: 'gmail', action: 'select', label: 'Q3 budget', ids: ['mail:m1'] }
    })

    if (intent?.type === 'intent') {
      expect(ephemeralIntentContext(intent.intent, 'gmail')).toBe('[ephemeral-ui inbox · gmail · sample data] Q3 budget (mail:m1)')
    }
  })

  it('builds an offline document whose config cannot close its script element', () => {
    const html = ephemeralCardsDocument({
      channel: 'c',
      scheme: 'dark',
      palette: {},
      cards: [{ kind: 'inbox', app: '</script><script>alert(1)</script>' }]
    })

    expect(html).toContain("default-src 'none'")
    expect(html).toContain("connect-src 'none'")
    expect(html).not.toContain('</script><script>alert(1)')
    expect(html.match(/<script/g)?.length).toBe(3)
  })

  it('parses the literal positional program and rejects bad cards', () => {
    expect(inspectOpenUiBoard(board)).toEqual({ kind: 'ready' })
    expect(inspectOpenUiBoard(board.replace('"ci"', '"not-a-kind"')).kind).toBe('invalid')
    expect(inspectOpenUiBoard(board.replace('{kind: "ci", app: "github"}', '{kind: "ci", input: {x: 1}}')).kind).toBe('invalid')
  })

  it('renders the cards in a sandboxed frame and adds a pick to the composer only on request', async () => {
    const { container } = render(embed(board))
    const region = await screen.findByRole('region', { name: 'Kit cards' })
    expect(region.getAttribute('data-ephemeral-ui-cards')).toBe('inbox ci trace')
    await waitFor(() => expect(container.querySelector('iframe')).toBeTruthy(), { timeout: 10_000 })
    const frame = container.querySelector('iframe')!
    expect(frame.getAttribute('sandbox')).toBe('allow-scripts')
    const doc = frame.getAttribute('srcdoc') ?? ''
    expect(doc).toContain('"kind":"inbox","app":"gmail"')
    expect(doc).toContain('"kind":"trace","app":"omp-stats"')
    const channel = /"channel":"([a-z0-9]+)"/.exec(doc)?.[1]
    expect(channel).toBeTruthy()
    expect(insert).not.toHaveBeenCalled()

    act(() => {
      window.dispatchEvent(new MessageEvent('message', {
        data: { source: 'hermes-eui', channel, type: 'intent', detail: { kind: 'inbox', app: 'gmail', action: 'select', label: 'Invoice #4512', ids: ['mail:4512'] } }
      }))
      window.dispatchEvent(new MessageEvent('message', { data: { source: 'hermes-eui', channel, type: 'height', value: 777 } }))
    })
    expect(await screen.findByText('Picked: Invoice #4512', { exact: false })).toBeTruthy()
    expect(frame.style.height).toBe('777px')
    fireEvent.click(screen.getByRole('button', { name: 'Add to chat' }))
    await screen.findByText('Added to the composer. Nothing was sent.', { exact: false })
    expect(insert).toHaveBeenCalledWith('[ephemeral-ui inbox · gmail · sample data] Invoice #4512 (mail:4512)', { mode: 'block', target: 'main' })
  }, 20_000)

  it('says so when no composer takes the pick', async () => {
    insert.mockResolvedValueOnce(false)
    const { container } = render(embed(board))
    await waitFor(() => expect(container.querySelector('iframe')).toBeTruthy(), { timeout: 10_000 })
    const channel = /"channel":"([a-z0-9]+)"/.exec(container.querySelector('iframe')!.getAttribute('srcdoc') ?? '')?.[1]
    act(() => {
      window.dispatchEvent(new MessageEvent('message', {
        data: { source: 'hermes-eui', channel, type: 'intent', detail: { kind: 'ci', action: 'rerun', label: 'Re-run lint' } }
      }))
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Add to chat' }))
    expect(await screen.findByText('No open composer to add this to.', { exact: false })).toBeTruthy()
  }, 20_000)
})
