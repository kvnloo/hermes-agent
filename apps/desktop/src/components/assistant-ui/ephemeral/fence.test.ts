import { describe, expect, it } from 'vitest'

import { ephemeralCardDocument } from './document'
import { ephemeralCardSpec, ephemeralContextLine, parseEphemeralFence } from './model'

// The agent decides when a card helps and writes an `ephemeral-ui` fence: a cached kit card, or its own.
describe('ephemeral-ui fences the agent writes', () => {
  it('draws the agent’s own card for any app, with the brand from the kit catalog when it knows the app', () => {
    const card = parseEphemeralFence(JSON.stringify({ app: 'github', title: 'CI on main', status: '1 failing', html: '<b>lint</b> failed', summary: 'CI · lint failing' }))

    expect(card).toMatchObject({ server: 'agent', app: 'github', appName: 'GitHub', kind: 'card', tool: 'CI on main' })
    expect(card?.hex).toMatch(/^#[0-9a-f]{6}$/i)
    expect(ephemeralCardSpec(card!)).toEqual({ kind: 'card', app: 'github', appName: 'GitHub', hex: card!.hex, title: 'CI on main', status: '1 failing', html: '<b>lint</b> failed', summary: 'CI · lint failing' })

    const unknown = parseEphemeralFence(JSON.stringify({ app: 'Home Assistant', appName: 'Home Assistant', hex: '#18bcf2', kind: 'Thermostat', html: '<p>68°F</p>' }))
    expect(unknown).toMatchObject({ app: 'home-assistant', appName: 'Home Assistant', hex: '#18bcf2', kind: 'thermostat' })
  })

  it('uses a cached kit card only for a kind the kit draws, and says it is sample data', () => {
    const cached = parseEphemeralFence('{"app":"gmail","kind":"inbox"}')

    expect(cached).toMatchObject({ app: 'gmail', kind: 'inbox' })
    expect(cached?.written).toBeUndefined()
    expect(ephemeralCardSpec(cached!)).toEqual({ kind: 'inbox', app: 'gmail' })
    expect(ephemeralContextLine(cached!, 'Sam')).toContain('sample data')
    expect(ephemeralContextLine(parseEphemeralFence('{"app":"gmail","html":"<p>x</p>"}')!, 'Sam')).toContain('agent card')
  })

  it('leaves anything else as the fence source', () => {
    for (const code of ['not json', '[]', '{"app":"gmail"}', '{"app":"gmail","kind":"nope"}', '{"app":"x","html":"   "}', JSON.stringify({ app: 'x', html: 'y'.repeat(40_000) })]) {
      expect(parseEphemeralFence(code)).toBeNull()
    }
  })

  it('keeps written markup inside the config: it can never close the document’s script element', () => {
    const card = parseEphemeralFence(JSON.stringify({ app: 'x', html: '</script><script>alert(1)</script>' }))!
    const html = ephemeralCardDocument({ channel: 'c', scheme: 'dark', palette: {}, card: ephemeralCardSpec(card), pinned: false })

    expect(html).not.toContain('</script><script>alert(1)')
    expect(html).toContain("connect-src 'none'")
  })
})
