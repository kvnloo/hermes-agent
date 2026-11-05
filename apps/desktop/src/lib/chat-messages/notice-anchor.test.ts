import { expect, it } from 'vitest'

import { type ChatMessage, preserveLocalSystemNotices, textPart } from './index'

const row = (id: string, role: 'user' | 'assistant', text: string, rowId: number): ChatMessage => ({
  id,
  role,
  parts: [textPart(text)],
  rowId
})

const older = [row('old-question', 'user', 'old question', 1), row('old-reply', 'assistant', 'old reply', 2)]
const notice: ChatMessage = {
  id: 'btw-complete-btw_1',
  role: 'system',
  parts: [textPart('[btw "aside"] answer')],
  noticeAfterId: 'old-reply',
  noticeAfterRowId: 2
}

const liveWithLaterTurn = (newReply: ChatMessage) => [
  ...older,
  notice,
  { id: 'user-optimistic', role: 'user' as const, parts: [textPart('new question')] },
  newReply
]

it('keeps a /btw answer in its original turn when an optimistic prompt hydrates (#149380)', () => {
  const newReply = row('new-reply', 'assistant', 'new reply', 4)
  const page = [
    row('hydrated-question', 'user', 'old question', 1),
    row('hydrated-reply', 'assistant', 'old reply', 2),
    row('new-question', 'user', 'new question', 3),
    newReply
  ]
  const result = preserveLocalSystemNotices(page, liveWithLaterTurn(newReply))

  expect(result.map(message => message.id)).toEqual([
    'hydrated-question',
    'hydrated-reply',
    'btw-complete-btw_1',
    'new-question',
    'new-reply'
  ])
  expect(preserveLocalSystemNotices(page, result)).toEqual(result)
})

it('drops a /btw answer instead of moving it into a later turn after compaction (#149380)', () => {
  const newReply = row('new-reply', 'assistant', 'new reply', 7)
  const page = [
    row('summary', 'assistant', 'compacted earlier context', 5),
    row('new-question', 'user', 'new question', 6),
    newReply
  ]

  expect(preserveLocalSystemNotices(page, liveWithLaterTurn(newReply))).toEqual(page)
})
