// Generate the documented defaults with the same formatter used for effective bindings.
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const scratch = await mkdtemp(join(tmpdir(), 'hermes-shortcuts-'))
const previousHome = process.env.HERMES_HOME
process.env.HERMES_HOME = scratch
try {
  const output = join(scratch, 'actions.mjs')
  await build({
    entryPoints: [join(root, 'src/actions.ts')], outfile: output, bundle: true,
    platform: 'node', format: 'esm', tsconfig: join(root, 'tsconfig.json'),
    plugins: [{ name: 'native-sdk', setup(builder) {
      builder.onResolve({ filter: /^@stencil-hq\/tern$/ }, () => ({ path: fileURLToPath(import.meta.resolve('@stencil-hq/tern')), external: true }))
    } }]
  })
  const { shortcutsMarkdown } = await import(pathToFileURL(output).href)
  const path = join(root, 'SHORTCUTS.md')
  const original = await readFile(path, 'utf8')
  if (!original.includes('<!-- generated-bindings:start -->') || !original.includes('<!-- generated-bindings:end -->')) {
    throw new Error('Shortcut documentation is missing its generation markers.')
  }
  const next = original.replace(/<!-- generated-bindings:start -->[\s\S]*?<!-- generated-bindings:end -->/,
    `<!-- generated-bindings:start -->\n${shortcutsMarkdown()}\n<!-- generated-bindings:end -->`)
  if (process.argv.includes('--check')) {
    if (next !== original) { throw new Error('Shortcut documentation is stale. Run npm run shortcuts:generate.') }
  } else {
    await writeFile(path, next)
  }
} finally {
  if (previousHome === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = previousHome }
  await rm(scratch, { force: true, recursive: true })
}
