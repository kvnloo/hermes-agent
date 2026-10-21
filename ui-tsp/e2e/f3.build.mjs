import { execFileSync } from 'node:child_process'
import { resolve, relative, dirname } from 'node:path'
import { build } from 'esbuild'
const files = new Set(['app.ts', 'actions.ts', 'attachments.ts', 'transcript.ts', 'retention.ts', 'surface-protocol.ts', 'overlays/help.tsx', 'overlays/settings.tsx', 'overlays/plan-review.tsx'].map(path => `ui-tsp/src/${path}`))
await build({
  entryPoints: ['ui-tsp/src/__tests__/fixtures/f3.fixture.ts'],
  outfile: 'ui-tsp/dist/f3.fixture.js', bundle: true, platform: 'node', format: 'esm',
  target: 'node22', jsx: 'automatic', jsxImportSource: '@stencil-hq/tern',
  loader: { '.png': 'binary' }, alias: { '@tui': resolve('ui-tui/src') },
  banner: { js: "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);" },
  plugins: process.argv.includes('--baseline') ? [{ name: 'verbatim-f3-base', setup(build) {
    build.onLoad({ filter: /\.tsx?$/ }, ({ path }) => {
      const file = relative(process.cwd(), path)
      if (!files.has(file)) return
      return { contents: execFileSync('git', ['show', `724b2aaec5:${file}`], { encoding: 'utf8' }), loader: file.endsWith('.tsx') ? 'tsx' : 'ts', resolveDir: dirname(path) }
    })
  } }] : []
})
