import { execFileSync } from 'node:child_process'
import { dirname, relative, resolve } from 'node:path'
import { build } from 'esbuild'
await build({
  entryPoints: ['ui-tsp/src/__tests__/fixtures/slash-parity.fixture.ts'],
  outfile: 'ui-tsp/dist/slash-parity.fixture.js', bundle: true, platform: 'node', format: 'esm',
  target: 'node22', jsx: 'automatic', jsxImportSource: '@stencil-hq/tern',
  loader: { '.png': 'binary' }, alias: { '@tui': resolve('ui-tui/src') },
  plugins: process.argv.includes('--baseline') ? [{
    name: 'classic-parity-baseline',
    setup(builder) {
      builder.onLoad({ filter: /ui-tsp\/src\/(commands\.ts|app\.ts|operations\.ts|overlays\/(completion|report-sheet)\.tsx)$/ }, args => ({
        contents: execFileSync('git', ['show', `724b2aaec5:${relative(process.cwd(), args.path)}`], { encoding: 'utf8' }),
        loader: args.path.endsWith('.tsx') ? 'tsx' : 'ts', resolveDir: dirname(args.path)
      }))
    }
  }] : [],
  banner: { js: "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);" }
})
