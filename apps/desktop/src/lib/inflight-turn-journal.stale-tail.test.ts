import { describe, expect, it } from 'vitest'

import { type ChatMessage, toChatMessages } from '@/lib/chat-messages'
import type { SessionMessage } from '@/types/hermes'
import { mergeInFlightMessages } from '@/lib/inflight-turn-journal'

function user(id: string, text: string, extra: Partial<ChatMessage> = {}): ChatMessage {
  return { id, role: 'user', parts: [{ type: 'text', text }], ...extra }
}

function assistant(id: string, text: string, extra: Partial<ChatMessage> = {}): ChatMessage {
  return { id, role: 'assistant', parts: [{ type: 'text', text }], ...extra }
}

/** A journal snapshot only ever describes the turn that was streaming. Once the
 *  transcript holds that reply AND a newer committed turn, replaying the
 *  snapshot puts an already committed reply below newer content (#70108). */
describe('stale journal tail against superseded turns', () => {
  const base: ChatMessage[] = [
    user('u1', 'first prompt'),
    assistant('a1', 'first reply', { rowId: 101, durableComplete: true }),
    user('u2', 'second prompt'),
    assistant('a2', 'second reply', { rowId: 102, durableComplete: true })
  ]

  it('retires a stale tail whose prompt row no longer matches the transcript', () => {
    // Snapshot taken while turn 1 streamed: the reply row carries no durable id
    // yet, and its prompt row drifted from the transcript (rewritten prompt or a
    // changed attachment signature), so no base user matches it.
    const tail: ChatMessage[] = [
      user('j1', 'first prompt', { rowId: 100, attachmentRefs: ['@file:notes.md'] }),
      assistant('live-1', 'first reply')
    ]

    const recovered = mergeInFlightMessages(base, tail, { keepPending: false })

    expect(recovered.caughtUp).toBe(true)
    expect(recovered.messages).toBe(base)
  })

  it('still appends a tail the transcript never committed', () => {
    const tail: ChatMessage[] = [user('j2', 'third prompt'), assistant('live-2', 'third reply')]

    const recovered = mergeInFlightMessages(base, tail, { keepPending: false })

    expect(recovered.applied).toBe(true)
    expect(recovered.messages.map(message => message.id)).toEqual([
      ...base.map(message => message.id),
      'j2',
      'live-2'
    ])
  })

  it.each([
    ['durable prompt id', { rowId: 1, timestamp: 1 }],
    ['timestamp only', { timestamp: 1 }]
  ])('retires an off-page journal after a 120-row tail advances (%s)', (_, extra) => {
    const rounds = Array.from({ length: 65 }, (_, i): SessionMessage[] => {
      const id = 4 + i * 2
      const callId = `tool-${id}`

      return [
        {
          id,
          role: 'assistant',
          content: '',
          reasoning: `Reasoning ${id}`,
          tool_calls: [{ id: callId, function: { name: 'terminal', arguments: '{}' } }],
          timestamp: id
        },
        { id: id + 1, role: 'tool', tool_call_id: callId, content: 'ok', timestamp: id + 1 }
      ]
    }).flat()
    const storedRows: SessionMessage[] = [
      { id: 1, role: 'user', content: 'Old prompt', timestamp: 1 },
      { id: 2, role: 'assistant', content: 'Old answer', timestamp: 2 },
      { id: 3, role: 'user', content: 'Run tools', timestamp: 3 },
      ...rounds,
      { id: 134, role: 'assistant', content: 'Tools done', timestamp: 134 }
    ]
    const page = storedRows.slice(-120)
    expect(page).toHaveLength(120)
    expect(page.every(row => Number(row.id) > 3)).toBe(true)

    const hydrated = toChatMessages(page)
    const tail = [
      user('journal-user', 'Old prompt', extra),
      assistant('journal-answer', 'Old answer', { timestamp: 2 })
    ]
    const result = mergeInFlightMessages(hydrated, tail, { keepPending: false })

    expect(result.caughtUp).toBe(true)
    expect(result.messages).toBe(hydrated)
  })

  it('preserves a new live occurrence of older identical text', () => {
    const stored = [
      user('old-user', 'First prompt', { rowId: 1, timestamp: 1 }),
      assistant('old-answer', 'Still working.', { rowId: 2, timestamp: 2, durableComplete: true }),
      user('next-user', 'Second prompt', { rowId: 3, timestamp: 3 }),
      assistant('next-answer', 'Done.', { rowId: 4, timestamp: 4, durableComplete: true })
    ]
    const live = [
      user('current-user', 'Third prompt', { rowId: 5, timestamp: 5 }),
      assistant('current-answer', 'Still working.', { timestamp: 6 })
    ]
    const result = mergeInFlightMessages(stored, live, { keepPending: false })

    expect(result.caughtUp).toBe(false)
    expect(result.messages.at(-1)?.id).toBe('current-answer')
  })
})
