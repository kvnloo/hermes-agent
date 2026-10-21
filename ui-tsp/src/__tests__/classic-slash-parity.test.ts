import { execFileSync } from 'node:child_process'
import { EventEmitter } from 'node:events'

import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { canonicalCommand, CLASSIC_COMMANDS } from '../classic-commands.js'
import { localCommand, localCompletions } from '../commands.js'
import { Composer } from '../composer.js'
import { Completion } from '../overlays/completion.js'

const names = CLASSIC_COMMANDS.flatMap(command => [command.name, ...command.aliases].map(name => ({ name, command })))

describe('classic slash registry parity', () => {
  it('is generated from the current Python canonical registry, not an independently maintained alias list', () => {
    execFileSync(process.env.HERMES_PYTHON || 'python', ['scripts/dump_tern_slash_registry.py', '--check'], { cwd: '..' })
  })

  it.each(names)('/$name resolves and dispatches to the same local owner as its canonical command', ({ name, command }) => {
    expect(canonicalCommand(name.toUpperCase())).toBe(command.name)
    expect(localCommand(name)).toBe(localCommand(command.name))
  })

  it.each(names.filter(({ command }) => !command.gateway_only))('/$name has an exact rendered completion even with empty backend results', async ({ name }) => {
    vi.useFakeTimers()
    try {
      const gw = new GatewayClient()
      vi.spyOn(gw, 'request').mockResolvedValue({ items: [{ text: '/irrelevant', display: 'irrelevant', kind: 'command', meta: 'fuzzy match' }] })
      const completion = new Completion({ changed() {}, open() {}, close() {} }, gw, () => 'sid')
      const composer = new Composer()
      composer.set(`/${name}`)
      completion.update(composer)
      await vi.advanceTimersByTimeAsync(61)
      const view = View.from({ layer: completion.nodes('input') })
      expect(completion.items[0]?.text).toBe(`/${name}`)
      expect(JSON.stringify(view)).toContain(name)
      completion.dismiss()
    } finally { vi.useRealTimers() }
  })

  it.each(localCompletions())('$text is discoverable and has a dispatch owner and description', item => {
    expect(localCommand(item.text.slice(1))).toBeDefined()
    expect(item.meta).toBeTruthy()
  })

  it.each(['/q list', '/Q list'])('%s reaches queue RPC without calling quit', async command => {
    const app = new App(new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' }), new GatewayClient(), 'test')
    app.sid = 'sid'
    const request = vi.spyOn(app.gw, 'request').mockResolvedValue({ output: 'No queued prompts.' })
    const quit = vi.spyOn(app, 'quit')
    await app.slash(command)
    expect(request).toHaveBeenCalledWith('slash.exec', { command: command.slice(1), session_id: 'sid' })
    expect(quit).not.toHaveBeenCalled()
    expect(app.transcript.entries.at(-1)).toMatchObject({ kind: 'panel', text: 'No queued prompts.', format: 'plain' })
  })

  it.each(['/clear', '/new', '/reset'])('%s closes the active session and creates a fresh gateway session, not a cosmetic clear', async command => {
    const gw = new GatewayClient()
    const app = new App(new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' }), gw, 'test')
    app.sid = 'old'
    app.transcript.notice('old conversation')
    const calls: string[] = []
    vi.spyOn(gw, 'request').mockImplementation(async method => {
      calls.push(method)
      if (method === 'settings.get') { return { values: {} } }
      if (method === 'setup.status') { return { provider_configured: true } }
      if (method === 'session.create') { return { session_id: 'fresh', stored_session_id: 'fresh-stored' } }
      return {}
    })
    await app.slash(command)
    expect(calls.filter(method => ['setup.status', 'session.close', 'session.create'].includes(method))).toEqual(['setup.status', 'session.close', 'session.create'])
    expect(gw.request).toHaveBeenCalledWith('session.close', { session_id: 'old' })
    expect(app.sid).toBe('fresh')
    expect(app.storedSid).toBe('fresh-stored')
    expect(app.transcript.entries[0]).toMatchObject({ kind: 'welcome' })
    expect(JSON.stringify(app.transcript.entries)).not.toContain('old conversation')
  })
})
