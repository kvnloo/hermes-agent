import { z } from 'zod/v4'

// Derived from the T3 Code OpenUI app-card experiment by Kevin Rajan.
// Keep the connector payload bounded and the renderer free of tool actions.
const LIMITS = {
  text: 200, snippet: 400, price: 24, options: 8, messages: 20,
  steps: 20, checks: 12, commits: 12, points: 600, minutes: 100_000
} as const

const text = z.string().max(LIMITS.text)
const name = z.string().min(1).max(LIMITS.text)
const minutes = z.number().finite().min(0).max(LIMITS.minutes)
const latitude = z.number().finite().min(-90).max(90)
const longitude = z.number().finite().min(-180).max(180)
const seconds = z.number().finite().min(0).max(LIMITS.minutes * 60)

export const rideOptionsProps = z.object({
  // Unrecognized ride connectors retain a plain, non-linking card.
  app: z.string().min(1).max(40),
  pickup: name,
  dropoff: name,
  options: z.array(z.object({
    name,
    minutes,
    price: z.string().min(1).max(LIMITS.price),
    seats: z.number().int().min(1).max(20),
    arrival: text.optional()
  })).min(1).max(LIMITS.options)
})

export const mailListProps = z.object({
  query: text,
  messages: z.array(z.object({
    from: name,
    subject: text,
    snippet: z.string().max(LIMITS.snippet),
    time: text,
    unread: z.boolean(),
    attachment: text.optional()
  })).max(LIMITS.messages)
})

export const routeProps = z.object({
  origin: name,
  destination: name,
  mode: z.enum(['drive', 'walk', 'transit', 'bike']),
  minutes,
  distance: text,
  steps: z.array(name).max(LIMITS.steps),
  via: text.optional(),
  path: z.array(z.tuple([latitude, longitude])).min(2).max(LIMITS.points).optional(),
  map: z.object({
    image: z.url({ protocol: /^https?$/ }).max(2_000),
    bounds: z.tuple([latitude, longitude, latitude, longitude])
  }).optional()
})

export const pullRequestProps = z.object({
  number: z.number().int().min(1),
  title: name,
  state: z.enum(['open', 'conflict', 'ready', 'merged', 'closed']),
  head: name,
  base: name,
  checks: z.array(z.object({
    name,
    status: z.enum(['pass', 'fail', 'running', 'skip']),
    detail: text,
    started: seconds.optional(),
    seconds: seconds.optional()
  })).max(LIMITS.checks),
  conflicts: z.number().int().min(0).max(10_000),
  commits: z.array(z.object({
    title: name,
    sha: z.string().min(4).max(12),
    author: name,
    age: text,
    lane: z.enum(['base', 'head', 'side']),
    branch: text.optional(),
    conflict: z.boolean().optional()
  })).max(LIMITS.commits).optional(),
  // The source demo has no repository identity. A real direct PR URL is optional.
  url: z.url({ protocol: /^https$/ }).max(2_000).optional()
})

export const appCardSchemas = {
  RideOptions: rideOptionsProps,
  MailList: mailListProps,
  Route: routeProps,
  PullRequest: pullRequestProps
} as const

export type AppCardType = keyof typeof appCardSchemas
export const isAppCardType = (s: string): s is AppCardType => Object.hasOwn(appCardSchemas, s)

export function appCardProblem(panel: { typeName: string; props: unknown }): string | null {
  if (panel.typeName === 'RideOptions') {
    const ride = rideOptionsProps.safeParse(panel.props)

    if (!ride.success) {return 'Invalid ride options'}
    const names = ride.data.options.map(option => option.name)

    return new Set(names).size === names.length ? null : 'Duplicate ride option'
  }

  if (panel.typeName === 'PullRequest') {
    const pr = pullRequestProps.safeParse(panel.props)

    if (!pr.success) {return 'Invalid pull request'}
    const { state, checks, conflicts, url, number } = pr.data

    if (state === 'conflict' && conflicts < 1) {return 'Conflict count required'}

    if (!['open', 'conflict'].includes(state) && conflicts !== 0) {return 'Inconsistent conflicts'}

    if (state === 'ready' && checks.some(c => c.status === 'fail' || c.status === 'running')) {
      return 'Checks have not passed'
    }

    if (url) {
      const parsed = new URL(url)
      const match = /^\/[^/]+\/[^/]+\/pull\/([1-9]\d*)\/?$/.exec(parsed.pathname)

      if (parsed.hostname !== 'github.com' || parsed.port || parsed.username || parsed.password ||
          parsed.search || parsed.hash || !match || Number(match[1]) !== number) {
        return 'Pull request URL does not match its number'
      }
    }
  }

  return null
}

export type BrandId = 'uber' | 'lyft' | 'gmail' | 'google-maps' | 'github'
export const BRANDS: Readonly<Record<BrandId, { name: string; mark: string; color: string; onColor: string }>> = {
  uber: { name: 'Uber', mark: 'U', color: '#000000', onColor: '#ffffff' },
  lyft: { name: 'Lyft', mark: 'L', color: '#ff00bf', onColor: '#ffffff' },
  gmail: { name: 'Gmail', mark: 'M', color: '#ea4335', onColor: '#ffffff' },
  'google-maps': { name: 'Google Maps', mark: '◆', color: '#188038', onColor: '#ffffff' },
  github: { name: 'GitHub', mark: 'GH', color: '#24292f', onColor: '#ffffff' }
}

// Adapted from T3 appConnectors; no connector API or credentials are called.
export function brandForServer(server: string): BrandId | null {
  const key = server.replace(/^mcp__/, '').toLowerCase().replace(/[\s-]+/g, '_')
    .replace(/^editor_(.+?)_[0-9a-f]{8}$/, '$1').replace(/[^a-z0-9]/g, '')

  if (['uber', 'uberrides'].includes(key)) {return 'uber'}

  if (key === 'lyft') {return 'lyft'}

  if (['gmail', 'googlegmail', 'gwsgmail', 'googlemail'].includes(key)) {return 'gmail'}

  if (['googlemaps', 'gmaps', 'maps'].includes(key)) {return 'google-maps'}

  if (['github', 'gh'].includes(key)) {return 'github'}

  return null
}

export interface Palette {
  surface: string; surfaceAlt: string; text: string; muted: string
  outline: string; primary: string; onPrimary: string; accent: string
  success: string; danger: string; warning: string; radius: number
}

// Brand palettes follow T3's Material 3 (Gmail/Maps), Base Web (Uber/Lyft)
// and Primer (GitHub) tokens. Font assets are not bundled: system fallbacks only.
const google = {
  light: { surface: '#ffffff', surfaceAlt: '#f2f6fc', text: '#1f1f1f',
    muted: '#444746', outline: '#c4c7c5', primary: '#0b57d0',
    onPrimary: '#ffffff', accent: '#0b57d0', success: '#188038',
    danger: '#b3261e', warning: '#b06000', radius: 16 },
  dark: { surface: '#1e1f20', surfaceAlt: '#282a2c', text: '#e3e3e3',
    muted: '#c4c7c5', outline: '#444746', primary: '#a8c7fa',
    onPrimary: '#062e6f', accent: '#a8c7fa', success: '#6dd58c',
    danger: '#f2b8b5', warning: '#fdd663', radius: 16 }
} as const

const uber = {
  light: { surface: '#ffffff', surfaceAlt: '#f3f3f3', text: '#000000',
    muted: '#5e5e5e', outline: '#e8e8e8', primary: '#000000',
    onPrimary: '#ffffff', accent: '#276ef1', success: '#0e8345',
    danger: '#de1135', warning: '#9f6402', radius: 12 },
  dark: { surface: '#161616', surfaceAlt: '#292929', text: '#dedede',
    muted: '#ababab', outline: '#383838', primary: '#dedede',
    onPrimary: '#000000', accent: '#5e8bdb', success: '#5c9d70',
    danger: '#de5b5d', warning: '#f6bc2f', radius: 12 }
} as const

const github = {
  light: { surface: '#ffffff', surfaceAlt: '#f6f8fa', text: '#1f2328',
    muted: '#59636e', outline: '#d1d9e0', primary: '#1f883d',
    onPrimary: '#ffffff', accent: '#0969da', success: '#1a7f37',
    danger: '#d1242f', warning: '#9a6700', radius: 12 },
  dark: { surface: '#0d1117', surfaceAlt: '#151b23', text: '#f0f6fc',
    muted: '#9198a1', outline: '#3d444d', primary: '#238636',
    onPrimary: '#ffffff', accent: '#4493f8', success: '#3fb950',
    danger: '#f85149', warning: '#d29922', radius: 12 }
} as const

export function cardPalette(brand: BrandId, dark: boolean): Palette {
  if (brand === 'github') {return github[dark ? 'dark' : 'light']}

  if (brand === 'gmail' || brand === 'google-maps') {return google[dark ? 'dark' : 'light']}

  if (brand === 'lyft') {
    const base = uber[dark ? 'dark' : 'light']

    return { ...base, primary: '#ff00bf', onPrimary: '#ffffff',
      accent: dark ? '#ff5fd5' : '#ff00bf' }
  }

  return uber[dark ? 'dark' : 'light']
}

export function cheapestRide(options: ReadonlyArray<{ name: string; price: string }>): string | null {
  let best: { name: string; price: number } | null = null

  for (const option of options) {
    const price = Number(option.price.replace(/[^0-9.]/g, ''))

    if (Number.isFinite(price) && /[0-9]/.test(option.price) &&
        (!best || price < best.price)) {best = { name: option.name, price }}
  }

  return best?.name ?? null
}

export function projectRoutePath(
  path: ReadonlyArray<readonly [number, number]>,
  width: number,
  height: number,
  bounds?: readonly [number, number, number, number]
) {
  if (!path.length) {return { points: [] as [number, number][], d: '' }}
  // Clamp to Web Mercator's defined latitude range; source values remain unchanged.
  const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + Math.max(-85, Math.min(85, lat)) * Math.PI / 360))
  const xs = path.map(([, lon]) => lon * Math.PI / 180)
  const ys = path.map(([lat]) => merc(lat))

  const [x0, x1, y0, y1] = bounds
    ? [bounds[1] * Math.PI / 180, bounds[3] * Math.PI / 180, merc(bounds[0]), merc(bounds[2])]
    : [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]

  const inset = bounds ? 0 : 22

  const span = Math.max((x1 - x0) / (width - inset * 2),
    (y1 - y0) / (height - inset * 2)) || 1

  const cx = (x0 + x1) / 2
  const cy = (y0 + y1) / 2

  const points = xs.map((x, i): [number, number] => [
    Math.round(((x - cx) / span + width / 2) * 10) / 10,
    Math.round(((cy - ys[i]!) / span + height / 2) * 10) / 10
  ])

  return { points, d: 'M' + points.map(([x, y]) => x + ' ' + y).join(' L') }
}
