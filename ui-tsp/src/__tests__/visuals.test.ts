import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { readVisualFile, summarizeVisual, type VisualBundle, visualScope } from '../visuals.js'

const dirs: string[] = []
afterEach(async () => { await Promise.all(dirs.splice(0).map(dir => rm(dir, { recursive: true, force: true }))) })
async function file(content: string | Buffer) {
  const dir = await mkdtemp(join(tmpdir(), 'hermes-visual-'))
  dirs.push(dir)
  const path = join(dir, 'candidate.hvisual.json')
  await writeFile(path, content)
  return path
}

const bundle: VisualBundle = {
  id: 'a'.repeat(64), selection: { view: { mode: 'code', metrics: ['files', 'code', 'churn'] } },
  artifact: { document: { title: 'Fixture', root: { code: 8, churn: 3, children: [
    { children: [] }, { children: [{ children: [] }, { children: [] }] }
  ] } } }
}

describe('prepared visual frontend', () => {
  it('uses unambiguous stored-session/branch scopes and refuses a sessionless host', () => {
    expect(visualScope({ sid: 'runtime', storedSid: 'stored', info: { branch: 'a:b' } })).toBe('["stored","a:b"]')
    expect(visualScope({ sid: 'runtime', storedSid: null, info: null })).toBe('["runtime",""]')
    expect(visualScope({ sid: null, storedSid: 'stored', info: null })).toBeUndefined()
    expect(visualScope({ sid: 'x'.repeat(256), storedSid: null, info: null })).toBeUndefined()
  })
  it('projects requested host metrics once without changing the source or inventing values', () => {
    const before = JSON.stringify(bundle)
    const summary = summarizeVisual(bundle)
    expect(summary.metrics.map(metric => metric.value)).toEqual([3, 8, 3])
    expect(summary.metrics.map(metric => metric.label)).toEqual(['Files', 'Text lines', 'File touches'])
    expect(JSON.stringify(bundle)).toBe(before)
    expect(Object.isFrozen(summary.metrics[0])).toBe(true)
  })
  it('does not traverse the repository for unrequested file counts', () => {
    const noFiles: VisualBundle = { ...bundle, selection: { view: { mode: 'churn', metrics: ['churn'] } },
      artifact: { document: { title: 'No scan', root: { code: 5, churn: 2,
        get children(): never { throw new Error('unexpected scan') }
      } } }
    }
    expect(summarizeVisual(noFiles).metrics).toEqual([{ key: 'churn', label: 'File touches', value: 2 }])
  })
  it('reads a regular UTF-8 JSON file with the exact byte limit', async () => {
    const path = await file('{"x":"é"}')
    expect((await readVisualFile(path, 10)).input).toEqual({ x: 'é' })
    await expect(readVisualFile(path, 9)).rejects.toThrow('bounded regular file')
  })
  it('rejects implicit paths, wrong extensions, directories and invalid UTF-8', async () => {
    await expect(readVisualFile('candidate.hvisual.json', 32)).rejects.toThrow('absolute path')
    await expect(readVisualFile('/tmp/candidate.json', 32)).rejects.toThrow('absolute path')
    const path = await file(Buffer.from([0xff]))
    await expect(readVisualFile(path, 32)).rejects.toThrow()
    await rm(path)
    await mkdir(path)
    await expect(readVisualFile(path, 32)).rejects.toThrow('bounded regular file')
  })
  it('rejects cancelled and malformed reads rather than treating them as a preview', async () => {
    const controller = new AbortController()
    controller.abort()
    await expect(readVisualFile('/missing.hvisual.json', 32, controller.signal)).rejects.toThrow()
    await expect(readVisualFile(await file('{'), 32)).rejects.toThrow()
  })
})
