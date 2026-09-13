import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getOverlayState, resetOverlayState } from '../app/overlayStore.js'
import { weatherApp, type WeatherState } from '../sdk/apps/index.js'
import { launchWidget } from '../sdk/host.js'
import type { WidgetInput } from '../sdk/types.js'

const key = (overrides: Partial<WidgetInput['key']> = {}, ch = ''): WidgetInput =>
  ({ ch, key: { ctrl: false, escape: false, return: false, ...overrides } }) as WidgetInput

const wttrReply = (weatherCode: string) => ({
  current_condition: [
    {
      FeelsLikeC: '20',
      humidity: '40',
      temp_C: '22',
      weatherCode,
      weatherDesc: [{ value: 'Sunny' }],
      windspeedKmph: '7'
    }
  ],
  nearest_area: [{ areaName: [{ value: 'Austin' }], country: [{ value: 'USA' }] }]
})

const activeState = () => getOverlayState().ambient.find(a => a.appId === 'weather')?.state as undefined | WeatherState

beforeEach(() => resetOverlayState())
afterEach(() => vi.unstubAllGlobals())

describe('weather reference app (async contract)', () => {
  it('launches into loading, lands the fetch via updateWidget', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ json: async () => wttrReply('113'), ok: true }))
    )

    expect(launchWidget('weather', 'Austin')).toBeNull()
    expect(activeState()?.phase.kind).toBe('loading')

    await vi.waitFor(() => expect(activeState()?.phase.kind).toBe('ready'))

    const phase = activeState()!.phase

    expect(phase).toMatchObject({ kind: 'ready', report: { area: 'Austin, USA', tempC: '22', weatherCode: 113 } })
  })

  it('a late resolution cannot resurrect a closed app', async () => {
    let resolve!: (value: unknown) => void

    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise(r => (resolve = r)))
    )

    launchWidget('weather', '')
    expect(activeState()?.phase.kind).toBe('loading')

    // Toggle closed while in flight (ambient dismissal), then resolve.
    expect(launchWidget('weather', '')).toBeNull()
    expect(getOverlayState().ambient).toEqual([])
    resolve({ json: async () => wttrReply('113'), ok: true })
    await new Promise(r => setTimeout(r, 0))

    expect(getOverlayState().ambient).toEqual([])
  })

  it('fetch failure lands as an error phase', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ json: async () => ({}), ok: false, status: 503 }))
    )

    launchWidget('weather', 'nowhere')
    await vi.waitFor(() => expect(activeState()?.phase.kind).toBe('error'))
    expect(activeState()?.phase).toMatchObject({ message: expect.stringContaining('503') })
  })

  it('r refreshes; Esc/q/Enter close', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ json: async () => wttrReply('113'), ok: true }))
    )

    const state: WeatherState = { location: 'x', phase: { kind: 'error', message: 'boom' } }

    expect(weatherApp.reduce(state, key({}, 'r'))).toMatchObject({ phase: { kind: 'loading' } })
    expect(weatherApp.reduce(state, key({ escape: true }))).toBeNull()
    expect(weatherApp.reduce(state, key({}, 'q'))).toBeNull()
    expect(weatherApp.reduce(state, key({ return: true }))).toBeNull()
  })
})

describe('weather reference app (relaunch race)', () => {
  const reply = (area: string, country: string, code: string) => ({
    current_condition: [
      {
        FeelsLikeC: '20',
        humidity: '40',
        temp_C: '22',
        weatherCode: code,
        weatherDesc: [{ value: 'Sunny' }],
        windspeedKmph: '7'
      }
    ],
    nearest_area: [{ areaName: [{ value: area }], country: [{ value: country }] }]
  })

  it('a stale resolution must not clobber the newer launch', async () => {
    let resolveParis!: (v: unknown) => void
    let resolveRome!: (v: unknown) => void

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('Paris')) {
          return new Promise(r => (resolveParis = r))
        }

        if (url.includes('Rome')) {
          return new Promise(r => (resolveRome = r))
        }

        throw new Error('unexpected url ' + url)
      })
    )

    expect(launchWidget('weather', 'Paris')).toBeNull()
    expect(launchWidget('weather', 'Rome')).toBeNull()
    expect(activeState()?.location).toBe('Rome')
    expect(activeState()?.phase.kind).toBe('loading')

    // Rome resolves first — the user sees correct Rome conditions.
    resolveRome({ json: async () => reply('Rome', 'Italy', '113'), ok: true })
    await vi.waitFor(() => expect(activeState()?.phase.kind).toBe('ready'))
    expect((activeState()!.phase as { kind: 'ready'; report: { area: string } }).report.area).toBe('Rome, Italy')

    // Paris, launched first but slower, resolves LAST. Expected: discarded.
    resolveParis({ json: async () => reply('Paris', 'France', '200'), ok: true })
    await new Promise(r => setTimeout(r, 0))

    const phase = activeState()!.phase as { kind: 'ready'; report: { area: string } }

    expect(phase.report.area).toBe('Rome, Italy')
    expect(activeState()?.location).toBe('Rome')
  })

  it('a stale rejection must not flip a ready slot to error', async () => {
    let rejectParis!: (e: unknown) => void
    let resolveRome!: (v: unknown) => void

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('Paris')) {
          return new Promise((_, rej) => (rejectParis = rej))
        }

        if (url.includes('Rome')) {
          return new Promise(r => (resolveRome = r))
        }

        throw new Error('unexpected url ' + url)
      })
    )

    expect(launchWidget('weather', 'Paris')).toBeNull()
    expect(launchWidget('weather', 'Rome')).toBeNull()
    expect(activeState()?.location).toBe('Rome')

    // Rome resolves successfully — the user sees correct Rome conditions.
    resolveRome({ json: async () => reply('Rome', 'Italy', '113'), ok: true })
    await vi.waitFor(() => expect(activeState()?.phase.kind).toBe('ready'))

    // Paris, launched first but slower, REJECTS. Expected: discarded — Rome stays ready.
    rejectParis(new DOMException('The operation was aborted due to timeout', 'TimeoutError'))
    await new Promise(r => setTimeout(r, 0))

    expect(activeState()?.phase.kind).toBe('ready')
    expect(activeState()?.location).toBe('Rome')
  })
})
