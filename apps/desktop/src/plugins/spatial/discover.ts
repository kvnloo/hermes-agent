/** FS bridge + repo walk for Spatial desk curation. Plugin-local (no @/ imports). */

import type { FoundDoc } from './model'
import { isDocFile, planWalk, shouldSkipDir } from './model'

interface DirEntry {
  name: string
  path?: string
  isDirectory?: boolean
  type?: string
}

interface HermesDesktopFs {
  readDir?: (path: string) => Promise<{ entries?: DirEntry[]; error?: string }>
  readFileText?: (path: string) => Promise<{ content?: string; text?: string; error?: string } | string>
}

function desktop(): HermesDesktopFs | null {
  return (globalThis as { hermesDesktop?: HermesDesktopFs }).hermesDesktop ?? null
}

function join(root: string, name: string): string {
  if (root.endsWith('/') || root.endsWith('\\')) return root + name
  return `${root}/${name}`
}

function basename(p: string): string {
  const parts = p.replace(/\\/g, '/').split('/')
  return parts[parts.length - 1] || p
}

function relTo(root: string, full: string): string {
  const r = root.replace(/\\/g, '/').replace(/\/$/, '')
  const f = full.replace(/\\/g, '/')
  return f.startsWith(r + '/') ? f.slice(r.length + 1) : f
}

async function listDir(path: string): Promise<DirEntry[]> {
  const bridge = desktop()
  if (!bridge?.readDir) return []
  const res = await bridge.readDir(path)
  if (res?.error || !res.entries) return []
  return res.entries
}

/** Shallow-ish walk: depth-capped BFS, doc files only. */
export async function walkDocs(root: string, maxDepth = 3, maxFiles = 80): Promise<FoundDoc[]> {
  const out: FoundDoc[] = []
  const queue: Array<{ path: string; depth: number }> = [{ path: root, depth: 0 }]
  const seen = new Set<string>()

  while (queue.length && out.length < maxFiles) {
    const { path, depth } = queue.shift()!
    if (seen.has(path)) continue
    seen.add(path)

    let entries: DirEntry[]
    try {
      entries = await listDir(path)
    } catch {
      continue
    }

    const normalized = entries.map(e => ({
      name: e.name,
      path: e.path || join(path, e.name),
      isDirectory: Boolean(e.isDirectory ?? e.type === 'directory' || e.type === 'dir')
    }))

    const { docs, dirs } = planWalk(normalized, depth, maxDepth)
    for (const p of docs) {
      if (out.length >= maxFiles) break
      out.push({ path: p, name: basename(p), rel: relTo(root, p) })
    }
    for (const d of dirs) queue.push({ path: d, depth: depth + 1 })
  }

  // Boost common doc roots with an extra pass (even if deep).
  for (const sub of ['docs', 'design', 'specs', 'architecture', '.zeros', 'product']) {
    if (out.length >= maxFiles) break
    const p = join(root, sub)
    try {
      const entries = await listDir(p)
      for (const e of entries) {
        if (out.length >= maxFiles) break
        if (shouldSkipDir(e.name)) continue
        const full = e.path || join(p, e.name)
        if (isDocFile(e.name)) {
          out.push({ path: full, name: e.name, rel: relTo(root, full) })
        }
      }
    } catch {
      /* missing folder */
    }
  }

  // Dedupe by path
  const uniq = new Map<string, FoundDoc>()
  for (const d of out) uniq.set(d.path, d)
  return [...uniq.values()]
}

export async function resolveScanRoots(cwd: string, projectPaths: string[] = []): Promise<string[]> {
  const roots = [...projectPaths, cwd].map(p => p.trim()).filter(Boolean)
  const uniq: string[] = []
  for (const r of roots) {
    if (!uniq.some(u => u === r || r.startsWith(u + '/') || r.startsWith(u + '\\'))) uniq.push(r)
  }
  return uniq.slice(0, 4)
}

export async function scanProjectDocs(roots: string[]): Promise<FoundDoc[]> {
  const all: FoundDoc[] = []
  for (const root of roots) {
    const found = await walkDocs(root)
    all.push(...found)
  }
  const uniq = new Map<string, FoundDoc>()
  for (const d of all) uniq.set(d.path, d)
  return [...uniq.values()]
}
