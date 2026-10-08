// Real #456/#457 validation and source fingerprints; no parser replacement,
// generated-code execution, installed OpenUI package or Tern window required.
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { readPreparedVisual } from '../visuals.js'

const root = fileURLToPath(new URL('../../../', import.meta.url))
const moduleUrl = (path: string) => pathToFileURL(join(root, path)).href
const dirs: string[] = []
afterEach(async () => {
  vi.unstubAllEnvs()
  await Promise.all(dirs.splice(0).map(dir => rm(dir, { recursive: true, force: true })))
})

async function fixture() {
  const tools = await import(/* @vite-ignore */ moduleUrl('ui-tsp/experiments/openui-preview/src/bundle.mjs'))
  const host = await import(/* @vite-ignore */ moduleUrl('ui-tsp/experiments/openui-generation/src/host.mjs'))
  const fp = await tools.fingerprints()
  const document = { version: 1, title: 'Native integration', root: {
    id: 'root', label: 'repo', code: 12, churn: 2, children: [
      { id: 'file', label: 'one.ts', code: 12, churn: 2, children: [] }
    ]
  } }
  const artifact = tools.prepareArtifact(JSON.stringify(document), fp.rendererHash)
  const scope = '["stored","main"]'
  const selection = host.bindSelection({ snapshotId: 'repo', mode: 'code', metrics: ['files', 'code'], hottestLimit: 1 },
    'host-reviewed fixture; not a model generation test', { scope, snapshots: new Map([['repo', artifact]]) })
  const presentation = { width: 728, height: 650, appearance: 'dark' }
  const bundle = tools.createBundle(selection, artifact, presentation, fp.bridgeHash)
  const dir = await mkdtemp(join(tmpdir(), 'hermes-visual-bundle-'))
  dirs.push(dir)
  const path = join(dir, 'candidate.hvisual.json')
  await writeFile(path, JSON.stringify(bundle))
  vi.stubEnv('HERMES_PYTHON_SRC_ROOT', root)
  return { tools, scope, selection, artifact, presentation, bundle, path }
}

describe('frontend consumes the existing immutable OpenUI bundle', () => {
  it('loads through the actual validator and current source fingerprint contract', async () => {
    const f = await fixture()
    const candidate = await readPreparedVisual(f.path, f.scope)
    expect(candidate.id).toBe(f.bundle.id)
    expect(candidate.metrics.map(metric => metric.value)).toEqual([1, 12])
    expect(candidate.href).toBe(pathToFileURL(f.path).href)
    expect(Object.isFrozen(candidate)).toBe(true)
  })
  it('does not treat a self-consistent bundle as cross-session or current-build authority', async () => {
    const f = await fixture()
    await expect(readPreparedVisual(f.path, '["another","main"]')).rejects.toThrow('scope changed')
    const oldBuild = f.tools.createBundle(f.selection, f.artifact, f.presentation, '0'.repeat(64))
    await writeFile(f.path, JSON.stringify(oldBuild))
    await expect(readPreparedVisual(f.path, f.scope)).rejects.toThrow('source changed')
  })
  it('rejects tampered data and does not silently find or install another adapter', async () => {
    const f = await fixture()
    const tampered = JSON.parse(JSON.stringify(f.bundle))
    tampered.artifact.document.title = 'Changed after preparation'
    await writeFile(f.path, JSON.stringify(tampered))
    await expect(readPreparedVisual(f.path, f.scope)).rejects.toThrow('bundle changed')
    vi.stubEnv('HERMES_PYTHON_SRC_ROOT', '')
    await expect(readPreparedVisual(f.path, f.scope)).rejects.toThrow('source-checkout launcher')
  })
})
