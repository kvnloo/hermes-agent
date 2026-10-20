// Builds the real presentation fixture; --baseline loads the four fixes' base sources verbatim.
import { execFileSync } from 'node:child_process'
import { resolve, relative, dirname } from 'node:path'
import { build } from 'esbuild'

const refIndex = process.argv.indexOf('--baseline-ref')
const base = refIndex < 0 ? '84fb40cf59117fd4b5a48fc91b69ca431cad1224' : process.argv[refIndex + 1]
if (!base || base.startsWith('-')) throw new Error('Missing --baseline-ref revision')
const files = new Set([
  'ui-tsp/src/live-voice.tsx', 'ui-tsp/src/view/dock.tsx',
  'ui-tsp/src/view/action-button.tsx', 'ui-tsp/src/view/tools.tsx',
  'ui-tsp/src/view/transcript.tsx', 'ui-tsp/src/overlays/models.tsx'
])
await build({
  entryPoints: ['ui-tsp/src/__tests__/fixtures/live-ux.fixture.ts'],
  outfile: 'ui-tsp/dist/live-ux.fixture.js', bundle: true, platform: 'node', format: 'esm',
  target: 'node22', jsx: 'automatic', jsxImportSource: '@stencil-hq/tern',
  loader: { '.png': 'binary' }, alias: { '@tui': resolve('ui-tui/src') },
  banner: { js: "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);" },
  plugins: process.argv.includes('--baseline') ? [{ name: 'verbatim-base-source', setup(build) {
    build.onLoad({ filter: /\.tsx$/ }, ({ path }) => {
      const file = relative(process.cwd(), path)
      if (!files.has(file)) return
      return { contents: execFileSync('git', ['show', `${base}:${file}`], { encoding: 'utf8' }), loader: 'tsx', resolveDir: dirname(path) }
    })
  } }] : []
})
