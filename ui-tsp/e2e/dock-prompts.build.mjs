import { execFileSync } from 'node:child_process'
import { dirname, relative, resolve } from 'node:path'
import { build } from 'esbuild'

await build({
  entryPoints: ['ui-tsp/src/__tests__/fixtures/dock-prompts.fixture.ts'],
  outfile: 'ui-tsp/dist/dock-prompts.fixture.js', bundle: true, platform: 'node', format: 'esm',
  target: 'node22', jsx: 'automatic', jsxImportSource: '@stencil-hq/tern',
  loader: { '.png': 'binary' }, alias: { '@tui': resolve('ui-tui/src') },
  banner: { js: "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);" },
  plugins: process.argv.includes('--baseline') ? [{ name: 'verbatim-f1-base', setup(build) {
    const files = new Set(['ui-tsp/src/app.ts', 'ui-tsp/src/overlays/approval.tsx',
      'ui-tsp/src/overlays/prompts.tsx', 'ui-tsp/src/view/dock.tsx'])
    build.onLoad({ filter: /\.tsx?$/ }, ({ path }) => {
      const file = relative(process.cwd(), path)
      if (!files.has(file)) { return }
      return { contents: execFileSync('git', ['show', `724b2aaec5:${file}`], { encoding: 'utf8' }),
        loader: path.endsWith('.tsx') ? 'tsx' : 'ts', resolveDir: dirname(path) }
    })
  } }] : []
})
