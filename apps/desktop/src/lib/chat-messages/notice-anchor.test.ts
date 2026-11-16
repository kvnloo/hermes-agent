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

it('keeps a waiting generic notice before its next held row when /btw anchors earlier (#149380)', () => {
  const source = row('source', 'assistant', 'answer before aside', 11)
  const middle = row('middle', 'user', 'later question', 12)
  const last = row('last', 'assistant', 'later answer', 13)
  const generic: ChatMessage = {
    id: 'background-complete',
    role: 'system',
    parts: [textPart('background finished')]
  }
  const anchored: ChatMessage = {
    ...notice,
    id: 'btw-complete-anchored',
    noticeAfterId: source.id,
    noticeAfterRowId: source.rowId
  }

  const page = [source, middle, last]
  const current = [source, middle, generic, anchored, last]
  const result = preserveLocalSystemNotices(page, current)

  expect(result.map(message => message.id)).toEqual([
    'source',
    'btw-complete-anchored',
    'middle',
    'background-complete',
    'last'
  ])
})

it('reanchors a /btw answer on a hydrated optimistic user row without a rowId (#149380)', () => {
  const optimistic: ChatMessage = {
    id: 'optimistic-next',
    role: 'user',
    parts: [textPart('next question')]
  }
  const hydrated = row('hydrated-next', 'user', 'next question', 3)
  const anchored: ChatMessage = {
    ...notice,
    id: 'btw-complete-optimistic',
    noticeAfterId: optimistic.id,
    noticeAfterRowId: undefined
  }

  const page = [...older, hydrated]
  const result = preserveLocalSystemNotices(page, [...older, optimistic, anchored])

  expect(result.map(message => message.id)).toEqual([
    'old-question',
    'old-reply',
    'hydrated-next',
    'btw-complete-optimistic'
  ])
  expect(result.at(-1)?.noticeAfterId).toBe('hydrated-next')
  expect(result.at(-1)?.noticeAfterRowId).toBe(3)
  expect(preserveLocalSystemNotices(page, result)).toEqual(result)
})
