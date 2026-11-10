// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'

import { VoiceLiveSession } from './voice-live'

afterEach(() => vi.useRealTimers())

it('paces GPT-Live chunks by ack and discards the old queue on a new delegation (#152345)', () => {
  vi.useFakeTimers()
  const send = vi.fn()
  const session = new VoiceLiveSession({
    onClosed: vi.fn(),
    onDelegation: vi.fn(),
    onError: vi.fn()
  })
  Object.assign(session, { events: { readyState: 'open', send } })
  const receive = (event: object) =>
    (session as unknown as { handleEvent: (raw: string) => void }).handleEvent(JSON.stringify(event))

  session.speak('d1', 'One long result, '.repeat(120))
  expect(send).toHaveBeenCalledTimes(1)
  const first = JSON.parse(send.mock.calls[0][0])
  expect(first.type).toBe('session.commentary.append')
  expect(first.content.length).toBeLessThanOrEqual(800)

  receive({ type: 'session.commentary.appended', client_event_id: first.event_id })
  expect(send).toHaveBeenCalledTimes(2)
  const second = JSON.parse(send.mock.calls[1][0])

  receive({ type: 'session.delegation.created', delegation: { id: 'd2' } })
  receive({ type: 'session.commentary.appended', client_event_id: second.event_id })
  vi.advanceTimersByTime(5_100)
  expect(send).toHaveBeenCalledTimes(2)

  session.speak('d2', 'This is the new answer.')
  expect(JSON.parse(send.mock.calls[2][0])).toMatchObject({
    content: 'This is the new answer.',
    delegation_id: 'd2'
  })
})
