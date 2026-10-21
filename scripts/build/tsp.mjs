#!/usr/bin/env node
// Self-contained Tern frontend (ui-tsp) compiler. Dependencies must already be prepared.
import { cpSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'
import { frontendArgs, isMain, productOutput, publishDirectory, repoRoot, withProduct } from './frontend-common.mjs'
import { recordProduct, buildInputs } from './freshness.mjs'

export async function buildTsp(options) {
  const { source, out: destination } = productOutput(options.source, options.out, ['ui-tsp', 'ui-tui', 'apps/shared', 'node_modules'])
  const { bundle } = await import(pathToFileURL(join(source, 'ui-tsp/scripts/build.mjs')).href)
  const inputs = buildInputs(source, 'tsp')
  await withProduct(destination, async product => {
    await bundle({ outfile: join(product, 'dist/entry.js'), logLevel: 'info' })
    writeFileSync(join(product, 'package.json'), JSON.stringify({ type: 'module' }) + '\n')
    recordProduct({ source, product: 'tsp', out: join(product, 'dist'), inputs })
  })
  return { out: destination, entry: join(destination, 'dist/entry.js') }
}

// npm's developer entrypoint refreshes ui-tsp/dist in place, like ui-tui's.
async function buildDeveloperTsp() {
  const scratch = mkdtempSync(join(tmpdir(), 'hermes-tsp-'))
  try {
    const result = await buildTsp({ source: repoRoot, out: join(scratch, 'tsp') })
    const staged = mkdtempSync(join(repoRoot, 'ui-tsp/.dist-'))
    try {
      cpSync(join(result.out, 'dist'), staged, { recursive: true })
      publishDirectory(staged, join(repoRoot, 'ui-tsp/dist'), { source: repoRoot })
    } finally {
      rmSync(staged, { recursive: true, force: true })
    }
    return { out: join(repoRoot, 'ui-tsp'), entry: join(repoRoot, 'ui-tsp/dist/entry.js') }
  } finally {
    rmSync(scratch, { recursive: true, force: true })
  }
}

if (isMain(import.meta.url)) {
  try {
    const result = process.argv.length === 2
      ? await buildDeveloperTsp()
      : await buildTsp(frontendArgs(process.argv.slice(2)))
    console.log(`built ${result.entry}`)
  } catch (error) {
    console.error(error)
    process.exitCode = 1
  }
}
