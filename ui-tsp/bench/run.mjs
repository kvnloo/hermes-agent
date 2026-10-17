#!/usr/bin/env node
import { build } from 'esbuild'
import { readFile, mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync, execFileSync } from 'node:child_process'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const out = await mkdtemp(join(tmpdir(), 'frame-bench-'))
const bundle = join(out, 'replay.mjs')
await build({
  absWorkingDir: root,
  entryPoints: [join(root, 'bench/worker.ts')],
  outfile: bundle,
  bundle: true,
  platform: 'node',
  format: 'esm',
  target: 'node22',
  jsx: 'automatic',
  jsxImportSource: '@stencil-hq/tern',
  loader: { '.png': 'binary' },
  alias: { '@tui': resolve(root, '../ui-tui/src') },
  banner: { js: "import { createRequire } from 'node:module'; const require = createRequire(import.meta.url);" },
  plugins: [
    {
      name: 'time-app-build',
      setup(b) {
        b.onLoad({ filter: /\/ui-tsp\/src\/(app|frame)\.ts$/ }, async ({ path }) => {
          const ref = process.argv.find(a => a.startsWith('--source-ref='))?.slice('--source-ref='.length)
          const source = `ui-tsp/src/${path.endsWith('/app.ts') ? 'app' : 'frame'}.ts`
          let contents = ref
            ? execFileSync('git', ['show', `${ref}:${source}`], { cwd: root, encoding: 'utf8' })
            : await readFile(path, 'utf8')
          if (!path.endsWith('/app.ts')) return { contents, loader: 'ts', resolveDir: dirname(path) }
          // Benchmark-only instrumentation. Includes node build, SDK View.from/diff and wire encode.
          const start = '  #render() {'
          const end = '\n  }\n}\n\n/**'
          if (contents.split(start).length !== 2 || contents.split(end).length !== 2)
            throw new Error('App instrumentation seam changed')
          contents = contents
            .replace(start, start + '\n    const __start = performance.now(); try {')
            .replace(end, '\n    } finally { globalThis.__frameBuildSample?.(performance.now() - __start) }' + end)
          return { contents, loader: 'ts', resolveDir: dirname(path) }
        })
      }
    }
  ]
})
if (process.argv.includes('--build-only')) {
  console.log(bundle)
} else {
  const result = spawnSync(process.execPath, [bundle, ...process.argv.slice(2)], {
    stdio: 'inherit',
    env: {
      ...process.env,
      HERMES_HOME: out,
      HERMES_TUI_SPLASH: '0',
      HERMES_TUI_QUERY: '',
      HERMES_TUI_IMAGE: '',
      HERMES_PYTHON_SRC_ROOT: resolve(root, '..')
    }
  })
  process.exitCode = result.status ?? 1
}
