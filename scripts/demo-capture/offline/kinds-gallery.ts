// "44 in 30": every kind of node Tern draws for a program, one after another, each really drawn
// by Tern. 44 kinds, 0.6 s each, in the order Tern answers a program's hello with them, then it
// exits. Every view has the kind's number and name as a text node above it ("10 / 44  diff").
//
// Kinds that only make sense inside another are shown inside it: `item` in a `list`, `seg` in a
// `status`. `overlay`, `toast`, `picker` and `prefs` sit in the surface's `layer`, `editor` in
// its `dock`, as Hermes places them; everything else is in `main`.
//
//   cd ui-tsp && ../node_modules/.bin/tsx ../scripts/demo-capture/offline/kinds-gallery.ts
//   ... kinds-gallery.ts --dwell 2000          # slower, to look at each kind
//   ... kinds-gallery.ts --only diff,table     # just these kinds (numbers stay those of the 44)
//   q, Escape or Ctrl+C leaves early.
//
// Record and render it with record.py / render.py (see ../README.md, "Offline rendering").
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

import { connect, html, node, ui, type Children, type Node, type Session } from '@stencil-hq/tern'

/** The 44 kinds, in the order Tern's hello reply lists them. */
const ORDER = [
  'col', 'row', 'card', 'section', 'rule', 'spacer', 'text', 'md', 'code', 'diff', 'ansi',
  'math', 'image', 'kv', 'table', 'tree', 'badge', 'kbd', 'icon', 'spinner', 'shimmer', 'elapsed',
  'progress', 'rate', 'list', 'item', 'tabs', 'editor', 'input', 'status', 'seg', 'overlay',
  'toast', 'rows', 'picker', 'prefs', 'tool', 'checklist', 'agent', 'chart', 'meter', 'block',
  'effort', 'el'
] as const

type Name = (typeof ORDER)[number]

/** What one kind puts on screen, by region of the surface; `main` sits under the label. */
interface Scene {
  main?: Children
  dock?: Children
  layer?: Children
}

interface Context {
  /** Blob id of the logo, when Tern takes blobs. */
  logo?: string
}

const args = process.argv.slice(2)
const option = (name: string) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined)
const DWELL_MS = Number(option('--dwell') ?? 600)
const only = option('--only')?.split(',')

/** Plain text, with a tone when given. */
const line = (text: string, tone?: string) => ui.text(tone ? { tone } : {}, text)

// ── the 44 scenes ─────────────────────────────────────────────────────────────────────────────

const SCENES: Record<Name, (key: string, cx: Context) => Scene> = {
  col: key => ({
    main: ui.col({ gap: 'sm', key }, line('first', 'accent'), line('second'), line('third', 'muted'))
  }),

  row: key => ({
    main: ui.row({ align: 'center', gap: 'md', key }, line('left', 'accent'), line('to'), line('right', 'muted'))
  }),

  card: key => ({
    main: ui.card(
      { head: 'Deploy', key, status: 'running' },
      line('Uploading api-gateway to us-east-1'),
      line('3 of 8 services', 'muted')
    )
  }),

  section: key => ({
    main: ui.section(
      { collapsible: true, head: 'Release notes', key },
      line('Faster startup, down to 38 ms.'),
      line('The flaky router test is fixed.')
    )
  }),

  rule: key => ({
    main: ui.col({ gap: 'sm', key }, line('above'), ui.rule({ label: 'or' }), line('below'))
  }),

  spacer: key => ({
    main: ui.card({ key }, ui.row({ gap: 'sm' }, line('left'), ui.spacer({ grow: 1 }), line('right')))
  }),

  text: key => ({
    main: ui.col(
      { gap: 'xs', key },
      line('Plain text, wrapped to the pane.'),
      ui.text({
        spans: [
          { s: 'strong', t: 'Styled ' },
          { s: 'accent', t: 'spans, ' },
          { s: 'em', t: 'italic, ' },
          { s: 'success', t: 'green, ' },
          { s: 'mono', t: 'monospace' },
          { t: ' and a ' },
          { href: 'https://tern.dev', s: 'link', t: 'link' }
        ]
      }),
      line('A muted line.', 'muted')
    )
  }),

  md: key => ({
    main: ui.md(
      { key },
      [
        '## Release notes',
        '',
        '- **Faster** startup, down to `38 ms`',
        '- Fixes the *flaky* router test',
        '',
        '> Ship it.'
      ].join('\n')
    )
  }),

  code: key => ({
    main: ui.code({
      key,
      lang: 'ts',
      numbers: true,
      path: 'src/router.ts',
      text: [
        'export function route(path: string) {',
        "  const hit = routes.find(r => r.test(path))",
        "  return hit ?? notFound",
        '}'
      ].join('\n')
    })
  }),

  diff: key => ({
    main: ui.diff({
      key,
      lang: 'ts',
      path: 'src/greet.ts',
      text: ['@@ -1,3 +1,3 @@', ' function greet() {', "-  return 'hello'", "+  return 'hello, tern'", ' }'].join('\n')
    })
  }),

  ansi: key => ({
    main: ui.ansi(
      { key },
      [
        '\x1b[1m$ npm test\x1b[0m',
        '\x1b[32m✓\x1b[0m router matches paths \x1b[2m(4 ms)\x1b[0m',
        '\x1b[32m✓\x1b[0m router falls back to notFound \x1b[2m(1 ms)\x1b[0m',
        '\x1b[31m✗\x1b[0m router decodes %2F \x1b[2m(2 ms)\x1b[0m',
        '\x1b[33m2 passed\x1b[0m, \x1b[31m1 failed\x1b[0m'
      ].join('\n')
    )
  }),

  math: key => ({
    main: ui.math({ display: true, key }, '\\int_0^\\infty e^{-x^2}\\,dx = \\frac{\\sqrt{\\pi}}{2}')
  }),

  image: (key, cx) => ({
    main: cx.logo
      ? ui.image({ alt: 'Hermes', blob: cx.logo, h: 128, key, w: 128 })
      : line('(this Tern does not take blobs)', 'muted')
  }),

  kv: key => ({
    main: ui.kv({
      items: [
        { k: 'Model', v: 'hermes-4-405b' },
        { k: 'Context', v: '131,072 tokens' },
        { k: 'Cost', v: '$0.04' },
        { k: 'Elapsed', v: '1m 23s' }
      ],
      key
    })
  }),

  table: key => ({
    main: ui.table({
      cols: [
        { grow: 1, head: 'Service', id: 'svc' },
        { head: 'State', id: 'state' },
        { head: 'Load', id: 'load' },
        { align: 'end', head: 'p95', id: 'p95' }
      ],
      key,
      rows: [
        { cells: { load: { meter: { value: 0.42 } }, p95: '38 ms', state: [{ s: 'success', t: 'healthy' }], svc: 'api-gateway' }, id: 'api' },
        { cells: { load: { meter: { value: 0.71 } }, p95: '112 ms', state: [{ s: 'warning', t: 'degraded' }], svc: 'search' }, id: 'search' },
        { cells: { load: { meter: { value: 0.18 } }, p95: '9 ms', state: [{ s: 'success', t: 'healthy' }], svc: 'cache' }, id: 'cache' }
      ]
    })
  }),

  tree: key => ({
    main: ui.tree({
      key,
      nodes: [
        {
          children: [
            { icon: 'file-code', id: 'app', label: 'app.ts' },
            {
              children: [
                { icon: 'file-code', id: 'tools', label: 'tools.tsx' },
                { icon: 'file-code', id: 'transcript', label: 'transcript.tsx' }
              ],
              icon: 'folder-open',
              id: 'view',
              label: 'view',
              open: true
            }
          ],
          icon: 'folder-open',
          id: 'src',
          label: 'src',
          open: true
        },
        { icon: 'file', id: 'pkg', label: 'package.json' }
      ]
    })
  }),

  badge: key => ({
    main: ui.row(
      { gap: 'sm', key },
      ui.badge({ text: 'beta' }),
      ui.badge({ text: 'passing', tone: 'success' }),
      ui.badge({ text: '2 warnings', tone: 'warning' }),
      ui.badge({ text: 'failed', tone: 'error' }),
      ui.badge({ text: 'new', tone: 'info' })
    )
  }),

  kbd: key => ({
    main: ui.row(
      { align: 'center', gap: 'md', key },
      ui.kbd({ keys: ['ctrl', 'k'] }),
      ui.kbd({ keys: ['shift', 'tab'] }),
      ui.kbd({ keys: ['alt', 'up'] }),
      ui.kbd({ keys: ['enter'] }),
      ui.kbd({ keys: ['esc'] })
    )
  }),

  icon: key => ({
    main: ui.row(
      { gap: 'md', key },
      ui.icon({ name: 'folder' }),
      ui.icon({ name: 'git-branch' }),
      ui.icon({ name: 'rocket' }),
      ui.icon({ name: 'bolt', tone: 'warning' }),
      ui.icon({ name: 'check', tone: 'success' }),
      ui.icon({ name: 'bug', tone: 'error' }),
      ui.icon({ name: 'sparkle', tone: 'accent' })
    )
  }),

  spinner: key => ({
    main: ui.row(
      { gap: 'lg', key },
      ui.spinner({ label: 'braille', style: 'braille' }),
      ui.spinner({ label: 'dots', style: 'dots' }),
      ui.spinner({ label: 'starburst', style: 'starburst' }),
      ui.spinner({ label: 'orbit', style: 'orbit' })
    )
  }),

  shimmer: key => ({
    main: ui.col(
      { gap: 'sm', key },
      ui.shimmer({ mode: 'classic', text: 'Thinking about the router…' }),
      ui.shimmer({ mode: 'kitt', text: 'Reading src/router.ts' })
    )
  }),

  elapsed: key => ({
    main: ui.row(
      { align: 'center', gap: 'lg', key },
      ui.elapsed({ age: 83000, format: 'short' }),
      ui.elapsed({ age: 3725000, format: 'clock' }),
      ui.elapsed({ age: -90000, format: 'short' })
    )
  }),

  progress: key => ({
    main: ui.col(
      { gap: 'sm', key },
      ui.progress({ label: '62%', value: 0.62 }),
      ui.progress({ label: 'Resolving…' })
    )
  }),

  rate: key => ({
    main: ui.row({ align: 'center', gap: 'lg', key }, ui.rate({ unit: 'tok/s', value: 48.2 }), ui.rate({ unit: 'MB/s', value: 12.6 }))
  }),

  list: key => ({
    main: ui.list(
      { key, selected: `main.${key}.b` },
      ui.item({ icon: 'folder', key: 'a', label: 'src' }),
      ui.item({ icon: 'file-code', key: 'b', label: 'router.ts' }),
      ui.item({ icon: 'file-code', key: 'c', label: 'router.test.ts' }),
      ui.item({ icon: 'file', key: 'd', label: 'package.json' })
    )
  }),

  item: key => ({
    main: ui.list(
      { key, selected: `main.${key}.a` },
      ui.item({ detail: 'Run it this time only', hint: ['enter'], icon: 'check', key: 'a', label: 'Allow once' }),
      ui.item({ detail: 'Until the session ends', icon: 'clock', key: 'b', label: 'Allow for this session', value: [{ s: 'accent', t: 'Recommended' }] }),
      ui.item({ detail: 'Not on this plan', disabled: true, icon: 'lock', key: 'c', label: 'Always allow' })
    )
  }),

  tabs: key => ({
    main: ui.tabs({
      active: 'changes',
      items: [
        { id: 'files', label: 'Files' },
        { id: 'changes', label: 'Changes' },
        { id: 'tests', label: 'Tests' }
      ],
      key
    })
  }),

  editor: key => ({
    dock: ui.editor({ cursor: 33, key, maxLines: 4, placeholder: 'Message Hermes…', text: 'Make the router test pass, then run the suite' })
  }),

  input: key => ({
    main: ui.input({ cursor: 6, key, placeholder: 'Search files…', prompt: '❯ ', text: 'router' })
  }),

  status: key => ({
    main: ui.status(
      { key },
      ui.seg({ icon: 'folder', text: '~/code/courier' }),
      ui.seg({ icon: 'git-branch', text: 'main' }),
      ui.seg({ icon: 'clock', side: 'right', text: '14:02' })
    )
  }),

  seg: key => ({
    main: ui.status(
      { key },
      ui.seg({ icon: 'cpu', priority: 3, spans: [{ s: 'dim', t: 'model ' }, { s: 'strong', t: 'hermes-4-405b' }] }),
      ui.seg({ icon: 'gauge', priority: 2, spans: [{ s: 'num', t: '42%' }, { s: 'dim', t: ' context' }] }),
      ui.seg({ icon: 'time', priority: 1, side: 'right', text: '3m 05s' })
    )
  }),

  overlay: key => ({
    main: line('The page behind the overlay.', 'muted'),
    layer: ui.overlay(
      { anchor: 'center', head: 'Run this command?', key, modal: true, size: 'md' },
      ui.code({ lang: 'bash', text: 'rm -rf node_modules && npm install' }),
      ui.row({ align: 'center', gap: 'md' }, ui.kbd({ keys: ['enter'] }), line('Allow'), ui.kbd({ keys: ['esc'] }), line('Deny'))
    )
  }),

  toast: key => ({
    main: line('The page behind the toast.', 'muted'),
    layer: ui.toast({ key, sub: 'src/router.ts', text: 'Saved', ttl: 4000 })
  }),

  rows: key => ({
    main: ui.rows({
      cols: 40,
      key,
      lines: [
        '\x1b[1;36m┌─ build ─────────────────────────┐\x1b[0m',
        '\x1b[1;36m│\x1b[0m \x1b[32m●\x1b[0m compile      \x1b[2m1.2s\x1b[0m         \x1b[1;36m│\x1b[0m',
        '\x1b[1;36m│\x1b[0m \x1b[33m●\x1b[0m bundle       \x1b[2mrunning\x1b[0m      \x1b[1;36m│\x1b[0m',
        '\x1b[1;36m└─────────────────────────────────┘\x1b[0m'
      ]
    })
  }),

  picker: key => ({
    main: line('The page behind the picker.', 'muted'),
    layer: ui.picker({
      actions: [
        { id: 'use', keys: ['enter'], label: 'Switch', primary: true },
        { end: true, id: 'close', keys: ['esc'], label: 'Close' }
      ],
      columns: [{ format: 'text', head: '$/M', id: 'price' }],
      current: ['m405'],
      icon: 'cpu',
      items: [
        { badges: [{ text: 'reasoning', tone: 'info' }], facts: { price: '3·15' }, id: 'm405', label: 'hermes-4-405b', mono: true },
        { facts: { price: '0.2·0.4' }, id: 'm70', label: 'hermes-4-70b', mono: true },
        { badges: [{ text: 'free', tone: 'success' }], facts: { price: 'free' }, id: 'm8', label: 'hermes-3-8b', mono: true }
      ],
      key,
      layout: 'rows',
      noun: 'models',
      order: ['m405', 'm70', 'm8'],
      placeholder: 'Search models…',
      preview: 'none',
      selected: 'm70',
      size: 'md',
      title: 'Models',
      total: 3
    })
  }),

  prefs: key => ({
    main: line('The page behind the settings.', 'muted'),
    layer: ui.prefs({
      key,
      page: 'look',
      pages: [
        { icon: 'palette', id: 'look', label: 'Appearance' },
        { icon: 'keyboard', id: 'keys', label: 'Keys' },
        { icon: 'agent', id: 'agent', label: 'Agent' }
      ],
      sections: [
        {
          id: 'theme',
          page: 'look',
          rows: [
            {
              control: {
                k: 'choice',
                options: [
                  { label: 'Light', value: 'light' },
                  { label: 'Dark', value: 'dark' },
                  { label: 'Auto', value: 'auto' }
                ],
                style: 'segmented',
                value: 'dark'
              },
              hint: 'Follow the system or pick one',
              id: 'mode',
              label: 'Appearance'
            },
            { control: { k: 'switch', on: false }, id: 'motion', label: 'Reduce motion' },
            { control: { k: 'number', max: 24, min: 8, step: 1, unit: 'px', value: 13 }, id: 'font', label: 'Font size' }
          ],
          title: 'Theme'
        }
      ],
      title: 'Settings'
    })
  }),

  tool: key => ({
    main: ui.tool(
      { collapsible: true, exit: 0, key, meta: ['12 passed'], name: 'bash', status: 'done', target: 'npm test', targetKind: 'command', title: 'Bash', took: 3200 },
      ui.ansi({ text: '\x1b[32m✓\x1b[0m router matches paths\n\x1b[32m✓\x1b[0m router falls back to notFound\n\x1b[2m12 passed (3.2s)\x1b[0m' })
    )
  }),

  checklist: key => ({
    main: ui.checklist({
      key,
      mode: 'full',
      phases: [
        {
          id: 'all',
          items: [
            { id: 'read', status: 'done', text: 'Read the failing test' },
            { id: 'fix', status: 'active', text: 'Fix the router' },
            { id: 'run', status: 'pending', text: 'Run the suite' }
          ]
        }
      ]
    })
  }),

  agent: key => ({
    main: ui.agent({
      agent: 'task',
      key,
      model: 'hermes-4-70b',
      name: 'Agent 1',
      stats: { age: 8200, requests: 6, tokens: 12400, tools: 4 },
      status: 'running',
      task: 'Find the flaky test in the router suite',
      tool: { age: 1500, intent: 'router.test.ts', name: 'grep' }
    })
  }),

  chart: key => ({
    main: ui.chart({
      key,
      kind: 'bars',
      series: [
        { label: 'Mon', value: 3 },
        { label: 'Tue', value: 5 },
        { label: 'Wed', value: 4 },
        { label: 'Thu', value: 8 },
        { label: 'Fri', value: 6 },
        { label: 'Sat', value: 2 },
        { label: 'Sun', value: 1 }
      ],
      size: 'md',
      summary: 'Requests per day'
    })
  }),

  meter: key => ({
    main: ui.col(
      { gap: 'sm', key },
      ui.meter({ label: '72%', style: 'bar', thresholds: { bad: 0.85, warn: 0.6 }, total: '131k', value: 0.72 }),
      ui.meter({ label: 'ring', size: 'md', style: 'ring', value: 0.4 }),
      ui.meter({ label: 'blocks', steps: 10, style: 'blocks', value: 0.8 })
    )
  }),

  block: key => ({
    main: node('block', { key }, [line('inside a block')])
  }),

  effort: key => ({
    main: ui.row(
      { gap: 'lg', key },
      ...(['off', 'low', 'medium', 'high', 'xhigh', 'max'] as const).map(level =>
        ui.row({ align: 'center', gap: 'xs', key: level }, ui.effort({ level }), line(level))
      )
    )
  }),

  el: key => ({
    main: html.article(
      { key },
      html.h3({}, 'Plain HTML'),
      html.p({}, 'Elements Tern draws natively:'),
      html.ul({}, html.li({}, 'div, p, ul, li, table'), html.li({}, 'form, label, button, input')),
      html.button({}, 'Click me')
    )
  })
}

// ── the show ──────────────────────────────────────────────────────────────────────────────────

/** The view of kind number `n` (1-based): its label over its scene. */
function view(n: number, cx: Context) {
  const name = ORDER[n - 1]!
  const label = ui.text({
    key: 'label',
    role: 'kinds.label',
    spans: [
      { s: 'dim', t: `${n} / ${ORDER.length}` },
      '  ',
      { s: 'strong accent', t: name }
    ]
  })

  let scene: Scene

  try {
    scene = SCENES[name](`k${n}`, cx)
  } catch (error) {
    scene = { main: line(`could not build ${name}: ${error instanceof Error ? error.message : String(error)}`, 'error') }
  }

  const list = (c: Children): Children[] => (Array.isArray(c) ? c : [c])

  return {
    dock: scene.dock === undefined ? undefined : list(scene.dock),
    layer: scene.layer === undefined ? undefined : list(scene.layer),
    main: [label, ...(scene.main === undefined ? [] : list(scene.main))]
  }
}

/** The logo as a blob, or undefined when it can't be read or Tern takes no blobs. */
function uploadLogo(session: Session): string | undefined {
  if (!session.caps.features.includes('blobs')) {
    return undefined
  }

  const script = process.argv[1] ?? ''

  for (const path of [
    resolve(dirname(script), '../../../ui-tsp/assets/logo.png'),
    resolve(process.cwd(), 'assets/logo.png')
  ]) {
    try {
      return session.blob(readFileSync(path), 'image/png')
    } catch {
      // try the next place
    }
  }

  return undefined
}

async function main() {
  const session = await connect({ app: 'kinds-gallery' })

  if (!session) {
    console.error('This needs a Tern pane (the Tern Surface Protocol).')
    process.exit(75)
  }

  const missing = ORDER.filter(kind => !session.caps.kinds.includes(kind))
  const cx: Context = { logo: uploadLogo(session) }
  const surface = session.open({ id: 'kinds', listen: false, mode: 'screen', role: 'kinds.gallery', title: 'kinds' })

  let leave = false
  let wake: (() => void) | undefined

  const sleep = (ms: number) =>
    new Promise<void>(done => {
      const timer = setTimeout(done, ms)

      wake = () => {
        clearTimeout(timer)
        done()
      }
    })

  void (async () => {
    for await (const input of session) {
      if (input.type === 'key' && (input.key.name === 'q' || input.key.name === 'escape' || (input.key.ctrl && input.key.name === 'c'))) {
        leave = true
        wake?.()
      }
    }
  })()

  const shown = ORDER.map((name, i) => ({ n: i + 1, name })).filter(({ name }) => !only || only.includes(name))
  const start = performance.now()

  // Each kind is due at a fixed offset from the first, so a late timer never stretches the show.
  for (const [i, { n }] of shown.entries()) {
    const wait = start + i * DWELL_MS - performance.now()

    if (wait > 0) {
      await sleep(wait)
    }

    if (leave) {
      break
    }

    surface.render(view(n, cx))
  }

  if (!leave) {
    await sleep(start + shown.length * DWELL_MS - performance.now())
  }

  await session.close()

  if (missing.length) {
    console.error(`kinds-gallery: Tern ${session.caps.ver} does not list: ${missing.join(' ')}`)
  }

  process.exit(0)
}

void main()
