import { describe, expect, it } from 'vitest'

import { Dispatches } from '../attention.js'

describe('native Tern gateway dispatches', () => {
  it('upserts keys without duplicates and clears only matching notices', () => {
    const notes = new Dispatches()
    notes.show({ text: 'Starting', key: 'work', level: 'info', kind: 'ttl' }, 100)
    notes.show({ text: 'Now working', key: 'work', level: 'success', kind: 'ttl', ttl_ms: 2_000 }, 200)
    notes.show({ text: 'Needs attention', key: 'approval', level: 'warn', kind: 'sticky' }, 300)

    expect(notes.active(301).map(note => note.text)).toEqual(['Now working', 'Needs attention'])
    expect(notes.nextExpiry(301)).toBe(2_200)
    notes.clear('work')
    expect(notes.active(302).map(note => note.key)).toEqual(['approval'])
    expect(notes.nextExpiry(302)).toBeNull()
  })

  it('expires short-lived entries without clearing sticky notices', () => {
    const notes = new Dispatches()
    notes.show({ text: 'Timed', id: 'sent', level: 'info', kind: 'agent', ttl_ms: 100 }, 1_000)
    notes.show({ text: 'Persistent', key: 'credential', level: 'error', kind: 'sticky', ttl_ms: 100 }, 1_000)
    expect(notes.active(1_099)).toHaveLength(2)
    expect(notes.active(1_100).map(note => note.text)).toEqual(['Persistent'])
    notes.reset()
    expect(notes.active(1_101)).toEqual([])
  })

  it('bounds the view, TTL and unusable payloads', () => {
    const notes = new Dispatches()
    notes.show({ text: '   ', level: 'info', kind: 'ttl' }, 0)
    for (let i = 0; i < 20; i++) {
      notes.show({ text: `note ${i}`, level: 'bogus', kind: 'ttl', ttl_ms: Infinity }, 0)
    }
    const shown = notes.active(0)
    expect(shown).toHaveLength(8)
    expect(shown[0]?.text).toBe('note 12')
    expect(shown.every(n => n.level === 'info' && n.expiresAt === 6_000)).toBe(true)
    notes.show({ text: 'bounded TTL', key: 'cap', level: 'success', kind: 'ttl', ttl_ms: 900_000 }, 100)
    expect(notes.active(100).find(n => n.key === 'cap')?.expiresAt).toBe(60_100)
  })
})
