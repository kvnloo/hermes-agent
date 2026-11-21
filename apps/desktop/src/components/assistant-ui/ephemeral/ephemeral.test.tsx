import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const insert = vi.hoisted(() => vi.fn(async () => true))
vi.mock('@/app/chat/composer/focus', () => ({ requestComposerInsertAcked: insert }))

import { ephemeralCardDocument } from './document'
import { EPHEMERAL_UI_CONNECTORS, EPHEMERAL_UI_KINDS, EPHEMERAL_UI_REVISION } from './kit-meta.generated'
import { EPHEMERAL_PIN_LIMIT, ephemeralContextLine, ephemeralReceipt, matchEphemeralTool, parseEphemeralMessage } from './model'
import { EphemeralPinnedBar } from './pinned-bar'
import {
  $ephemeralCards,
  dissolveEphemeralCard,
  noteEphemeralCard,
  pinEphemeralCard,
  pinnedEphemeralCards,
  reopenEphemeralCard,
  unpinEphemeralCard
} from './store'

beforeEach(() => $ephemeralCards.set({}))

afterEach(() => {
  cleanup()
  insert.mockClear()
})

describe('ephemeral-ui tool cards', () => {
  it('vendors the kit at a pinned revision, with a card for every connector', () => {
    expect(EPHEMERAL_UI_REVISION).toMatch(/^[0-9a-f]{40}$/)
    expect(new Set(EPHEMERAL_UI_KINDS).size).toBe(EPHEMERAL_UI_KINDS.length)

    for (const [server, entry] of Object.entries(EPHEMERAL_UI_CONNECTORS)) {
      for (const [, kind] of entry.tools) {
        if (kind !== null) {
          expect(EPHEMERAL_UI_KINDS as readonly string[], `${server} → ${kind}`).toContain(kind)
        }
      }
    }
  })

  it('grows a card only from MCP calls on a known app server', () => {
    expect(matchEphemeralTool('mcp__gmail__search_threads')).toMatchObject({ app: 'gmail', kind: 'inbox', appName: 'Gmail' })
    expect(matchEphemeralTool('mcp__gmail__get_thread')).toMatchObject({ kind: 'thread' })
    expect(matchEphemeralTool('mcp__google_calendar__find_free_slots')).toMatchObject({ app: 'google-calendar', kind: 'slots' })
    expect(matchEphemeralTool('mcp__github__get_check_runs')).toMatchObject({ app: 'github', kind: 'ci' })
    expect(matchEphemeralTool('mcp__github__get_pull_request')).toMatchObject({ kind: 'merge' })
    expect(matchEphemeralTool('mcp__work_gmail__list')).toMatchObject({ app: 'gmail' })
    expect(matchEphemeralTool('mcp__stripe__create_refund')).toMatchObject({ kind: 'approve' })
    expect(matchEphemeralTool('terminal')).toBeNull()
    expect(matchEphemeralTool('mcp__filesystem__read_file')).toBeNull()
    expect(matchEphemeralTool('mcp__gmailer__list')).toBeNull()
  })

  it('reads only its own channel and bounds what a card reports', () => {
    expect(parseEphemeralMessage({ source: 'hermes-eui', channel: 'b', type: 'ready' }, 'a')).toBeNull()
    expect(parseEphemeralMessage({ type: 'eui:intent', detail: { label: 'raw kit post' } }, 'a')).toBeNull()
    expect(parseEphemeralMessage({ source: 'hermes-eui', channel: 'a', type: 'height', value: 1e9 }, 'a')).toEqual({ type: 'height', value: 4000 })
    expect(parseEphemeralMessage({ source: 'hermes-eui', channel: 'a', type: 'dissolved', summary: '  Gmail ·\n 3 unread ' }, 'a')).toEqual({
      type: 'dissolved',
      summary: 'Gmail · 3 unread'
    })

    expect(
      parseEphemeralMessage(
        {
          source: 'hermes-eui',
          channel: 'a',
          type: 'intent',
          detail: { kind: 'slots', action: 'select', label: '  Tue   10:00 ', ids: ['slot:tue-10', 'not an id', 7], summary: 'Calendar' }
        },
        'a'
      )
    ).toEqual({ type: 'intent', intent: { kind: 'slots', action: 'select', label: 'Tue 10:00', ids: ['slot:tue-10'] }, summary: 'Calendar' })

    expect(ephemeralContextLine({ kind: 'slots', appName: 'Google Calendar' }, 'Tue 10:00', ['slot:tue-10'])).toBe(
      '[ephemeral-ui slots · Google Calendar · sample data] Tue 10:00 (slot:tue-10)'
    )
  })

  it('builds an offline, network-free document whose config cannot close its script element', () => {
    const html = ephemeralCardDocument({ channel: 'c', scheme: 'dark', palette: {}, card: { kind: 'inbox', app: '</script><script>alert(1)</script>' }, pinned: false })

    expect(html).toContain("default-src 'none'")
    expect(html).toContain("connect-src 'none'")
    expect(html).not.toContain('</script><script>alert(1)')
  })

  it('walks a card through live → receipt → live → pinned → receipt, and history starts as a receipt', () => {
    const gmail = matchEphemeralTool('mcp__gmail__search_threads')!
    noteEphemeralCard('call-1', gmail, 's1', true)
    expect($ephemeralCards.get()['call-1'].phase).toBe('live')
    noteEphemeralCard('call-1', gmail, 's1', false) // a remount does not replay or reset it
    expect($ephemeralCards.get()['call-1'].phase).toBe('live')
    dissolveEphemeralCard('call-1')
    expect($ephemeralCards.get()['call-1']).toMatchObject({ phase: 'receipt', summary: 'Gmail · search threads' })
    reopenEphemeralCard('call-1')
    pinEphemeralCard('call-1')
    expect(pinnedEphemeralCards($ephemeralCards.get(), 's1').map(card => card.id)).toEqual(['call-1'])
    expect(pinnedEphemeralCards($ephemeralCards.get(), 's2')).toEqual([])
    unpinEphemeralCard('call-1')
    expect($ephemeralCards.get()['call-1'].phase).toBe('receipt')

    noteEphemeralCard('old', gmail, 's1', false)
    expect($ephemeralCards.get().old.phase).toBe('receipt')
  })

  it('writes receipts from the real call and never claims an outcome the card did not perform', () => {
    const slots = matchEphemeralTool('mcp__google_calendar__find_free_slots')!

    expect(ephemeralReceipt(slots)).toBe('Google Calendar · find free slots')
    expect(ephemeralReceipt(slots, 'Tue 10:00a')).toBe('Google Calendar · find free slots · you picked Tue 10:00a, not sent')
  })

  it(`keeps at most ${EPHEMERAL_PIN_LIMIT} pins per session, unpinning the oldest`, () => {
    const ci = matchEphemeralTool('mcp__github__get_check_runs')!
    const now = vi.spyOn(Date, 'now')

    for (let i = 0; i <= EPHEMERAL_PIN_LIMIT; i++) {
      now.mockReturnValue(1000 + i)
      noteEphemeralCard(`c${i}`, ci, 's1', true)
      pinEphemeralCard(`c${i}`)
    }

    now.mockRestore()
    const pinned = pinnedEphemeralCards($ephemeralCards.get(), 's1').map(card => card.id)
    expect(pinned).toHaveLength(EPHEMERAL_PIN_LIMIT)
    expect(pinned).not.toContain('c0')
    expect($ephemeralCards.get().c0.phase).toBe('receipt')
  })

  it('collapses a pinned card to an input-bar chip that opens it in a popup, and inserts only on request', async () => {
    const slots = matchEphemeralTool('mcp__google_calendar__find_free_slots')!
    noteEphemeralCard('cal', slots, 's1', true)
    dissolveEphemeralCard('cal')
    reopenEphemeralCard('cal')
    pinEphemeralCard('cal')

    const { container } = render(<EphemeralPinnedBar sessionId="s1" />)
    const chip = screen.getByRole('button', { name: 'Google Calendar: Google Calendar · find free slots' })
    expect(container.querySelector('iframe')).toBeNull() // collapsed: no card drawn until opened

    fireEvent.click(chip)
    const page = container.ownerDocument
    await waitFor(() => expect(page.querySelector('iframe[title="Google Calendar card (pinned)"]')).toBeTruthy(), { timeout: 10_000 })
    const frame = page.querySelector('iframe')!
    expect(frame.getAttribute('sandbox')).toBe('allow-scripts')
    const doc = frame.getAttribute('srcdoc') ?? ''
    expect(doc).toContain('"card":{"kind":"slots","app":"google-calendar"},"pinned":true')
    const channel = /"channel":"([a-z0-9]+)"/.exec(doc)?.[1]
    expect(insert).not.toHaveBeenCalled()

    act(() => {
      window.dispatchEvent(
        new MessageEvent('message', {
          data: { source: 'hermes-eui', channel, type: 'intent', detail: { kind: 'slots', action: 'select', label: 'Tue 10:00', ids: ['slot:tue-10'] } }
        })
      )
    })
    expect(await screen.findByText('Picked: Tue 10:00', { exact: false })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Add to chat' }))
    await screen.findByText('Added to the composer. Nothing was sent.', { exact: false })
    expect(insert).toHaveBeenCalledWith('[ephemeral-ui slots · Google Calendar · sample data] Tue 10:00 (slot:tue-10)', { mode: 'block', target: 'main' })

    fireEvent.click(screen.getByRole('button', { name: 'Unpin' }))
    await waitFor(() => expect(screen.queryByRole('toolbar', { name: 'Pinned cards' })).toBeNull())
    expect($ephemeralCards.get().cal.phase).toBe('receipt')
  }, 20_000)
})
