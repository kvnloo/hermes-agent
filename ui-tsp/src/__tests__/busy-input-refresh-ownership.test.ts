import type { App } from '../app.js'
import { BusyInput } from '../busy-input.js'
import { describe, expect, it, vi } from 'vitest'

interface DeferredRead {
  method: string
  params: { key: string; session_id: string }
  resolve(value: { value: unknown }): void
  reject(error: Error): void
}

function fixture() {
  const pending: DeferredRead[] = []
  const changed = vi.fn()
  const request = vi.fn((method: string, params: DeferredRead['params']) =>
    new Promise<{ value: unknown }>((resolve, reject) => {
      pending.push({ method, params, resolve, reject })
    })
  )
  // BusyInput uses only the gateway request, current session id and changed
  // callback on a preference read. No SDK, model, daemon or terminal required.
  const app = { sid: 'session-a', gw: { request }, changed } as unknown as App

  return { app, input: new BusyInput(app), pending, changed, request }
}

describe('busy preference ownership across asynchronous session reads', () => {
  it('only adopts the latest response for two reads of the same session', async () => {
    const h = fixture()
    const old = h.input.refresh()
    const newest = h.input.refresh()

    expect(h.pending.map(({ method, params }) => [method, params])).toEqual([
      ['config.get', { key: 'busy', session_id: 'session-a' }],
      ['config.get', { key: 'busy', session_id: 'session-a' }]
    ])
    expect(h.changed).not.toHaveBeenCalled()

    h.pending[1]!.resolve({ value: 'steer' })
    await newest
    expect(h.input.mode).toBe('steer')
    expect(h.changed).toHaveBeenCalledTimes(1)

    h.pending[0]!.resolve({ value: 'queue' })
    await old
    expect(h.input.mode).toBe('steer')
    expect(h.changed).toHaveBeenCalledTimes(1)
  })

  it('discards the old response when a different session is adopted', async () => {
    const h = fixture()
    const old = h.input.refresh()

    h.app.sid = 'session-b'
    const newer = h.input.refresh()

    h.pending[0]!.resolve({ value: 'steer' })
    await old
    expect(h.input.mode).toBe('queue')
    expect(h.changed).not.toHaveBeenCalled()

    h.pending[1]!.resolve({ value: 'steer' })
    await newer
    expect(h.input.mode).toBe('steer')
    expect(h.changed).toHaveBeenCalledTimes(1)
    expect(h.pending[1]!.params.session_id).toBe('session-b')
  })

  it('invalidates a pending read when the session becomes detached', async () => {
    const h = fixture()
    const old = h.input.refresh()

    h.app.sid = null
    await h.input.refresh()
    expect(h.pending).toHaveLength(1)
    h.pending[0]!.resolve({ value: 'steer' })
    await old

    expect(h.input.mode).toBe('queue')
    expect(h.changed).not.toHaveBeenCalled()
  })

  it('retains the last confirmed hint after a failed newer read and a late rejection', async () => {
    const h = fixture()
    const initial = h.input.refresh()
    h.pending[0]!.resolve({ value: 'steer' })
    await initial

    const older = h.input.refresh()
    const newer = h.input.refresh()
    h.pending[2]!.reject(new Error('offline'))
    await newer
    h.pending[1]!.reject(new Error('late offline'))
    await older

    expect(h.input.mode).toBe('steer')
    expect(h.changed).toHaveBeenCalledTimes(1)
  })

  it.each([null, undefined, '', 'interrupt', 'STEER', 'queue', 1, false])(
    'never treats unsupported gateway value %s as implicit steering',
    async value => {
      const h = fixture()
      const read = h.input.refresh()
      h.pending[0]!.resolve({ value })
      await read
      expect(h.input.mode).toBe('queue')
      expect(h.input.shouldSteer(false)).toBe(false)
      expect(h.input.shouldSteer(true)).toBe(true)
    }
  )

  it('preserves explicit alternate-intent inversion for the confirmed steer preference', async () => {
    const h = fixture()
    const read = h.input.refresh()
    h.pending[0]!.resolve({ value: 'steer' })
    await read

    expect(h.input.mode).toBe('steer')
    expect(h.input.shouldSteer(false)).toBe(true)
    expect(h.input.shouldSteer(true)).toBe(false)
    expect(h.request).toHaveBeenCalledTimes(1)
  })
})
