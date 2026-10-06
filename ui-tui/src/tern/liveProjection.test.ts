import { describe, expect, it } from 'vitest'

import type { TranscriptRow } from '../app/interfaces.js'
import type { Msg } from '../types.js'
import { projectTernTranscript, stableTernMessageId } from './liveProjection.js'

const row = (index: number, key: string, msg: Msg): TranscriptRow => ({ index, key, msg })

describe('native live transcript projection', () => {
  it('projects only user/assistant prose with stable semantic ids', () => {
    const rows = [
      row(0, 'intro:1:c80', { role: 'system', kind: 'intro', text: '' }),
      row(1, 'msg:101:c80', { role: 'user', text: 'Please inspect this.' }),
      row(2, 'msg:102:c80', { role: 'assistant', text: 'I will inspect it.' }),
      row(3, 'msg:103:c80', { role: 'system', text: 'ambient status' })
    ]

    expect(projectTernTranscript(rows, '')).toEqual([
      {
        id: 'hermes:message:msg:101',
        k: 'card',
        p: { role: 'omp.user', tone: 'user' },
        c: [{ id: 'hermes:message:msg:101:text', k: 'md', p: { text: 'Please inspect this.' } }]
      },
      {
        id: 'hermes:message:msg:102',
        k: 'md',
        p: { text: 'I will inspect it.' }
      }
    ])
  })

  it('keeps message ids stable across width-dependent virtual row keys', () => {
    expect(stableTernMessageId(row(1, 'msg:101:c80', { role: 'user', text: 'x' }))).toBe(
      stableTernMessageId(row(1, 'msg:101:c160', { role: 'user', text: 'x' }))
    )
  })

  it('uses one stable node for the current streaming assistant text', () => {
    const first = projectTernTranscript([], 'Working')
    const second = projectTernTranscript([], 'Working on it')

    expect(first[0]).toMatchObject({ id: 'hermes:streaming', k: 'md', p: { text: 'Working' } })
    expect(second[0]).toMatchObject({ id: 'hermes:streaming', k: 'md', p: { text: 'Working on it' } })
  })
})
