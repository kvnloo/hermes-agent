import { EventEmitter } from 'node:events'

import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

function fixture() {
  const app = new App(new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' }), new GatewayClient(), 'test')
  app.sid = 'live-parent'
  app.storedSid = 'stored-parent'

  return app
}

describe('classic session command dispatch', () => {
  it.each(['/branch', '/fork'])('%s adopts the independent child and applies its requested title', async command => {
    const app = fixture()
    const request = vi.spyOn(app.gw, 'request').mockResolvedValue({ session_id: 'stored-child' })
    const resume = vi.spyOn(app, 'resume').mockResolvedValue(undefined)
    await app.slash(`${command} --here alternate approach`)
    expect(request).toHaveBeenCalledWith('session.fork', { session_id: 'live-parent' })
    expect(request).toHaveBeenCalledWith('session.rename', { session_key: 'stored-child', title: 'alternate approach' })
    expect(resume).toHaveBeenCalledExactlyOnceWith('stored-child')
  })

  it.each(['/new', '/reset'])('%s titles only the newly created session', async command => {
    const app = fixture()
    vi.spyOn(app, 'newSession').mockImplementation(async () => { app.sid = 'fresh' })
    const request = vi.spyOn(app.gw, 'request').mockResolvedValue({})
    await app.slash(`${command} next task`)
    expect(request).toHaveBeenCalledExactlyOnceWith('session.title', { session_id: 'fresh', title: 'next task' })
  })

  it.each(['list', 'ls', 'browse'])('/sessions %s renders the picker instead of resuming a session named after the verb', async verb => {
    const app = fixture()
    vi.spyOn(app.gw, 'request').mockResolvedValue({ rows: [] })
    const resume = vi.spyOn(app, 'resume').mockResolvedValue(undefined)
    await app.slash(`/sessions ${verb}`)
    expect(resume).not.toHaveBeenCalled()
    const overlay = app.overlays.at(-1)!
    expect(overlay.key).toBe('sessions')
    expect(JSON.stringify(View.from({ layer: overlay.node('layer.sessions') }))).toContain('No saved sessions match')
  })

  it.each(['/quit', '/exit'])('%s --delete closes and deletes the stored session before exiting', async command => {
    const app = fixture()
    const order: string[] = []
    vi.spyOn(app.gw, 'request').mockImplementation(async method => { order.push(method); return {} })
    vi.spyOn(app, 'quit').mockImplementation(() => { order.push('quit') })
    await app.slash(`${command} --delete`)
    expect(app.gw.request).toHaveBeenCalledWith('session.delete', { session_id: 'stored-parent' })
    expect(order).toEqual(['session.close', 'session.delete', 'quit'])
  })
})
