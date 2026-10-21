import { execFileSync } from 'node:child_process'
import { dirname, relative, resolve } from 'node:path'
import { build } from 'esbuild'

const baseline = process.argv.includes('--baseline')
const files = new Set(['ui-tsp/src/actions.ts', 'ui-tsp/src/overlays/settings.tsx'])
await build({
  entryPoints: ['ui-tsp/src/__tests__/fixtures/f4.fixture.ts'],
  outfile: 'ui-tsp/dist/f4.fixture.js', bundle: true, platform: 'node', format: 'esm',
  target: 'node22', jsx: 'automatic', jsxImportSource: '@stencil-hq/tern',
  loader: { '.png': 'binary' }, alias: { '@tui': resolve('ui-tui/src') },
  banner: { js: "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);" },
  plugins: baseline ? [{ name: 'f4-baseline', setup(build) {
    build.onLoad({ filter: /\.(ts|tsx)$/ }, ({ path }) => {
      const file = relative(process.cwd(), path)
      if (!files.has(file)) {return}
      return { contents: execFileSync('git', ['show', `724b2aaec5:${file}`], { encoding: 'utf8' }), loader: path.endsWith('.tsx') ? 'tsx' : 'ts', resolveDir: dirname(path) }
    })
  } }] : []
})
