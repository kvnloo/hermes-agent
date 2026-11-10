import type { PersistedTurn } from '@hermes/shared'
import { describe, expect, it } from 'vitest'

import type { ChatMessage } from '@/lib/chat-messages'

import { bindReceiptUserRows } from './receipt-user-rows'

// Measured in #149560: a steered turn has two user rows, but the window may
// only show its original prompt. The prompt has no rowId, although the final
// bubble already carries that turn's partial completion receipt.
const previousTurn = (): ChatMessage[] => [
  { id: 'user-previous', role: 'user', parts: [{ type: 'text', text: 'Prompt N' }] },
  {
    id: 'reply-previous',
    role: 'assistant',
    parts: [{ type: 'text', text: 'FINAL A' }],
    persistedTurn: {
      row_ids: [103250, 103295, 103328],
      complete: false,
      user_row_id: 103250,
      user_row_ids: [103250, 103295],
      final_assistant_row_id: 103328
    }
  }
]

const nextReceipt: PersistedTurn = {
  row_ids: [103329, 103330],
  complete: true,
  user_row_id: 103329,
  user_row_ids: [103329],
  final_assistant_row_id: 103330
}

describe('receipt user-row turn boundary', () => {
  it('does not bind an earlier prompt to a process_complete turn that drew no prompt', () => {
    const messages = previousTurn()

    // 103329 belongs to a background-process notification, not to Prompt N.
    expect(bindReceiptUserRows(messages, nextReceipt)).toEqual(messages)
  })

  it('still binds the new user prompt when it really follows the completed turn', () => {
    const messages: ChatMessage[] = [
      ...previousTurn(),
      { id: 'user-new', role: 'user', parts: [{ type: 'text', text: 'New prompt' }] }
    ]

    const bound = bindReceiptUserRows(messages, nextReceipt)

    expect(bound[0].rowId).toBeUndefined()
    expect(bound[2].rowId).toBe(103329)
  })
})
