import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { afterAll, expect, it } from 'vitest'
import { build, loadConfigFromFile } from 'vite'

// Use the actual production chunking options, not a mock of the chunk matcher.
const root = mkdtempSync(path.join(tmpdir(), 'hermes-webapp-chunks-'))
afterAll(() => rmSync(root, { recursive: true, force: true }))

it('embeds a tiny shared JS chunk in its lazy routes without eager-loading either route', async () => {
  writeFileSync(path.join(root, 'index.html'), '<div id="app"></div><script type="module" src="/main.js"></script>')
  writeFileSync(path.join(root, 'main.js'), [
    "globalThis.loadA = () => import('./lazy-a.js')",
    "globalThis.loadB = () => import('./lazy-b.js')"
  ].join('\n'))
  writeFileSync(path.join(root, 'shared.js'), [
    'export function readShared() {',
    '  globalThis.sharedReads = (globalThis.sharedReads || 0) + 1',
    `  return "${'x'.repeat(2048)}"`,
    '}'
  ].join('\n'))
  for (const suffix of ['a', 'b']) {
    writeFileSync(path.join(root, `lazy-${suffix}.js`), [
      "import { readShared } from './shared.js'",
      `export function value() { return readShared() + '${suffix}' }`
    ].join('\n'))
  }

  const configPath = fileURLToPath(new URL('../vite.config.ts', import.meta.url))
  const loaded = await loadConfigFromFile({ command: 'build', mode: 'production' }, configPath)
  expect(loaded).not.toBeNull()
  const result = await build({
    configFile: false,
    root,
    base: './',
    logLevel: 'silent',
    build: { write: false, rolldownOptions: loaded!.config.build!.rolldownOptions }
  })
  const output = Array.isArray(result) ? result.flatMap((bundle) => bundle.output) : result?.output ?? []
  const chunks = output.filter((file) => file.type === 'chunk')
  const lazy = chunks.filter((chunk) => chunk.isDynamicEntry)

  // With automatic splitting, shared.js is a third HTTP fetch. Inline copies
  // into the two lazy chunks remove it without pulling either route into entry.
  expect(lazy).toHaveLength(2)
  expect(lazy.every((chunk) => chunk.moduleIds.some((id) => id.endsWith('/shared.js')))).toBe(true)
  expect(chunks.filter((chunk) => chunk.isEntry).some((chunk) =>
    chunk.moduleIds.some((id) => id.endsWith('/shared.js'))
  )).toBe(false)
})
