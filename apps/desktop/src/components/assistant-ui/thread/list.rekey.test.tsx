import { AssistantRuntimeProvider, type ThreadMessage, useAuiState } from '@assistant-ui/react'
import { act, cleanup, render, waitFor } from '@testing-library/react'
import { useMemo } from 'react'
import { afterEach, describe, expect, it } from 'vitest'

import { useRuntimeMessageRepository } from '@/app/chat/runtime-repository'
import { type ChatMessage, toChatMessages } from '@/lib/chat-messages'
import { useIncrementalExternalStoreRuntime } from '@/lib/incremental-external-store-runtime'

import { stubThreadEnvironment, stubThreadViewportSize } from '../test-utils'

import { ThreadMessageList } from './list'

stubThreadEnvironment()
stubThreadViewportSize()
afterEach(cleanup)

const preview = 'https://example.com/board'
const answer = `Board ready: [Preview: board](#preview/${preview})`

function messages(stage: 'streaming' | 'complete' | 'bound' | 'history', folded = false): ChatMessage[] {
  if (folded && stage === 'history') {
    return toChatMessages([
      { id: 10, role: 'user', content: 'First question', timestamp: 1 },
      { id: 11, role: 'assistant', content: 'First answer', timestamp: 2 },
      { id: 12, role: 'user', content: 'Show the board', timestamp: 3 },
      {
        id: 13,
        role: 'assistant',
        content: 'Building the board.',
        timestamp: 4,
        tool_calls: [{ id: 'board-call', type: 'function', function: { name: 'terminal', arguments: '{}' } }]
      },
      { id: 14, role: 'tool', tool_call_id: 'board-call', content: 'ok', timestamp: 5 },
      { id: 15, role: 'assistant', content: answer, timestamp: 6 }
    ])
  }

  const stored = stage === 'bound' || stage === 'history'
  const introduction: ChatMessage['parts'][number] = { type: 'text', text: 'Building the board.' }

  const tool: ChatMessage['parts'][number] = {
    type: 'tool-call',
    toolCallId: 'board-call',
    toolName: 'terminal',
    args: {},
    argsText: '{}',
    result: 'ok'
  }

  return [
    { id: 'old-user', rowId: 10, role: 'user', parts: [{ type: 'text', text: 'First question' }] },
    { id: 'old-assistant', rowId: 11, role: 'assistant', parts: [{ type: 'text', text: 'First answer' }] },
    {
      id: stage === 'history' ? 'stored-user' : 'stream-user',
      ...(stored ? { rowId: 12 } : {}),
      role: 'user',
      parts: [{ type: 'text', text: 'Show the board' }]
    },
    {
      id: stage === 'history' ? 'stored-assistant' : 'stream-assistant',
      ...(stored ? { rowId: folded ? 15 : 13 } : {}),
      role: 'assistant',
      pending: stage === 'streaming',
      parts: [...(folded ? [introduction, tool] : []), { type: 'text', text: answer, ...(stored && folded ? { sourceRowId: 15 } : {}) }]
    }
  ]
}

function MessageRow() {
  const id = useAuiState(s => s.message.id)

  const showPreview = useAuiState(s =>
    s.message.role === 'assistant' &&
    s.message.status.type === 'complete' &&
    s.message.content.some(part => part.type === 'text' && part.text.includes(preview))
  )

  return (
    <section data-message-id={id}>
      {showPreview && <iframe srcDoc="<input value='keep my selection'>" title={preview} />}
    </section>
  )
}

const messageComponents = { AssistantMessage: MessageRow, SystemMessage: MessageRow, UserMessage: MessageRow }

function Harness({ stage, folded = false, messageOverride, scope = 'rekey-session' }: {
  stage: Parameters<typeof messages>[0]
  folded?: boolean
  messageOverride?: ChatMessage[]
  scope?: string
}) {
  const currentMessages = useMemo(() => messageOverride ?? messages(stage, folded), [stage, folded, messageOverride])
  const messageRepository = useRuntimeMessageRepository(currentMessages)

  const runtime = useIncrementalExternalStoreRuntime<ThreadMessage>({
    messageRepository,
    isRunning: stage === 'streaming',
    onNew: async () => {}
  })

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <ThreadMessageList
        clampToComposer={false}
        components={messageComponents}
        sessionId={scope}
        sessionKey={scope}
      />
    </AssistantRuntimeProvider>
  )
}

const rows = (container: HTMLElement) => [...container.querySelectorAll('[data-slot="aui_message-group"]')]
const responses = (container: HTMLElement) => [...container.querySelectorAll('[data-slot="aui_response-group"]')]
const previewNode = (container: HTMLElement) => container.querySelector(`[title="${preview}"]`)

async function settle() {
  await act(async () => {
    await new Promise<void>(resolve => window.setTimeout(resolve, 0))
  })
}

describe('finished turn identity', () => {
  it('keeps the streamed turn and its preview mounted when stored rows bind', async () => {
    const { container, rerender } = render(<Harness stage="streaming" />)
    await settle()
    const streamingRows = rows(container)
    expect(streamingRows).toHaveLength(2)

    rerender(<Harness stage="complete" />)
    await waitFor(() => expect(previewNode(container)).not.toBeNull())
    expect(rows(container)).toEqual(streamingRows)
    const completedRows = rows(container)
    const completedResponses = responses(container)
    const completedFrame = previewNode(container)

    rerender(<Harness stage="bound" />)
    await settle()
    expect.soft(rows(container).map((row, index) => row === completedRows[index])).toEqual([true, true])
    expect.soft(responses(container).map((row, index) => row === completedResponses[index])).toEqual([true, true])
    expect(previewNode(container)).toBe(completedFrame)
  })

  it('keeps response sections and their preview mounted when history replaces renderer ids', async () => {
    const { container, rerender } = render(<Harness stage="bound" />)
    await waitFor(() => expect(previewNode(container)).not.toBeNull())
    const beforeRows = rows(container)
    const beforeResponses = responses(container)
    const beforeFrame = previewNode(container)
    expect(beforeRows).toHaveLength(2)
    expect(beforeResponses).toHaveLength(2)

    rerender(<Harness stage="history" />)
    await settle()
    expect.soft(rows(container).map((row, index) => row === beforeRows[index])).toEqual([true, true])
    expect.soft(responses(container).map((row, index) => row === beforeResponses[index])).toEqual([true, true])
    expect(previewNode(container)).toBe(beforeFrame)
    expect(container.querySelector('[data-message-id="stored-assistant"]')).not.toBeNull()
  })

  it('keeps the streamed preview through completion, receipt binding, and tool-folded history', async () => {
    expect(messages('bound', true).at(-1)?.rowId).toBe(15)
    expect(messages('history', true).at(-1)?.rowId).toBe(13)
    const { container, rerender } = render(<Harness folded stage="streaming" />)
    await settle()
    rerender(<Harness folded stage="complete" />)
    await waitFor(() => expect(previewNode(container)).not.toBeNull())
    const beforeRows = rows(container)
    const beforeResponses = responses(container)
    const beforeFrame = previewNode(container)
    const storedStages: ('bound' | 'history')[] = ['bound', 'history']

    for (const stage of storedStages) {
      rerender(<Harness folded stage={stage} />)
      await settle()
      expect.soft(rows(container).map((row, index) => row === beforeRows[index])).toEqual([true, true])
      expect.soft(responses(container).map((row, index) => row === beforeResponses[index])).toEqual([true, true])
      expect.soft(previewNode(container)).toBe(beforeFrame)
    }
  })

  it('uses durable occurrences rather than recycled renderer ids', async () => {
    const initial = messages('bound')
    const shifted = initial.slice(2).map((message, index) => ({
      ...message,
      id: index === 0 ? 'old-user' : 'old-assistant'
    }))

    const { container, rerender } = render(<Harness messageOverride={initial} stage="bound" />)
    await waitFor(() => expect(previewNode(container)).not.toBeNull())
    const beforeRows = rows(container)
    const beforeFrame = previewNode(container)
    expect(beforeRows).toHaveLength(2)

    rerender(<Harness messageOverride={shifted} stage="bound" />)
    await settle()
    expect(rows(container)[0]).toBe(beforeRows[1])
    expect(previewNode(container)).toBe(beforeFrame)

    const differentRows = shifted.map((message, index) => ({ ...message, rowId: 112 + index }))
    rerender(<Harness messageOverride={differentRows} stage="bound" />)
    await settle()
    expect(rows(container)[0]).not.toBe(beforeRows[1])
    expect(previewNode(container)).not.toBe(beforeFrame)
    expect(previewNode(container)).not.toBeNull()
    const freshFrame = previewNode(container)

    rerender(<Harness messageOverride={differentRows} scope="other-session" stage="bound" />)
    await settle()
    expect(previewNode(container)).not.toBe(freshFrame)
    expect(previewNode(container)).not.toBeNull()
  })
})
