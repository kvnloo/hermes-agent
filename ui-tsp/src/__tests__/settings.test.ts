import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { SettingsField, SettingsGetResult } from '@hermes/shared/gateway-events'
import type { Surface, TspEvent } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { localCommand } from '../commands.js'
import { openSettings } from '../overlays/settings.js'

// Hermes history binds HERMES_HOME at module load. Hoisted isolation must precede those imports.
const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-native-prefs-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const views = new WeakMap<Surface, View>()

interface Fixture {
  read(session: string): Promise<SettingsGetResult>
  write(key: string, value: unknown, confirmed: boolean, session: string): Promise<unknown>
}

function field(type: string, value: unknown, extra: Partial<SettingsField> = {}): SettingsField {
  return { category: 'general', default: value, description: 'Fixture profile value', type, value, ...extra }
}

function prefs(surface: Surface) {
  const root = views.get(surface)?.regions[2]?.children.find(node => node.kind === 'prefs')

  if (!root) {
    throw new Error('Native preferences did not render')
  }

  return root
}

function row(surface: Surface, id: string) {
  const sections = prefs(surface).props.sections as { rows: { id: string; control: unknown; warning?: string; hint?: string }[] }[]
  const result = sections.flatMap(section => section.rows).find(item => item.id === id)

  if (!result) {
    throw new Error(`The preference row is absent: ${id}`)
  }

  return result
}

function change(surface: Surface, item: string, value: unknown) {
  const event = { ev: 'change', id: prefs(surface).id, item, raw: {}, sf: 'hermes', value } as TspEvent
  const action = surface.dispatch(event)

  if (!action) {
    throw new Error('Native preferences did not accept a change event')
  }

  return action
}

function click(surface: Surface, key: string) {
  const root = views.get(surface)?.regions[2]?.children[0]
  const target = root?.children.flatMap(node => node.children).flatMap(node => node.children).find(node => node.props.key === key)

  if (!target) {
    throw new Error(`The native action is absent: ${key}`)
  }

  const action = surface.dispatch({ act: 'click', ev: 'action', id: target.id, raw: {}, sf: 'hermes' })

  if (!action) {
    throw new Error(`The native action has no handler: ${key}`)
  }

  return action
}

async function withApp(fixture: Fixture, run: (app: App, surface: Surface, press: (bytes: string) => Promise<void>) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)

  if (!await connecting) {
    throw new Error('The unit SDK peer did not connect')
  }

  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    const p = params as { key: string; value: unknown; confirmed?: boolean; session_id: string }

    if (method === 'settings.get') {
      return fixture.read(p.session_id)
    }

    if (method === 'settings.set') {
      return fixture.write(p.key, p.value, p.confirmed === true, p.session_id)
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  app.info = { model: 'fixture-model', reasoning_effort: 'medium' }
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)

  surface.render = view => {
    views.set(surface, View.from(view))
    render(view)
  }

  try {
    await run(app, surface, async bytes => {
      input.emit('data', bytes)
      await rendered()
      await rendered()
    })
  } finally {
    app.quit()
    await running
  }
}

function profile(fields: Record<string, SettingsField>): SettingsGetResult {
  return { fields: structuredClone(fields), profile: 'fixture-profile' }
}

const escape = { alt: false, ctrl: false, meta: false, name: 'escape', shift: false } as const

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('native Settings', () => {
  it('coalesces duplicate commits, serializes new edits, and shows canonical profile values', async () => {
    const stored = { limit: field('number', 10), enabled: field('boolean', false) }
    const gate = Promise.withResolvers<void>()
    const writes: string[] = []
    let active = 0
    let maximum = 0

    const fixture: Fixture = {
      read: async () => profile(stored),
      write: async (key, value) => {
        active++
        maximum = Math.max(maximum, active)
        writes.push(key)

        if (key === 'limit') {
          await gate.promise
          // The authority clamps. An event echo would hide this distinction.
          stored.limit.value = Math.min(20, value as number)
        } else {
          stored.enabled.value = value
        }

        active--

        return { confirm_message: '', confirm_required: false, key, value }
      }
    }

    await withApp(fixture, async (app, surface, press) => {
      app.composer.set('draft with caret', 6)
      openSettings(app)
      await rendered()
      const first = change(surface, 'limit', 50)
      const duplicate = change(surface, 'limit', 50)
      await first()
      await duplicate()
      await change(surface, 'enabled', true)()
      gate.resolve()
      await rendered()
      await rendered()

      expect(writes).toEqual(['limit', 'enabled'])
      expect(maximum).toBe(1)
      expect(row(surface, 'limit').control).toMatchObject({ k: 'number', value: 20 })
      expect(row(surface, 'enabled').control).toMatchObject({ k: 'switch', on: true })
      // A second native commit of the pre-normalized draft must not write again.
      await change(surface, 'limit', 50)()
      await rendered()
      expect(writes).toEqual(['limit', 'enabled'])
      await press('\x1b[27u')
      await rendered()
      expect(app.composer.text).toBe('draft with caret')
      expect(app.composer.cursor).toBe(6)
    })
  })

  it('adopts canonical readback after a duplicate commit of an edit queued behind the same field', async () => {
    const stored = { limit: field('number', 2) }
    const gate = Promise.withResolvers<void>()
    let writes = 0

    const fixture: Fixture = {
      read: async () => profile(stored),
      write: async (key, value) => {
        writes++
        await gate.promise
        stored.limit.value = Math.min(20, value as number)

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface) => {
      openSettings(app)
      await rendered()
      await change(surface, 'limit', 5)()
      await change(surface, 'limit', 50)()
      await change(surface, 'limit', 50)()
      gate.resolve()
      await rendered()
      await rendered()
      expect(writes).toBe(2)
      expect(row(surface, 'limit').warning).toBeUndefined()
      expect(row(surface, 'limit').control).toMatchObject({ value: 20 })
    })
  })

  it('keeps partial numeric drafts visible without committing invalid input', async () => {
    const stored = { optional: field('number', null, { nullable: true }) }
    const writes: unknown[] = []

    const fixture: Fixture = {
      read: async () => profile(stored),
      write: async (key, value) => {
        writes.push(value)
        stored.optional.value = value

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface, press) => {
      openSettings(app)
      await rendered()
      await surface.dispatch({ ev: 'activate', id: prefs(surface).id, item: 'optional', raw: {}, sf: 'hermes' })?.()
      await press('\x1b[200~1e\x1b[201~')
      expect(row(surface, 'optional').control).toHaveProperty('value', '1e')
      expect(stored.optional.value).toBeNull()
      expect(writes).toEqual([])
      await press('\r')
      expect(row(surface, 'optional').warning).toBeTruthy()
      expect(row(surface, 'optional').control).toHaveProperty('value', '1e')
      expect(writes).toEqual([])
      await press('\x7f')
      expect(row(surface, 'optional').control).toHaveProperty('value', '1')
      await press('\r')
      await rendered()
      expect(stored.optional.value).toBe(1)
      expect(writes).toEqual([1])
      expect(row(surface, 'optional').warning).toBeUndefined()
    })
  })

  it('keeps invalid JSON visible, leaves nullable values untouched, and recovers a failed save', async () => {
    const stored = { rules: field('object', { allow: ['read'] }), optional: field('number', null, { nullable: true }) }
    let writes = 0
    let reject = true

    const fixture: Fixture = {
      read: async () => profile(stored),
      write: async (key, value) => {
        writes++

        if (reject) {
          reject = false
          throw new Error('Profile file is not writable')
        }

        stored[key as keyof typeof stored].value = value

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface) => {
      await localCommand('prefs')!.run(app, '')
      await rendered()
      await change(surface, 'rules', '[]')()
      await rendered()
      expect(row(surface, 'rules').warning).toBeTruthy()
      expect(row(surface, 'rules').control).toMatchObject({ k: 'text', value: '[]' })
      expect(writes).toBe(0)

      await change(surface, 'rules', '{"allow":["read","write"]}')()
      await rendered()
      expect(row(surface, 'rules').warning).toContain('not writable')
      await click(surface, 'retry')()
      await rendered()
      await rendered()
      expect(row(surface, 'rules').warning).toBeUndefined()
      expect(row(surface, 'rules').control).toMatchObject({ value: '{"allow":["read","write"]}' })
      expect(stored.optional.value).toBeNull()
      expect(writes).toBe(2)
    })
  })

  it('requires exact risk consent, cancels on Enter, and rejects a queued confirmation after cancel', async () => {
    const stored = { policy: field('boolean', false, { category: 'security' }) }
    let committed = 0

    const fixture: Fixture = {
      read: async () => profile(stored),
      write: async (key, value, confirmed) => {
        if (!confirmed) {
          return { confirm_message: 'This changes the profile policy.', confirm_required: true, key }
        }

        committed++
        stored.policy.value = value

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface, press) => {
      openSettings(app)
      await rendered()
      await change(surface, 'policy', true)()
      await rendered()
      const staleConfirm = click(surface, 'confirm')
      const texts = views.get(surface)?.regions[2]?.children[0]?.children[0]?.children.map(node => node.props.text)
      expect(texts).toContain('Setting: policy')
      expect(texts).toContain('true')
      expect(texts?.some(text => typeof text === 'string' && text.includes('fixture-profile'))).toBe(true)
      await press('\r')
      await staleConfirm()
      await rendered()
      expect(committed).toBe(0)
      expect(row(surface, 'policy').control).toMatchObject({ on: false })
      await change(surface, 'policy', true)()
      await rendered()
      await click(surface, 'confirm')()
      await rendered()
      expect(committed).toBe(1)
      expect(row(surface, 'policy').control).toMatchObject({ on: true })
    })
  })

  it('drops a late load and a retained native change when another session replaces the sheet', async () => {
    const first = Promise.withResolvers<SettingsGetResult>()
    let reads = 0
    let writes = 0

    const fixture: Fixture = {
      read: async () => ++reads === 1 ? first.promise : profile({ limit: field('number', 3) }),
      write: async () => { writes++; throw new Error('A stale setting must not reach the authority') }
    }

    await withApp(fixture, async (app, surface) => {
      openSettings(app)
      await rendered()
      const old = app.overlays.at(-1)!
      app.sid = 'session-2'
      app.info = { model: 'second-model', reasoning_effort: 'low' }
      openSettings(app)
      first.resolve(profile({ limit: field('number', 99) }))
      await rendered()
      await rendered()
      expect(app.overlays).not.toContain(old)
      expect(row(surface, 'limit').control).toMatchObject({ value: 3 })

      const queued = change(surface, 'limit', 4)
      const event = { ev: 'change', id: prefs(surface).id, item: 'limit', raw: {}, sf: 'hermes', value: 4 } as const
      openSettings(app)
      await rendered()
      await queued()
      await surface.dispatch(event)?.()
      await rendered()
      expect(writes).toBe(0)
      expect(row(surface, 'limit').control).toMatchObject({ value: 3 })
      expect(app.info).toMatchObject({ model: 'second-model', reasoning_effort: 'low' })
    })
  })

  it('retries an uncertain readback without replaying the acknowledged mutation', async () => {
    const stored = { limit: field('number', 2) }
    let reads = 0
    let writes = 0

    const fixture: Fixture = {
      read: async () => {
        if (++reads === 2) {
          throw new Error('Readback disconnected')
        }

        return profile(stored)
      },
      write: async (key, value) => {
        writes++
        stored.limit.value = value

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface) => {
      openSettings(app)
      await rendered()
      await change(surface, 'limit', 5)()
      await rendered()
      expect(row(surface, 'limit').warning).toContain('disconnected')
      await click(surface, 'retry')()
      await rendered()
      expect(writes).toBe(1)
      expect(row(surface, 'limit').warning).toBeUndefined()
      expect(row(surface, 'limit').control).toMatchObject({ value: 5 })
    })
  })

  it('keeps null and private values intact through untouched editors, and searches across profile pages', async () => {
    const stored = {
      optional: field('number', null, { description: 'Optional native count', nullable: true }),
      inherit: field('select', null, { nullable: true, options: ['none', 'low', 'high'] }),
      secret: field('string', null, { category: 'security', sensitive: true }),
      mode: field('select', 'safe', { category: 'security', options: ['safe', 'strict'] })
    }

    let writes = 0

    const fixture: Fixture = {
      read: async () => profile(stored),
      write: async () => { writes++; throw new Error('Untouched and invalid controls must not mutate the profile') }
    }

    await withApp(fixture, async (app, surface, press) => {
      openSettings(app)
      await rendered()
      await surface.dispatch({ ev: 'activate', id: prefs(surface).id, item: 'optional', raw: {}, sf: 'hermes' })?.()
      await press('\r')
      await rendered()
      await surface.dispatch({ ev: 'activate', id: prefs(surface).id, item: 'inherit', raw: {}, sf: 'hermes' })?.()
      await press('\r')
      await rendered()
      expect(row(surface, 'inherit').warning).toBeUndefined()
      await press('\x1b[200~secret\x1b[201~')
      await rendered()
      expect(prefs(surface).props.query).toBe('secret')
      expect(row(surface, 'secret').control).toMatchObject({ k: 'text', secret: true, value: '' })
      expect(row(surface, 'secret').hint).not.toContain('***')

      await surface.dispatch({ act: 'page', ev: 'action', id: prefs(surface).id, raw: {}, sf: 'hermes', value: 'profile.security' })?.()
      await rendered()
      expect(prefs(surface).props.page).toBe('profile.security')
      expect(prefs(surface).props.query).toBeUndefined()
      await surface.dispatch({ ev: 'activate', id: prefs(surface).id, item: 'secret', raw: {}, sf: 'hermes' })?.()
      await press('\r')
      await change(surface, 'mode', 'not-declared')()
      await rendered()
      expect(row(surface, 'mode').warning).toBeTruthy()
      expect(stored.optional.value).toBeNull()
      expect(stored.inherit.value).toBeNull()
      expect(stored.secret.value).toBeNull()
      expect(writes).toBe(0)
    })
  })

  it('does not dispatch queued edits or publish an old save into a different live session', async () => {
    const stored = {
      'session-1': { limit: field('number', 2), enabled: field('boolean', false) },
      'session-2': { limit: field('number', 8), enabled: field('boolean', false) }
    }

    const gate = Promise.withResolvers<void>()
    const owners: string[] = []

    const fixture: Fixture = {
      read: async session => profile(stored[session as keyof typeof stored]),
      write: async (key, value, _confirmed, session) => {
        owners.push(session)
        await gate.promise
        const target = stored[session as keyof typeof stored]
        target[key as keyof typeof target].value = value

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface) => {
      openSettings(app)
      await rendered()
      await change(surface, 'limit', 4)()
      await change(surface, 'enabled', true)()
      await rendered()
      app.sid = 'session-2'
      app.info = { model: 'second-model', reasoning_effort: 'low' }
      openSettings(app)
      gate.resolve()
      await rendered()
      await rendered()
      expect(owners).toEqual(['session-1'])
      expect(row(surface, 'limit').control).toMatchObject({ value: 8 })
      expect(row(surface, 'enabled').control).toMatchObject({ on: false })
      expect(stored['session-1'].enabled.value).toBe(false)
      expect(app.info).toEqual({ model: 'second-model', reasoning_effort: 'low' })
    })
  })

  it('keeps raw environment references visible until an explicit typed replacement', async () => {
    const stored = {
      enabled: field('boolean', '${FIXTURE_ENABLED}', { default: false }),
      timeout: field('number', '${FIXTURE_TIMEOUT}', { default: 60 })
    }

    const writes: unknown[] = []

    const fixture: Fixture = {
      read: async () => profile(stored),
      write: async (key, value) => {
        writes.push(value)
        stored[key as keyof typeof stored].value = value

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface, press) => {
      openSettings(app)
      await rendered()
      expect(row(surface, 'enabled').control).toMatchObject({ k: 'text', value: '${FIXTURE_ENABLED}' })
      expect(row(surface, 'timeout').control).toMatchObject({ k: 'text', value: '${FIXTURE_TIMEOUT}' })
      await surface.dispatch({ ev: 'activate', id: prefs(surface).id, item: 'enabled', raw: {}, sf: 'hermes' })?.()
      await press('\r')
      await rendered()
      expect(writes).toEqual([])
      await change(surface, 'enabled', 'false')()
      await change(surface, 'timeout', '42')()
      await rendered()
      await rendered()
      expect(writes).toEqual([false, 42])
      expect(row(surface, 'enabled').control).toMatchObject({ k: 'switch', on: false })
      expect(row(surface, 'timeout').control).toMatchObject({ k: 'number', value: 42 })
    })
  })

  it.each([5, null])('preserves an explicit reversion after acknowledged %s fails readback', async acknowledged => {
    const stored = { limit: field('number', 2, { default: null, nullable: true }) }
    const writes: unknown[] = []
    let reads = 0

    const fixture: Fixture = {
      read: async () => {
        if (++reads === 2) {
          throw new Error('Readback disconnected')
        }

        return profile(stored)
      },
      write: async (key, value) => {
        writes.push(value)
        stored.limit.value = value

        return { confirm_message: '', confirm_required: false, key }
      }
    }

    await withApp(fixture, async (app, surface) => {
      openSettings(app)
      await rendered()
      await change(surface, 'limit', acknowledged)()
      await rendered()
      expect(row(surface, 'limit').warning).toContain('disconnected')
      await change(surface, 'limit', 2)()
      await rendered()
      await rendered()
      expect(writes).toEqual([acknowledged, 2])
      expect(stored.limit.value).toBe(2)
      expect(row(surface, 'limit').control).toMatchObject({ k: 'number', value: 2 })
      expect(row(surface, 'limit').warning).toBeUndefined()
    })
  })
})
