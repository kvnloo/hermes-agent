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
  it('holds short notifications while hidden and restarts TTL on return', () => {
    const notes = new Dispatches()
    notes.show({ key: 'work', text: 'Started', level: 'info', kind: 'ttl', ttl_ms: 100 }, 100, true)
    expect(notes.active(20_000)).toEqual([])
    expect(notes.nextExpiry(20_000)).toBeNull()

    notes.resume(21_000)
    expect(notes.active(21_099).map(n => n.text)).toEqual(['Started'])
    expect(notes.active(21_100)).toEqual([])
  })

  it('cancels held notes and deduplicates repeated keys across visibility', () => {
    const notes = new Dispatches()
    notes.show({ key: 'stage', text: 'Old', level: 'info', kind: 'ttl' }, 100, true)
    notes.show({ key: 'stage', text: 'New', level: 'info', kind: 'ttl' }, 200, true)
    notes.show({ key: 'cleared', text: 'Cancelled', level: 'warn', kind: 'sticky' }, 300, true)
    notes.clear('cleared')
    notes.resume(20_000)
    expect(notes.active(20_000).map(n => n.text)).toEqual(['New'])
  })

  it('bounds held notifications and drops held updates on reset', () => {
    const notes = new Dispatches()
    for (let i = 0; i < 20; i++) {
      notes.show({ key: `task:${i}`, text: `Task ${i}`, level: 'success', kind: 'ttl' }, i, true)
    }
    notes.resume(20_000)
    expect(notes.active(20_000).map(n => n.text)).toEqual(
      Array.from({ length: 8 }, (_, i) => `Task ${i + 12}`)
    )
    notes.show({ key: 'unseen', text: 'Unseen', level: 'info', kind: 'ttl' }, 21_000, true)
    notes.reset()
    notes.resume(22_000)
    expect(notes.active(22_000)).toEqual([])
  })
})
