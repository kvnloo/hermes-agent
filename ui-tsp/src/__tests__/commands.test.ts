import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { ConfigGetResult } from '@hermes/shared/gateway-events'
import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { localCommand } from '../commands.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-native-settings-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('native reasoning command', () => {
  it('does not overwrite a resumed session when the old effort read completes', async () => {
    const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
    const gw = new GatewayClient()
    const app = new App(tern, gw, 'test')
    const read = Promise.withResolvers<ConfigGetResult>()
    vi.spyOn(gw, 'request').mockImplementation(method =>
      method === 'config.set' ? Promise.resolve({ key: 'reasoning', value: 'high' }) : read.promise
    )
    app.sid = 'old-session'
    app.info = { model: 'old-model', reasoning_effort: 'medium' }

    const pending = localCommand('reasoning')!.run(app, 'high')
    await new Promise<void>(resolve => setImmediate(resolve))
    app.sid = 'resumed-session'
    app.info = { model: 'resumed-model', reasoning_effort: 'low' }
    read.resolve({ value: 'high' })
    await pending

    expect(app.info).toEqual({ model: 'resumed-model', reasoning_effort: 'low' })
    expect(app.transcript.entries).toEqual([])
  })
})
