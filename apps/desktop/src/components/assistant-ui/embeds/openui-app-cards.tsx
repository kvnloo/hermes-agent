'use client'

import { defineComponent } from '@openuidev/react-lang'
import { z } from 'zod/v4'
import { useState, type CSSProperties, type ReactNode } from 'react'
import { useI18n } from '@/i18n/context'
import { useIsDark } from './use-is-dark'

import {
  BRANDS, appCardSchemas, brandForServer, cardPalette, cheapestRide, projectRoutePath,
  type BrandId
} from './openui-app-card-model'
import { OCTICONS, type OcticonName } from './openui-octicons'

type Ride = z.infer<typeof appCardSchemas.RideOptions>
type Mail = z.infer<typeof appCardSchemas.MailList>
type RouteData = z.infer<typeof appCardSchemas.Route>
type Pull = z.infer<typeof appCardSchemas.PullRequest>

function Icon({ name, color }: { name: OcticonName; color?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4 shrink-0" fill="currentColor" style={{ color }}>
      {OCTICONS[name].map(d => <path d={d} key={d} />)}
    </svg>
  )
}

function CardFrame({
  brand, title, children
}: { brand: BrandId | null; title: string; children: ReactNode }) {
  const dark = useIsDark()
  const palette = brand ? cardPalette(brand, dark) : null
  const style = palette ? {
    '--ac-surface': palette.surface,
    '--ac-alt': palette.surfaceAlt,
    '--ac-text': palette.text,
    '--ac-muted': palette.muted,
    '--ac-outline': palette.outline,
    '--ac-primary': palette.primary,
    '--ac-on-primary': palette.onPrimary,
    '--ac-accent': palette.accent,
    '--ac-success': palette.success,
    '--ac-warning': palette.warning,
    '--ac-danger': palette.danger,
    backgroundColor: palette.surface,
    color: palette.text,
    borderColor: palette.outline,
    borderRadius: palette.radius,
    fontFamily: brand === 'github' ? 'system-ui, sans-serif' : 'Arial, system-ui, sans-serif'
  } as CSSProperties : undefined
  return (
    <section
      aria-label={title}
      role="region"
      data-app-card-brand={brand ?? 'unknown'}
      className="min-w-0 overflow-hidden rounded-lg border border-(--ui-stroke-tertiary) bg-muted/20 text-foreground"
      style={style}
    >
      {children}
    </section>
  )
}

function BrandMark({ brand, fallback }: { brand: BrandId | null; fallback?: string }) {
  if (!brand) return <span className="truncate text-xs font-semibold text-muted-foreground">{fallback}</span>
  const info = BRANDS[brand]
  return (
    <span aria-hidden="true" className="grid size-7 shrink-0 place-items-center rounded-md text-xs font-bold"
      style={{ backgroundColor: info.color, color: info.onColor }}>
      {info.mark}
    </span>
  )
}

function OpenApp({ href, brand }: { href: string; brand: BrandId }) {
  const { t } = useI18n()
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className="inline-flex min-h-8 items-center rounded-full px-3 text-xs font-semibold hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2"
      style={{ background: 'var(--ac-primary)', color: 'var(--ac-on-primary)' }}>
      {t.openui.openApp.replace('{app}', BRANDS[brand].name)}
    </a>
  )
}

const RIDE_LINKS = { uber: 'https://m.uber.com/', lyft: 'https://ride.lyft.com/' } as const

function RideOptionsCard({ props }: { props: Ride }) {
  const { t } = useI18n()
  const candidate = brandForServer(props.app)
  const brand = candidate === 'uber' || candidate === 'lyft' ? candidate : null
  const appName = brand ? BRANDS[brand].name : props.app
  const best = cheapestRide(props.options)
  const [selected, setSelected] = useState(() => Math.max(0, props.options.findIndex(o => o.name === best)))
  const chosen = props.options[Math.min(selected, props.options.length - 1)]!
  return (
    <CardFrame brand={brand} title={appName + ' ride options, ' + props.pickup + ' to ' + props.dropoff}>
      <header className="flex items-center gap-3 px-4 py-3">
        <BrandMark brand={brand} fallback={props.app} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{props.dropoff}</p>
          <p className="truncate text-xs" style={{ color: 'var(--ac-muted, currentColor)' }}>{props.pickup}</p>
        </div>
      </header>
      <div className="px-2 pb-2">
        {props.options.map((option, i) => (
          <button type="button" key={option.name} aria-pressed={selected === i}
            aria-label={option.name + ', ' + option.minutes + ' min, ' + option.price + ', ' + option.seats + ' ' + t.openui.seats}
            onClick={() => setSelected(i)}
            className="flex min-h-14 w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:opacity-80"
            style={{ background: selected === i ? 'var(--ac-alt, var(--ui-fill-secondary))' : undefined,
              outline: selected === i ? '1px solid var(--ac-outline, currentColor)' : undefined }}>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{option.name}</span>
              <span className="text-xs" style={{ color: 'var(--ac-muted, currentColor)' }}>
                {option.minutes} min · {option.seats} {t.openui.seats}
                {option.arrival ? ' · ' + option.arrival : ''}
              </span>
            </span>
            {option.name === best && <span className="shrink-0 text-xs" style={{ color: 'var(--ac-success, currentColor)' }}>{t.openui.bestPrice}</span>}
            <span className="shrink-0 font-semibold tabular-nums">{option.price}</span>
          </button>
        ))}
      </div>
      <footer className="flex items-center justify-between gap-3 border-t px-4 py-2.5 text-xs" style={{ borderColor: 'var(--ac-outline, currentColor)' }}>
        <span style={{ color: 'var(--ac-muted, currentColor)' }}>{chosen.name} · {t.openui.readOnly}</span>
        {brand ? <OpenApp brand={brand} href={RIDE_LINKS[brand]} /> : null}
      </footer>
    </CardFrame>
  )
}

function MailListCard({ props }: { props: Mail }) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState<number | null>(null)
  return (
    <CardFrame brand="gmail" title={'Gmail results for ' + props.query}>
      <header className="flex items-center gap-3 px-4 py-3">
        <BrandMark brand="gmail" />
        <span className="min-w-0 flex-1 truncate text-sm font-semibold">{props.query}</span>
        <span className="text-xs tabular-nums" style={{ color: 'var(--ac-muted)' }}>{props.messages.length}</span>
      </header>
      {props.messages.length === 0 && <p className="px-4 pb-3 text-xs">{t.openui.noMessages}</p>}
      <ul className="m-0 list-none p-0">
        {props.messages.map((message, i) => (
          <li className="list-none border-t" key={i} style={{ borderColor: 'var(--ac-outline)' }}>
            <button type="button" aria-expanded={expanded === i} onClick={() => setExpanded(expanded === i ? null : i)}
              className="flex w-full items-start gap-3 px-4 py-2.5 text-left hover:opacity-85"
              style={{ background: message.unread ? 'var(--ac-surface)' : 'var(--ac-alt)' }}>
              <span aria-hidden="true" className="grid size-8 shrink-0 place-items-center rounded-full text-xs font-semibold text-white"
                style={{ background: BRANDS.gmail.color }}>{message.from.charAt(0).toUpperCase()}</span>
              <span className="min-w-0 flex-1 text-sm">
                <span className={'block truncate ' + (message.unread ? 'font-bold' : 'font-medium')}>{message.from}</span>
                <span className={'block truncate ' + (message.unread ? 'font-semibold' : '')}>{message.subject}</span>
                <span className={expanded === i ? 'block whitespace-pre-wrap text-xs' : 'block truncate text-xs'}
                  style={{ color: 'var(--ac-muted)' }}>{message.snippet}</span>
                {expanded === i && message.attachment && <span className="mt-1 block text-xs">{message.attachment}</span>}
              </span>
              <span className="shrink-0 text-xs" style={{ color: 'var(--ac-muted)' }}>{message.time}</span>
            </button>
          </li>
        ))}
      </ul>
      <footer className="flex items-center justify-between gap-2 border-t px-4 py-2.5" style={{ borderColor: 'var(--ac-outline)' }}>
        <span className="text-xs" style={{ color: 'var(--ac-muted)' }}>{t.openui.readOnly}</span>
        <OpenApp brand="gmail" href={'https://mail.google.com/mail/u/0/#search/' + encodeURIComponent(props.query)} />
      </footer>
    </CardFrame>
  )
}

const MAPS_MODE = { drive: 'driving', walk: 'walking', transit: 'transit', bike: 'bicycling' } as const
const MAP_WIDTH = 400
const MAP_HEIGHT = 180

function RouteMap({ props }: { props: RouteData }) {
  if (!props.path) return null
  const route = projectRoutePath(props.path, MAP_WIDTH, MAP_HEIGHT, props.map?.bounds)
  const start = route.points[0]!
  const end = route.points[route.points.length - 1]!
  return (
    <svg role="img" aria-label={props.origin + ' to ' + props.destination}
      viewBox={'0 0 ' + MAP_WIDTH + ' ' + MAP_HEIGHT} className="block h-auto max-h-56 w-full"
      style={{ background: 'var(--ac-alt)' }}>
      <path d={route.d} fill="none" stroke="var(--ac-outline)" strokeWidth={7} strokeLinejoin="round" strokeLinecap="round" />
      <path d={route.d} fill="none" stroke="var(--ac-accent)" strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={start[0]} cy={start[1]} r={5} stroke="var(--ac-text)" strokeWidth={2} fill="var(--ac-surface)" />
      <circle cx={end[0]} cy={end[1]} r={6} fill="var(--ac-primary)" />
    </svg>
  )
}

function RouteCard({ props }: { props: RouteData }) {
  const { t } = useI18n()
  const [index, setIndex] = useState(0)
  const active = Math.min(index, props.steps.length - 1)
  const mode = {
    drive: t.openui.drive, walk: t.openui.walk, transit: t.openui.transit, bike: t.openui.bike
  }[props.mode]
  const query = 'origin=' + encodeURIComponent(props.origin) +
    '&destination=' + encodeURIComponent(props.destination) + '&travelmode=' + MAPS_MODE[props.mode]
  return (
    <CardFrame brand="google-maps" title={'Directions from ' + props.origin + ' to ' + props.destination}>
      <header className="flex items-center gap-3 px-4 py-3">
        <BrandMark brand="google-maps" />
        <div className="min-w-0 flex-1 truncate text-sm font-semibold">{props.origin} → {props.destination}</div>
      </header>
      <div className="flex flex-wrap items-center gap-3 px-4 pb-3 text-sm">
        <span className="font-semibold">{mode}</span>
        <strong className="text-lg tabular-nums" style={{ color: 'var(--ac-success)' }}>{props.minutes} min</strong>
        <span style={{ color: 'var(--ac-muted)' }}>{props.distance}{props.via ? ' · ' + props.via : ''}</span>
      </div>
      <RouteMap props={props} />
      {props.steps.length > 0 && (
        <div className="flex items-center gap-2 border-t px-4 py-3 text-sm" style={{ borderColor: 'var(--ac-outline)' }}>
          <button type="button" aria-label={t.openui.previousStep} disabled={active === 0} onClick={() => setIndex(active - 1)}
            className="rounded-md px-2 py-1 disabled:opacity-30">‹</button>
          <p role="status" className="min-w-0 flex-1">{props.steps[active]}</p>
          <span className="shrink-0 text-xs tabular-nums">{active + 1}/{props.steps.length}</span>
          <button type="button" aria-label={t.openui.nextStep} disabled={active === props.steps.length - 1}
            onClick={() => setIndex(active + 1)} className="rounded-md px-2 py-1 disabled:opacity-30">›</button>
        </div>
      )}
      <footer className="flex items-center justify-between gap-3 border-t px-4 py-2.5" style={{ borderColor: 'var(--ac-outline)' }}>
        <span className="text-xs" style={{ color: 'var(--ac-muted)' }}>{t.openui.readOnly}</span>
        <OpenApp brand="google-maps" href={'https://www.google.com/maps/dir/?api=1&' + query} />
      </footer>
    </CardFrame>
  )
}

const STATUS_ICONS = {
  pass: 'check-circle-fill',
  fail: 'x-circle-fill',
  running: 'git-pull-request',
  skip: 'skip'
} as const satisfies Record<Pull['checks'][number]['status'], OcticonName>

function PullRequestCard({ props }: { props: Pull }) {
  const { t } = useI18n()
  const [expanded, setExpanded] = useState<number | null>(null)
  const checksPassed = props.checks.every(check => check.status === 'pass' || check.status === 'skip')
  const summary = props.state === 'conflict'
    ? t.openui.conflictCount.replace('{count}', String(props.conflicts))
    : props.state === 'ready' && checksPassed ? t.openui.checksPassed : props.state
  return (
    <CardFrame brand="github" title={'Pull request ' + props.number + ', ' + props.state}>
      <header className="flex items-start gap-3 px-4 py-3">
        <BrandMark brand="github" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">{props.title} <span style={{ color: 'var(--ac-muted)' }}>#{props.number}</span></p>
          <p className="mt-1 break-words text-xs" style={{ color: 'var(--ac-muted)' }}>{props.head} → {props.base}</p>
        </div>
        <span className="inline-flex items-center gap-1 text-xs" style={{ color: props.state === 'merged' ? 'var(--ac-accent)' : 'var(--ac-success)' }}>
          <Icon name={props.state === 'merged' ? 'git-merge' : 'git-pull-request'} />{props.state}
        </span>
      </header>
      {props.commits && props.commits.length > 0 && (
        <ol className="m-0 list-none border-t p-0" style={{ borderColor: 'var(--ac-outline)' }}>
          {props.commits.map(commit => (
            <li key={commit.sha} className="flex min-w-0 items-center gap-3 px-4 py-2 text-xs" style={{
              background: commit.conflict ? 'var(--ac-alt)' : undefined
            }}>
              <span aria-hidden="true" className="size-2 shrink-0 rounded-full" style={{
                background: commit.lane === 'head' ? 'var(--ac-accent)' : 'var(--ac-muted)'
              }} />
              <span className="min-w-0 flex-1 truncate">{commit.title}</span>
              <code className="shrink-0">{commit.sha.slice(0, 7)}</code>
              <span className="hidden shrink-0 sm:inline" style={{ color: 'var(--ac-muted)' }}>{commit.author} · {commit.age}</span>
            </li>
          ))}
        </ol>
      )}
      <ul className="m-0 list-none border-t p-0" style={{ borderColor: 'var(--ac-outline)' }}>
        {props.checks.map((check, i) => (
          <li className="list-none" key={i}>
            <button type="button" disabled={!check.detail} aria-expanded={Boolean(check.detail) ? expanded === i : undefined}
              onClick={() => setExpanded(expanded === i ? null : i)}
              className="flex w-full items-center gap-2 px-4 py-2 text-left text-xs disabled:cursor-default">
              <Icon name={STATUS_ICONS[check.status]} color={
                check.status === 'pass' ? 'var(--ac-success)' :
                check.status === 'fail' ? 'var(--ac-danger)' :
                check.status === 'running' ? 'var(--ac-warning)' : 'var(--ac-muted)'
              } />
              <span className="min-w-0 flex-1 truncate font-semibold">{check.name}</span>
              <span className="shrink-0" style={{ color: 'var(--ac-muted)' }}>{check.status}</span>
              {check.seconds !== undefined && <span className="shrink-0 tabular-nums" style={{ color: 'var(--ac-muted)' }}>
                {Math.round(check.seconds)}s
              </span>}
            </button>
            {expanded === i && check.detail && (
              <p role="status" className="mx-4 mb-2 whitespace-pre-wrap text-xs" style={{ color: 'var(--ac-muted)' }}>{check.detail}</p>
            )}
          </li>
        ))}
      </ul>
      <footer className="flex items-center justify-between gap-3 border-t px-4 py-2.5" style={{ borderColor: 'var(--ac-outline)' }}>
        <span className="min-w-0 text-xs" style={{ color: 'var(--ac-muted)' }}>{summary}</span>
        <OpenApp brand="github" href={props.url ?? 'https://github.com/pulls'} />
      </footer>
    </CardFrame>
  )
}

export const RideOptions = defineComponent({
  name: 'RideOptions',
  description: 'Read-only ride prices supplied by the connector; no booking.',
  props: appCardSchemas.RideOptions,
  component: ({ props }) => <RideOptionsCard props={props} />
})
export const MailList = defineComponent({
  name: 'MailList',
  description: 'Read-only Gmail search results, with local message preview.',
  props: appCardSchemas.MailList,
  component: ({ props }) => <MailListCard props={props} />
})
export const Route = defineComponent({
  name: 'Route',
  description: 'Read-only Google Maps directions, supplied steps and optional real geometry.',
  props: appCardSchemas.Route,
  component: ({ props }) => <RouteCard props={props} />
})
export const PullRequest = defineComponent({
  name: 'PullRequest',
  description: 'Read-only GitHub PR checks and commit status; no merge or actions.',
  props: appCardSchemas.PullRequest,
  component: ({ props }) => <PullRequestCard props={props} />
})
