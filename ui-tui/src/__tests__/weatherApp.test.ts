import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getOverlayState, resetOverlayState } from '../app/overlayStore.js'
import { weatherApp, type WeatherState } from '../sdk/apps/index.js'
import { launchWidget } from '../sdk/host.js'
import type { WidgetInput } from '../sdk/types.js'

const key = (overrides: Partial<WidgetInput['key']> = {}, ch = ''): WidgetInput =>
  ({ ch, key: { ctrl: false, escape: false, return: false, ...overrides } }) as WidgetInput

const ipGeoReply = {
  city: 'Cascais',
  country: 'Portugal',
  latitude: 38.6968,
  longitude: -9.4215,
  success: true,
  timezone: { id: 'Europe/Lisbon' }
}

const openMeteoForecast = {
  current: {
    apparent_temperature: 20,
    relative_humidity_2m: 40,
    temperature_2m: 22,
    weather_code: 0,
    wind_speed_10m: 7
  }
}

const activeState = () => getOverlayState().ambient.find(a => a.appId === 'weather')?.state as undefined | WeatherState

beforeEach(() => resetOverlayState())
afterEach(() => vi.unstubAllGlobals())

describe('weather reference app (async contract)', () => {
  it('uses Open-Meteo for a named location', async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = String(input)

      if (url.startsWith('https://geocoding-api.open-meteo.com/')) {
        return {
          json: async () => ({
            results: [
              { country: 'USA', latitude: 30.2672, longitude: -97.7431, name: 'Austin', timezone: 'America/Chicago' }
            ]
          }),
          ok: true
        }
      }

      if (url.startsWith('https://api.open-meteo.com/')) {
        return { json: async () => openMeteoForecast, ok: true }
      }

      throw new Error(`unexpected weather URL: ${url}`)
    })

    vi.stubGlobal('fetch', fetchMock)

    launchWidget('weather', 'Austin')
    await vi.waitFor(() => expect(activeState()?.phase.kind).toBe('ready'))

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(activeState()?.phase).toMatchObject({
      kind: 'ready',
      report: { area: 'Austin, USA', condition: 'Clear sky', tempC: '22', weatherCode: 0 }
    })
  })

  it('geolocates by IP when the location is blank', async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = String(input)

      if (url.startsWith('https://ipwho.is/')) {
        return {
          json: async () => ipGeoReply,
          ok: true
        }
      }

      if (url.startsWith('https://api.open-meteo.com/')) {
        return { json: async () => openMeteoForecast, ok: true }
      }

      throw new Error(`unexpected weather URL: ${url}`)
    })

    vi.stubGlobal('fetch', fetchMock)

    launchWidget('weather', '')
    await vi.waitFor(() => expect(activeState()?.phase.kind).toBe('ready'))

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(activeState()?.phase).toMatchObject({
      kind: 'ready',
      report: { area: 'Cascais, Portugal', tempC: '22' }
    })
  })

  it('a late resolution cannot resurrect a closed app', async () => {
    let resolveForecast!: (value: unknown) => void

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ json: async () => ipGeoReply, ok: true })
      .mockImplementationOnce(() => new Promise(resolve => (resolveForecast = resolve)))

    vi.stubGlobal('fetch', fetchMock)

    launchWidget('weather', '')
    expect(activeState()?.phase.kind).toBe('loading')
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))

    // Toggle closed while the final forecast is in flight, then complete it.
    expect(launchWidget('weather', '')).toBeNull()
    expect(getOverlayState().ambient).toEqual([])
    resolveForecast({ json: async () => openMeteoForecast, ok: true })
    await new Promise(resolve => setTimeout(resolve, 0))

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

    // Geocoding succeeds at the HTTP level but matches nothing: surfaced as an error, not a hang.
    resetOverlayState()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ json: async () => ({ results: [] }), ok: true }))
    )

    launchWidget('weather', 'nowhere')
    await vi.waitFor(() => expect(activeState()?.phase.kind).toBe('error'))
    expect(activeState()?.phase).toMatchObject({ message: expect.stringContaining('location not found') })
  })

  it('r refreshes; Esc/q/Enter close', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ json: async () => ipGeoReply, ok: true }))
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
