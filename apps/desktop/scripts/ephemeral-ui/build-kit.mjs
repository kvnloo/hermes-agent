#!/usr/bin/env node
// Vendors the ephemeral-ui card kit into Hermes Desktop as one offline HTML document per card.
//
//   node scripts/ephemeral-ui/build-kit.mjs <launch-videos checkout> [--check]
//
// The kit lives in kvnloo/launch-videos at pretotypes/ephemeral-ui/src (its site is published as
// kvnloo/ephemeral-ui). The build reads that folder at KIT_REV through `git archive`, so local edits in
// the checkout never leak in. The document carries the kit's own card code (bundled with esbuild), its
// CSS, the app and theme catalogs, and synthetic stand-ins for the trace and intent fixtures. The
// renderer inserts one card's config between HEAD and TAIL and shows it in a sandboxed iframe.
// --check exits non-zero when the generated files are stale.
//
// Ported from the T3 Code (experiments/openui-lab/ephemeral-ui) and Dash (app/scripts/ephemeral-kit)
// integrations of the same kit.
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { build, transform } from 'esbuild'

import { synthesize } from './synthetic.mjs'

export const KIT_REV = '377e664a4cf9305c375c0c429da91918b7de4977'
const KIT_PATH = 'pretotypes/ephemeral-ui/src'
// The modules the card document draws from: everyday app cards (A, B), trace, intent and the work dock.
const KIND_MODULES = ['kinds-a.js', 'kinds-b.js', 'kinds-t.js', 'kinds-i.js', 'kinds-dock.js']
const CSS = ['styles.css', 'trace.css', 'intent.css', 'dock.css']

const here = dirname(fileURLToPath(import.meta.url))
const out = resolve(here, '../../src/components/assistant-ui/ephemeral')
const args = process.argv.slice(2)
const check = args.includes('--check')
const repo = resolve(args.find(arg => !arg.startsWith('--')) ?? '')

const scratch = mkdtempSync(join(tmpdir(), 'eui-kit-'))
try {
  // Code, data and CSS only (the kit's media folder is large and unused here).
  const paths = ['js', 'data', ...CSS].map(path => `${KIT_PATH}/${path}`)
  execFileSync('sh', ['-c', 'repo=$1 rev=$2 dest=$3; shift 3; git -C "$repo" archive --format=tar "$rev" -- "$@" | tar -x -C "$dest"', 'sh', repo, KIT_REV, scratch, ...paths])
  await vendor(join(scratch, KIT_PATH))
} finally {
  rmSync(scratch, { recursive: true, force: true })
}

async function vendor(kit) {
  const read = path => readFileSync(join(kit, path), 'utf8')
  const json = path => JSON.parse(read(path))

  const script = (
    await build({
      entryPoints: [join(here, 'card-entry.js')],
      alias: { '@eui': join(kit, 'js') },
      bundle: true,
      format: 'iife',
      legalComments: 'none',
      logLevel: 'error',
      minify: true,
      target: 'es2020',
      write: false
    })
  ).outputFiles[0].text
  const css = (
    await transform(CSS.map(read).join('\n'), { loader: 'css', minify: true })
  ).code

  // App icons stay monograms, so the brand SVG paths are not shipped. The kit's trace and intent
  // fixtures are sanitized real measurements; Hermes vendors synthetic values in their shape.
  const apps = json('data/apps.json')
  const data = {
    'data/apps.json': { ...apps, apps: apps.apps.map(app => ({ ...app, path: undefined })) },
    'data/themes.json': json('data/themes.json'),
    'data/trace-fixture.json': synthesize('trace', json('data/trace-fixture.json')),
    'data/intent-snapshot.json': synthesize('intent', json('data/intent-snapshot.json'))
  }

  // Registered kinds: the top-level keys of each module's `export const KINDS_* = { … }`.
  const kinds = KIND_MODULES.flatMap(file => {
    const source = read(`js/${file}`)
    const start = source.search(/export const KINDS_\w+ = \{/)
    const end = source.indexOf('\n};', start)
    const block = source.slice(start, end < 0 ? source.indexOf('\n', start) : end + 3)
    return [...block.matchAll(/(?:^ {2}(?! )|KINDS_\w+ = \{ )(?:"([\w-]+)"|'([\w-]+)'|([\w-]+)):\s*(?:\{|define\()/gm)].map(m => m[1] ?? m[2] ?? m[3])
  })
  if (kinds.length < 40) throw new Error(`found only ${kinds.length} registered kinds; the KINDS block format changed`)

  // Every connector must name a catalog app and kinds this build draws.
  const connectors = JSON.parse(readFileSync(join(here, 'connectors.json'), 'utf8')).servers
  const byId = Object.fromEntries(apps.apps.map(app => [app.id, app]))
  const connectorApps = {}
  for (const [server, entry] of Object.entries(connectors)) {
    const app = byId[entry.app]
    if (!app) throw new Error(`connector ${server}: app ${entry.app} is not in the kit catalog`)
    for (const [pattern, kind] of entry.tools) {
      if (!kinds.includes(kind)) throw new Error(`connector ${server}: kind ${kind} is not in this build`)
      new RegExp(pattern, 'i')
    }
    connectorApps[app.id] = { name: app.name, hex: app.hex ?? null }
  }

  // JSON: "<" only occurs inside strings, so \u003c is exact. Code and CSS must never close their element.
  const safeJson = text => text.replaceAll('<', '\\u003c')
  const safe = text => {
    if (/<\/(script|style)|<!--/i.test(text)) throw new Error('kit source would close its element')
    return text
  }

  const csp =
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; " +
    "font-src data:; media-src data: blob:; connect-src 'none'; frame-src 'none'; worker-src 'none'; " +
    "base-uri 'none'; form-action 'none'"
  // One card per document. The kit's .eu-card is sized for its gallery; here it fills the frame.
  const hostCss =
    'html,body{margin:0;background:transparent}#eui-root{padding:2px 2px 6px}' +
    '#eui-root>.eu-card{max-width:none;width:auto;margin:0}#eui-root>.eu-card.gone{width:fit-content}' +
    '.eui-fail{padding:10px 12px;border:1px solid var(--h-danger,#e5484d);border-radius:10px;color:var(--h-fg,#ddd);font:13px system-ui}'
  const documentHead =
    '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
    `<meta http-equiv="Content-Security-Policy" content="${csp}">` +
    `<style>${safe(css)}${hostCss}</style>` +
    `<script type="application/json" id="eui-data">${safeJson(JSON.stringify(data))}</script><script>window.__EUI_CARD=`
  const documentTail = `</script></head><body><div id="eui-root"></div><script>${safe(script)}</script></body></html>`

  const sha256 = createHash('sha256').update(documentHead + documentTail).digest('hex')
  const banner =
    '// Generated by apps/desktop/scripts/ephemeral-ui/build-kit.mjs. Do not edit.\n' +
    `// Source: ephemeral-ui kit (kvnloo/launch-videos ${KIT_PATH}) at ${KIT_REV}\n` +
    '/* eslint-disable */\n'
  const files = {
    'kit-meta.generated.ts':
      banner +
      `export const EPHEMERAL_UI_REVISION = ${JSON.stringify(KIT_REV)}\n` +
      `export const EPHEMERAL_UI_DOCUMENT_SHA256 = ${JSON.stringify(sha256)}\n` +
      `export const EPHEMERAL_UI_KINDS = ${JSON.stringify(kinds)} as const\n` +
      '/** Catalog name and brand colour of every app a connector names (data/apps.json). */\n' +
      `export const EPHEMERAL_UI_APPS: Record<string, { name: string; hex: string | null }> = ${JSON.stringify(connectorApps)}\n` +
      '/** scripts/ephemeral-ui/connectors.json: which card a tool call on each MCP server grows. */\n' +
      `export const EPHEMERAL_UI_CONNECTORS: Record<string, { app: string; aliases: readonly string[]; tools: readonly (readonly [string, string])[] }> = ${JSON.stringify(connectors)}\n`,
    'kit.generated.ts':
      banner +
      `export const EPHEMERAL_UI_HEAD = ${JSON.stringify(documentHead)}\n` +
      `export const EPHEMERAL_UI_TAIL = ${JSON.stringify(documentTail)}\n`
  }

  const stale = []
  for (const [name, text] of Object.entries(files)) {
    const path = join(out, name)
    if (check) {
      let current = ''
      try {
        current = readFileSync(path, 'utf8')
      } catch {
        // Missing output is stale output.
      }
      if (current !== text) stale.push(name)
    } else {
      writeFileSync(path, text)
    }
  }

  console.log(JSON.stringify({ revision: KIT_REV, kinds: kinds.length, kib: (documentHead.length + documentTail.length) >> 10, sha256, ...(check ? { stale } : { wrote: Object.keys(files) }) }))
  if (stale.length) process.exitCode = 1
}
