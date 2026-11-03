import { createParser } from '@openuidev/lang-core'
import { createLibrary, defineComponent, Renderer } from '@openuidev/react-lang'
import { z } from 'zod/v4'
import { appCardProblem, appCardSchemas, isAppCardType } from './openui-app-card-model'
import { RideOptions, MailList, Route, PullRequest } from './openui-app-cards'

// Ported from the T3 Code OpenUI experiment. The small, read-only Desktop
// catalog excludes treemaps, heatmaps and actions; app cards stay read-only.
const LIMITS = {
  bytes: 65_536,
  panels: 8,
  categories: 60,
  series: 8
} as const

const title = z.string().min(1).max(200)
const summary = z.string().max(4_000)
const label = z.string().min(1).max(100)
const unit = z.string().max(40)
const value = z.number().finite().min(0).max(1e12)
const metricProps = z.object({
  title,
  metrics: z.array(z.object({ label, value: z.string().max(200) })).min(1).max(12)
})
const barProps = z.object({
  title,
  unit,
  bars: z.array(z.object({ label, value })).min(1).max(30)
})
const seriesItem = z.object({
  name: label,
  values: z.array(value).min(1).max(LIMITS.categories)
})
// OpenUI tags component schemas by identity: shared Zod objects alias refs.
// Give each series chart its own top-level schema, keeping the same constraints.
const createSeriesProps = () => z.object({
  title,
  unit,
  categories: z.array(label).min(2).max(LIMITS.categories),
  series: z.array(seriesItem).min(1).max(LIMITS.series)
})
const stackedBarProps = createSeriesProps()
const stackedAreaProps = createSeriesProps()
const lineChartProps = createSeriesProps()
const tableProps = z.object({
  title,
  columns: z.array(label).min(1).max(12),
  rows: z.array(z.array(z.string().max(2_000)).max(12)).max(200)
})

const formatCount = (n: number) =>
  n.toLocaleString('en-US', { maximumFractionDigits: 2 })

// Every series uses an existing skin token, never a T3 palette literal.
const SERIES_TONE = [
  'text-primary',
  'text-foreground',
  'text-muted-foreground',
  'text-destructive',
  'text-primary/60',
  'text-foreground/60',
  'text-muted-foreground/65',
  'text-destructive/65'
] as const

interface SeriesEntry {
  name: string
  values: number[]
}

interface SeriesData {
  categories: string[]
  series: SeriesEntry[]
  title: string
  unit: string
}

function Legend({ series }: { series: SeriesEntry[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {series.map((entry, index) => (
        <span className="inline-flex items-center gap-1.5" key={index}>
          <span aria-hidden className={`inline-block size-2 rounded-sm bg-current ${SERIES_TONE[index]}`} />
          {entry.name}
        </span>
      ))}
    </div>
  )
}

function SeriesValues({ props }: { props: SeriesData }) {
  return (
    <div className="overflow-x-auto" role="region" aria-label={`${props.title} values`} tabIndex={0}>
      <table className="w-full border-collapse text-left text-xs tabular-nums">
        <thead>
          <tr>
            <th className="border-b border-(--ui-stroke-tertiary) px-2 py-1.5" scope="col" />
            {props.categories.map((category, i) => (
              <th className="border-b border-(--ui-stroke-tertiary) px-2 py-1.5" key={i} scope="col">{category}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.series.map((entry, i) => (
            <tr key={i}>
              <th className="border-b border-(--ui-stroke-tertiary) px-2 py-1.5 font-medium" scope="row">{entry.name}</th>
              {entry.values.map((number, j) => (
                <td className="border-b border-(--ui-stroke-tertiary) px-2 py-1.5" key={j}>
                  {formatCount(number)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const Stat = defineComponent({
  name: 'Stat',
  description: 'Read-only labeled values. Use supplied strings, without inventing numbers.',
  props: metricProps,
  component: ({ props }) => (
    <section aria-label={props.title} className="space-y-2">
      <h4 className="text-sm font-semibold">{props.title}</h4>
      <dl className="grid grid-cols-2 gap-x-5 gap-y-3 sm:grid-cols-3">
        {props.metrics.map((metric, i) => (
          <div className="min-w-0 border-t border-(--ui-stroke-tertiary) pt-2" key={i}>
            <dt className="text-xs text-muted-foreground">{metric.label}</dt>
            <dd className="break-words text-base font-semibold tabular-nums">{metric.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
})

const BarChart = defineComponent({
  name: 'BarChart',
  description: 'Horizontal bars with non-negative raw values.',
  props: barProps,
  component: ({ props }) => {
    const max = Math.max(1, ...props.bars.map(bar => bar.value))
    return (
      <section aria-label={props.title} className="space-y-2">
        <h4 className="text-sm font-semibold">{props.title}</h4>
        <ul className="space-y-2 text-xs">
          {props.bars.map((bar, i) => (
            <li className="grid grid-cols-[minmax(0,8rem)_minmax(0,1fr)_auto] items-center gap-2" key={i}>
              <span className="truncate" title={bar.label}>{bar.label}</span>
              <span aria-label={`${bar.label}: ${formatCount(bar.value)} ${props.unit}`} className="h-2 overflow-hidden rounded-sm bg-muted" role="meter" aria-valuemin={0} aria-valuemax={max} aria-valuenow={bar.value}>
                <span className="block h-full bg-primary" style={{ width: `${(bar.value / max) * 100}%` }} />
              </span>
              <span className="text-right font-medium tabular-nums">{formatCount(bar.value)}</span>
            </li>
          ))}
        </ul>
        {props.unit && <p className="text-xs text-muted-foreground">{props.unit}</p>}
      </section>
    )
  }
})

const StackedBar = defineComponent({
  name: 'StackedBar',
  description: 'Non-negative series stacked across equally sized categories.',
  props: stackedBarProps,
  component: ({ props }) => {
    const totals = props.categories.map((_, i) =>
      props.series.reduce((sum, entry) => sum + (entry.values[i] ?? 0), 0)
    )
    const max = Math.max(1, ...totals)
    return (
      <section aria-label={props.title} className="space-y-2">
        <h4 className="text-sm font-semibold">{props.title}</h4>
        <Legend series={props.series} />
        <ul className="space-y-2 text-xs">
          {props.categories.map((category, index) => (
            <li className="grid grid-cols-[minmax(0,6rem)_minmax(0,1fr)_auto] items-center gap-2" key={index}>
              <span className="truncate" title={category}>{category}</span>
              <span aria-label={`${category}: ${formatCount(totals[index] ?? 0)} ${props.unit}`} className="flex h-3 overflow-hidden rounded-sm bg-muted" role="img">
                {props.series.map((entry, i) => (
                  <span
                    aria-hidden
                    className={`block h-full shrink-0 bg-current ${SERIES_TONE[i]}`}
                    key={i}
                    style={{ width: `${((entry.values[index] ?? 0) / max) * 100}%` }}
                  />
                ))}
              </span>
              <span className="text-right font-medium tabular-nums">{formatCount(totals[index] ?? 0)}</span>
            </li>
          ))}
        </ul>
        <SeriesValues props={props} />
      </section>
    )
  }
})

function stackedBands(series: SeriesEntry[], count: number) {
  const totals = Array.from({ length: count }, () => 0)
  const bands = series.map(entry => {
    const lower = [...totals]
    entry.values.forEach((number, i) => { totals[i] = (totals[i] ?? 0) + number })
    return { lower, upper: [...totals] }
  })
  return { bands, max: Math.max(1, ...totals) }
}

function polygonPoints(lower: number[], upper: number[], max: number) {
  const width = 560
  const height = 180
  const x = (i: number) => (i * width) / (upper.length - 1)
  const y = (n: number) => height - (n / max) * height
  return [
    ...upper.map((n, i) => `${x(i)},${y(n)}`),
    ...lower.map((n, i) => `${x(i)},${y(n)}`).reverse()
  ].join(' ')
}

const StackedArea = defineComponent({
  name: 'StackedArea',
  description: 'Original catalog-v2 stacked area, with one raw value per category per series.',
  props: stackedAreaProps,
  component: ({ props }) => {
    const stack = stackedBands(props.series, props.categories.length)
    return (
      <section aria-label={props.title} className="space-y-2">
        <h4 className="text-sm font-semibold">{props.title}</h4>
        <Legend series={props.series} />
        <svg aria-label={`${props.title}, stacked values`} className="h-40 w-full" preserveAspectRatio="none" role="img" viewBox="0 0 560 180">
          {stack.bands.map((band, i) => (
            <polygon className={SERIES_TONE[i]} fill="currentColor" key={i} points={polygonPoints(band.lower, band.upper, stack.max)} />
          ))}
        </svg>
        <SeriesValues props={props} />
      </section>
    )
  }
})

const LineChart = defineComponent({
  name: 'LineChart',
  description: 'Line series with one non-negative raw value per category.',
  props: lineChartProps,
  component: ({ props }) => {
    const max = Math.max(1, ...props.series.flatMap(entry => entry.values))
    return (
      <section aria-label={props.title} className="space-y-2">
        <h4 className="text-sm font-semibold">{props.title}</h4>
        <Legend series={props.series} />
        <svg aria-label={`${props.title}, line chart`} className="h-40 w-full" preserveAspectRatio="none" role="img" viewBox="0 0 560 180">
          {props.series.map((entry, i) => (
            <polyline
              className={SERIES_TONE[i]}
              fill="none"
              key={i}
              points={entry.values.map((n, j) => `${(j * 560) / (entry.values.length - 1)},${180 - (n / max) * 180}`).join(' ')}
              stroke="currentColor"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
          ))}
        </svg>
        <SeriesValues props={props} />
      </section>
    )
  }
})

const Table = defineComponent({
  name: 'Table',
  description: 'Read-only text table. Every row must contain one cell per column.',
  props: tableProps,
  component: ({ props }) => (
    <section aria-label={props.title} className="space-y-2">
      <h4 className="text-sm font-semibold">{props.title}</h4>
      <div aria-label={`${props.title} table`} className="max-h-80 overflow-auto" role="region" tabIndex={0}>
        <table className="w-full border-collapse text-left text-xs">
          <thead>
            <tr>
              {props.columns.map((column, i) => (
                <th className="border-b border-(--ui-stroke-tertiary) px-2 py-2 font-semibold" key={i} scope="col">{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {props.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td className="border-b border-(--ui-stroke-tertiary) px-2 py-2 whitespace-pre-wrap" key={j}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
})

const Board = defineComponent({
  name: 'Board',
  description: 'Read-only chart board with a title, a summary and up to eight panels.',
  props: z.object({
    title,
    summary,
    panels: z.array(z.union([Stat.ref, BarChart.ref, StackedBar.ref, StackedArea.ref, LineChart.ref, Table.ref, RideOptions.ref, MailList.ref, Route.ref, PullRequest.ref]))
      .min(1).max(LIMITS.panels)
  }),
  component: ({ props, renderNode }) => (
    <section aria-label={props.title} className="not-prose min-w-0 space-y-5 p-3 text-foreground">
      <header className="space-y-1">
        <h3 className="text-base font-semibold">{props.title}</h3>
        {props.summary && <p className="whitespace-pre-wrap text-sm text-muted-foreground">{props.summary}</p>}
      </header>
      {renderNode(props.panels)}
    </section>
  )
})

// No Query, Mutation, functions, registered actions or user-defined state.
// Generated content cannot send messages, follow links or call tools.
const library = createLibrary({
  components: [Board, Stat, BarChart, StackedBar, StackedArea, LineChart, Table, RideOptions, MailList, Route, PullRequest],
  root: 'Board'
})
const parser = createParser(library.toJSONSchema(), library.root)
const panelSchemas = {
  Stat: metricProps,
  BarChart: barProps,
  StackedBar: stackedBarProps,
  StackedArea: stackedAreaProps,
  LineChart: lineChartProps,
  Table: tableProps,
  ...appCardSchemas
} as const

type PanelType = keyof typeof panelSchemas

export type OpenUiIssue = 'incomplete' | 'invalid' | 'oversized' | 'readOnlyError' | 'series' | 'rows'
export type OpenUiStatus = { kind: 'ready' } | { kind: 'invalid' | 'incomplete'; reason: OpenUiIssue }

const isRecord = (item: unknown): item is Record<string, unknown> =>
  typeof item === 'object' && item !== null && !Array.isArray(item)

export function inspectOpenUiBoard(code: string): OpenUiStatus {
  if (new TextEncoder().encode(code).byteLength > LIMITS.bytes) {
    return { kind: 'invalid', reason: 'oversized' }
  }

  try {
    const parsed = parser.parse(code)

    if (parsed.queryStatements.length || parsed.mutationStatements.length || Object.keys(parsed.stateDeclarations).length) {
      return { kind: 'invalid', reason: 'readOnlyError' }
    }
    if (parsed.meta.incomplete || parsed.meta.unresolved.length || !parsed.root) {
      return { kind: 'incomplete', reason: 'incomplete' }
    }
    const root = parsed.root
    const props = root.props

    if (parsed.meta.errors.length || root.typeName !== 'Board' || !isRecord(props) ||
        typeof props.title !== 'string' || props.title.length === 0 || props.title.length > 200 ||
        typeof props.summary !== 'string' || props.summary.length > 4_000 ||
        !Array.isArray(props.panels) || props.panels.length < 1 || props.panels.length > LIMITS.panels) {
      return { kind: 'invalid', reason: 'invalid' }
    }

    for (const panel of props.panels) {
      if (!isRecord(panel) || typeof panel.typeName !== 'string' ||
          !Object.hasOwn(panelSchemas, panel.typeName)) {
        return { kind: 'invalid', reason: 'invalid' }
      }
      const panelType = panel.typeName as PanelType
      const validated = panelSchemas[panelType].safeParse(panel.props)

      if (!validated.success) {
        return { kind: 'invalid', reason: 'invalid' }
      }
      if (isAppCardType(panelType) && appCardProblem({ typeName: panelType, props: validated.data })) {
        return { kind: 'invalid', reason: 'invalid' }
      }
      if (panelType === 'Table') {
        const table = validated.data as z.infer<typeof tableProps>
        if (table.rows.some(row => row.length !== table.columns.length)) {
          return { kind: 'invalid', reason: 'rows' }
        }
      }
      if (panelType === 'StackedBar' || panelType === 'StackedArea' || panelType === 'LineChart') {
        const chart = validated.data as z.infer<typeof stackedBarProps>
        if (chart.series.some(entry => entry.values.length !== chart.categories.length)) {
          return { kind: 'invalid', reason: 'series' }
        }
      }
    }
    return { kind: 'ready' }
  } catch {
    return { kind: 'invalid', reason: 'invalid' }
  }
}

export function OpenUiBoard({ code, streaming }: { code: string; streaming?: boolean }) {
  return <Renderer isStreaming={Boolean(streaming)} library={library} response={code} />
}
