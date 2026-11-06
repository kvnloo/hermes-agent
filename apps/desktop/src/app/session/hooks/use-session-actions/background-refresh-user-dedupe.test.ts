import { describe, expect, it } from 'vitest'

import { type ChatMessage, chatMessageText, textPart } from '@/lib/chat-messages'

import { appendLiveSessionProjection, preserveLocalPendingTurnMessages } from './utils'

const user = (id: string, text: string, rowId: number): ChatMessage => ({
  id,
  role: 'user',
  parts: [textPart(text)],
  rowId
})

const toolGroup = (id: string, rowId: number, pending: boolean): ChatMessage => ({
  id,
  role: 'assistant',
  rowId,
  pending,
  parts: [
    {
      type: 'tool-call',
      toolCallId: id,
      toolName: 'terminal',
      args: { command: 'echo checked' },
      ...(pending ? {} : { result: 'checked' })
    }
  ]
})

describe('background refresh user identity (#145333)', () => {
  it('keeps the opening prompt once across repeated refreshes after committed tool progress', () => {
    const prompt = 'Why did four access points appear?'
    const steer = 'Continue checking the network'
    const persisted: ChatMessage[] = [
      user('stored-user-10', prompt, 10),
      toolGroup('stored-tool-11', 11, false),
      user('stored-user-12', steer, 12),
      toolGroup('assistant-stream-session', 13, true)
    ]
    const snapshot = {
      session_id: 'session',
      turn_started_at: 100,
      inflight: {
        user: prompt,
        corrections: [steer],
        assistant: 'Still checking',
        streaming: true
      }
    }

    let visible = persisted

    // Background completions can trigger multiple refreshes while the tool
    // turn is still live. Its durable opening prompt must never be reprojected.
    for (let receipt = 0; receipt < 4; receipt += 1) {
      const refreshed = appendLiveSessionProjection(persisted, snapshot)
      visible = preserveLocalPendingTurnMessages(refreshed, visible)

      expect(visible.filter(row => row.role === 'user' && chatMessageText(row) === prompt)).toHaveLength(1)
      expect(visible.some(row => row.id === 'user-inflight-session')).toBe(false)
    }
  })
})
