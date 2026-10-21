import { resolve } from 'node:path'
import { build } from 'esbuild'
await build({
  entryPoints: ['ui-tsp/src/__tests__/fixtures/slash-parity.fixture.ts'],
  outfile: 'ui-tsp/dist/slash-parity.fixture.js', bundle: true, platform: 'node', format: 'esm',
  target: 'node22', jsx: 'automatic', jsxImportSource: '@stencil-hq/tern',
  loader: { '.png': 'binary' }, alias: { '@tui': resolve('ui-tui/src') },
  banner: { js: "import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);" }
})
