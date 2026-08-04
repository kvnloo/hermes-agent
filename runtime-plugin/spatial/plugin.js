/** Spatial desk runtime plugin — load-safe ESM for packaged Hermes Desktop. */
import {
  Badge,
  cn,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  host,
  icons,
  KEYBINDS_AREA,
  PALETTE_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  Tip,
  useGrabScroll,
  useValue
} from '@hermes/plugin-sdk'
import { useEffect, useMemo, useRef, useState } from 'react'
import { jsx as _j, jsxs as _js } from 'react/jsx-runtime'

const ID = 'spatial'

const CSS = `
.spatial-desk{--spatial-canvas:#e6e6e8;--spatial-paper:#f0f0f2;--spatial-card:#ffffff;--spatial-card-raised:#ffffff;--spatial-folder:#f5f5f7;--spatial-text:#1c1c1e;--spatial-muted:#636366;--spatial-dim:#8e8e93;--spatial-hair:rgba(0,0,0,.07);--spatial-hair-dim:rgba(0,0,0,.045);--spatial-accent:#0a84ff;--spatial-shadow-rest:0 .5px 1px rgba(0,0,0,.04),0 2px 6px rgba(0,0,0,.04),0 12px 28px rgba(0,0,0,.07),0 28px 56px rgba(0,0,0,.05);--spatial-shadow-hover:0 1px 2px rgba(0,0,0,.05),0 8px 18px rgba(0,0,0,.08),0 24px 48px rgba(0,0,0,.12),0 40px 72px rgba(0,0,0,.08);--spatial-shadow-folder:0 1px 2px rgba(0,0,0,.04),0 10px 24px rgba(0,0,0,.08);--spatial-radius-card:18px;--spatial-radius-folder:20px;--spatial-spring:cubic-bezier(.34,1.45,.64,1);--spatial-ease:cubic-bezier(.22,1,.36,1);position:relative;display:flex;min-height:0;flex:1;flex-direction:column;overflow:hidden;color:var(--spatial-text);background:var(--spatial-canvas);font-family:ui-sans-serif,system-ui,-apple-system,"SF Pro Text","Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
.spatial-desk[data-theme=dark]{--spatial-canvas:#1c1c1e;--spatial-paper:#2c2c2e;--spatial-card:#2c2c2e;--spatial-card-raised:#3a3a3c;--spatial-folder:#2c2c2e;--spatial-text:#f5f5f7;--spatial-muted:#a1a1a6;--spatial-dim:#6c6c70;--spatial-hair:rgba(255,255,255,.1);--spatial-hair-dim:rgba(255,255,255,.06);--spatial-shadow-rest:0 1px 1px rgba(0,0,0,.35),0 8px 18px rgba(0,0,0,.4),0 22px 40px rgba(0,0,0,.35);--spatial-shadow-hover:0 2px 4px rgba(0,0,0,.45),0 16px 32px rgba(0,0,0,.5),0 36px 64px rgba(0,0,0,.42);--spatial-shadow-folder:0 6px 16px rgba(0,0,0,.45)}
.spatial-desk__stage{position:relative;min-height:0;flex:1;overflow:auto;cursor:grab;scrollbar-width:none;overscroll-behavior:contain;touch-action:pan-x pan-y;background:
  radial-gradient(90% 70% at 50% 42%,color-mix(in srgb,var(--spatial-paper) 92%,transparent) 0%,transparent 70%),
  radial-gradient(40% 30% at 18% 80%,rgba(10,132,255,.03),transparent 60%),
  var(--spatial-canvas)}
.spatial-desk__stage::-webkit-scrollbar{display:none}
.spatial-desk__stage.is-grabbing{cursor:grabbing;user-select:none}
.spatial-desk__stage.is-grabbing .spatial-card,.spatial-desk__stage.is-grabbing .spatial-folder__body{transition:none!important}
.spatial-desk__world{position:relative;transform-origin:0 0;will-change:transform}
.spatial-folder{position:absolute;transform-origin:50% 30%;pointer-events:auto}
.spatial-folder__tab{position:absolute;top:-12px;left:20px;z-index:4;width:96px;height:15px;border-radius:9px 9px 0 0;box-shadow:0 -1px 0 rgba(255,255,255,.3) inset}
.spatial-folder__peek{position:absolute;left:0;top:0;border:1px solid var(--spatial-hair-dim);border-radius:var(--spatial-radius-folder);background:linear-gradient(180deg,#fff,var(--spatial-folder));box-shadow:var(--spatial-shadow-rest);pointer-events:none}
.spatial-desk[data-theme=dark] .spatial-folder__peek{background:var(--spatial-folder)}
.spatial-folder__body{position:relative;z-index:3;display:flex;align-items:center;justify-content:space-between;min-height:72px;padding:14px 16px;border:1px solid var(--spatial-hair);border-radius:var(--spatial-radius-folder);background:linear-gradient(180deg,color-mix(in srgb,var(--spatial-card) 85%,transparent),color-mix(in srgb,var(--spatial-folder) 90%,transparent));box-shadow:var(--spatial-shadow-folder);backdrop-filter:blur(10px);transition:transform 280ms var(--spatial-spring),box-shadow 280ms var(--spatial-ease)}
.spatial-folder__body:hover{box-shadow:var(--spatial-shadow-hover);transform:translateY(-4px) scale(1.01)}
.spatial-folder__label{display:flex;gap:10px;align-items:center;min-width:0;font-size:11px;font-weight:650;letter-spacing:.12em;text-transform:uppercase}
.spatial-folder__label>span:nth-child(2){overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.spatial-folder__count{flex-shrink:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px;font-weight:500;color:var(--spatial-dim);letter-spacing:.04em;text-transform:none}
.spatial-folder__toggle{display:grid;place-items:center;width:28px;height:28px;border:1px solid var(--spatial-hair-dim);border-radius:999px;background:color-mix(in srgb,var(--spatial-card) 80%,transparent);color:var(--spatial-muted);font-size:12px;cursor:pointer;transition:transform 220ms var(--spatial-spring),background 160ms var(--spatial-ease)}
.spatial-folder__toggle:hover{color:var(--spatial-text);background:var(--spatial-card-raised);transform:scale(1.08)}
.spatial-card{position:absolute;z-index:5;display:flex;flex-direction:column;gap:8px;padding:18px 18px 14px;overflow:hidden;border:1px solid var(--spatial-hair-dim);border-radius:var(--spatial-radius-card);background:var(--spatial-card);box-shadow:var(--spatial-shadow-rest);color:inherit;text-align:left;cursor:pointer;transform-origin:center center;transition:transform 300ms var(--spatial-spring),box-shadow 260ms var(--spatial-ease),background 180ms var(--spatial-ease);contain:layout paint;-webkit-tap-highlight-color:transparent}
.spatial-card::before{position:absolute;inset:0;border-radius:inherit;background:linear-gradient(180deg,rgba(255,255,255,.55),transparent 28%);pointer-events:none;content:""}
.spatial-desk[data-theme=dark] .spatial-card::before{background:linear-gradient(180deg,rgba(255,255,255,.05),transparent 30%)}
.spatial-card::after{position:absolute;inset:0;border-radius:inherit;box-shadow:inset 0 1px 0 rgba(255,255,255,.65);pointer-events:none;content:""}
.spatial-desk[data-theme=dark] .spatial-card::after{box-shadow:inset 0 1px 0 rgba(255,255,255,.06)}
.spatial-card:hover,.spatial-card:focus-visible{z-index:30;background:var(--spatial-card-raised);box-shadow:var(--spatial-shadow-hover);outline:none;transform:translateY(-12px) scale(1.04) rotate(var(--card-rot,0deg))!important}
.spatial-card.is-selected{z-index:31;box-shadow:var(--spatial-shadow-hover),0 0 0 1.5px color-mix(in srgb,var(--card-accent,var(--spatial-accent)) 55%,transparent)}
.spatial-card--sticky{border-color:transparent;background:color-mix(in srgb,var(--card-accent,#ffd60a) 82%,white);box-shadow:0 1px 1px rgba(0,0,0,.05),0 10px 22px color-mix(in srgb,var(--card-accent,#ffd60a) 32%,transparent)}
.spatial-desk[data-theme=dark] .spatial-card--sticky{background:color-mix(in srgb,var(--card-accent,#ffd60a) 48%,#2c2c2e)}
.spatial-card--sticky::before{background:linear-gradient(180deg,rgba(255,255,255,.35),transparent 40%)}
.spatial-card__title{position:relative;z-index:1;font-size:14px;font-weight:600;line-height:1.28;letter-spacing:-.022em}
.spatial-card--sticky .spatial-card__title{font-size:13px;font-weight:650}
.spatial-card__summary{position:relative;z-index:1;display:-webkit-box;overflow:hidden;color:var(--spatial-muted);font-size:12px;line-height:1.45;-webkit-box-orient:vertical;-webkit-line-clamp:4}
.spatial-card__meta{position:relative;z-index:1;display:flex;flex-wrap:wrap;gap:5px;margin-top:auto}
.spatial-chip{padding:2px 7px;border:1px solid var(--spatial-hair-dim);border-radius:999px;color:var(--spatial-dim);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:8.5px;letter-spacing:.04em;text-transform:uppercase;background:color-mix(in srgb,var(--spatial-paper) 55%,transparent)}
.spatial-toolbar{position:absolute;bottom:24px;left:50%;z-index:40;display:flex;gap:2px;align-items:center;padding:6px 8px;border:1px solid rgba(255,255,255,.08);border-radius:999px;background:rgba(28,28,30,.72);box-shadow:0 8px 32px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.08);backdrop-filter:blur(22px) saturate(160%);-webkit-backdrop-filter:blur(22px) saturate(160%);transform:translateX(-50%);color:#f5f5f7}
.spatial-desk[data-theme=light] .spatial-toolbar{border-color:var(--spatial-hair-dim);background:color-mix(in srgb,var(--spatial-card) 78%,transparent);box-shadow:var(--spatial-shadow-hover);color:var(--spatial-text)}
.spatial-toolbar input{width:min(200px,32vw);padding:7px 12px;border:1px solid transparent;border-radius:999px;background:rgba(255,255,255,.08);color:inherit;font:inherit;font-size:12.5px;outline:none}
.spatial-desk[data-theme=light] .spatial-toolbar input{background:color-mix(in srgb,var(--spatial-paper) 70%,transparent)}
.spatial-toolbar input:focus{border-color:rgba(255,255,255,.14);background:rgba(255,255,255,.12)}
.spatial-toolbar button{display:grid;place-items:center;width:32px;height:32px;border:0;border-radius:999px;background:transparent;color:rgba(245,245,247,.72);cursor:pointer;transition:background 160ms var(--spatial-ease),color 160ms var(--spatial-ease),transform 200ms var(--spatial-spring)}
.spatial-desk[data-theme=light] .spatial-toolbar button{color:var(--spatial-muted)}
.spatial-toolbar button:hover{background:rgba(255,255,255,.1);color:#fff;transform:scale(1.08)}
.spatial-desk[data-theme=light] .spatial-toolbar button:hover{background:color-mix(in srgb,var(--spatial-paper) 80%,transparent);color:var(--spatial-text)}
.spatial-toolbar__count{min-width:3.2rem;padding:0 6px;color:rgba(245,245,247,.55);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;text-align:center}
.spatial-desk[data-theme=light] .spatial-toolbar__count{color:var(--spatial-dim)}
.spatial-status{position:absolute;top:16px;left:50%;z-index:35;padding:6px 14px;border:1px solid var(--spatial-hair-dim);border-radius:999px;background:color-mix(in srgb,var(--spatial-card) 82%,transparent);color:var(--spatial-muted);font-size:11px;box-shadow:var(--spatial-shadow-rest);backdrop-filter:blur(14px);transform:translateX(-50%);pointer-events:none}
.spatial-corner{position:absolute;z-index:36;display:flex;gap:6px;align-items:center}
.spatial-corner--bl{bottom:28px;left:22px}
.spatial-corner--br{bottom:28px;right:22px}
.spatial-corner button{display:grid;place-items:center;width:36px;height:36px;border:1px solid var(--spatial-hair-dim);border-radius:999px;background:color-mix(in srgb,var(--spatial-card) 80%,transparent);color:var(--spatial-muted);box-shadow:var(--spatial-shadow-rest);backdrop-filter:blur(14px);cursor:pointer;transition:transform 200ms var(--spatial-spring),box-shadow 200ms var(--spatial-ease)}
.spatial-corner button:hover{transform:scale(1.06);box-shadow:var(--spatial-shadow-hover);color:var(--spatial-text)}
@media (prefers-reduced-motion:reduce){.spatial-card,.spatial-folder__body,.spatial-folder__toggle,.spatial-toolbar button,.spatial-corner button{transition:none!important}}
`

function ensureCss() {
  if (typeof document === 'undefined') return
  if (document.getElementById('spatial-desk-css')) return
  const el = document.createElement('style')
  el.id = 'spatial-desk-css'
  el.textContent = CSS
  document.head.appendChild(el)
}

// Character-class regexes only — never \\ / inside /.../ (breaks ESM parse).
function classifyDoc(relOrName) {
  const s = String(relOrName || '').split('\\').join('/')
  const rules = [
    { re: /(^|[/])(prd|product[-_ ]?requirements?)([.]|$)/i, type: 'prd', priority: 100, stack: 'Scope', accent: '#0a84ff' },
    { re: /(^|[/])(frd|functional[-_ ]?requirements?)([.]|$)/i, type: 'frd', priority: 96, stack: 'Scope', accent: '#0a84ff' },
    { re: /(north[-_ ]?star|vision|product[-_ ]?brief)/i, type: 'prd', priority: 94, stack: 'Scope', accent: '#0a84ff' },
    { re: /roadmap/i, type: 'roadmap', priority: 90, stack: 'Plan', accent: '#30d158' },
    { re: /timeline|milestones?/i, type: 'timeline', priority: 86, stack: 'Plan', accent: '#30d158' },
    { re: /\bepics?\b/i, type: 'epic', priority: 82, stack: 'Plan', accent: '#30d158' },
    { re: /\bsprints?\b/i, type: 'sprint', priority: 78, stack: 'Plan', accent: '#30d158' },
    { re: /(adr|decision|decisions?[-_ ]?log|rfc)/i, type: 'decision', priority: 88, stack: 'Decisions', accent: '#ffd60a', kind: 'sticky' },
    { re: /(architecture|spec|design[-_ ]?doc|contract)/i, type: 'spec', priority: 84, stack: 'Specs', accent: '#bf5af2' },
    { re: /(^|[/])(agents|claude|cursor|hermes)[.]md$/i, type: 'context', priority: 72, stack: 'Context', accent: '#64d2ff' },
    { re: /(^|[/])readme([.]mdx?)?$/i, type: 'doc', priority: 68, stack: 'Context', accent: '#8e8e93' },
    { re: /[/]docs[/]/i, type: 'doc', priority: 55, stack: 'Docs', accent: '#8e8e93' },
    { re: /[.](md|mdx)$/i, type: 'doc', priority: 30, stack: 'Docs', accent: '#8e8e93' }
  ]
  for (const r of rules) {
    if (r.re.test(s)) {
      return { type: r.type, priority: r.priority, stack: r.stack, accent: r.accent, kind: r.kind || 'note' }
    }
  }
  return { type: 'doc', priority: 20, stack: 'Docs', accent: '#8e8e93', kind: 'note' }
}

function titleFromPath(name) {
  return String(name || '')
    .replace(/[.](md|mdx|txt)$/i, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function hashRot(id) {
  let h = 0
  const s = String(id || '')
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return ((h % 70) - 35) / 12
}

const STACK_META = {
  Scope: { color: '#0a84ff', order: 0 },
  Plan: { color: '#30d158', order: 1 },
  Decisions: { color: '#ffd60a', order: 2 },
  Specs: { color: '#bf5af2', order: 3 },
  Context: { color: '#64d2ff', order: 4 },
  Docs: { color: '#8e8e93', order: 5 }
}

const STICKY_PALETTE = ['#ffd60a', '#30d158', '#64d2ff', '#ff9f0a', '#bf5af2', '#ff375f']

function layoutDesk(docs, roots) {
  const ranked = docs
    .map(doc => {
      const cls = classifyDoc(doc.rel || doc.name)
      return { doc, ...cls, title: titleFromPath(doc.name), summary: doc.rel || doc.path }
    })
    .sort((a, b) => b.priority - a.priority || a.title.localeCompare(b.title))

  const byStack = new Map()
  for (const item of ranked) {
    const list = byStack.get(item.stack) || []
    list.push(item)
    byStack.set(item.stack, list)
  }

  const stackNames = [...byStack.keys()].sort((a, b) => {
    const pa = Math.max(...(byStack.get(a) || []).map(x => x.priority))
    const pb = Math.max(...(byStack.get(b) || []).map(x => x.priority))
    if (pb !== pa) return pb - pa
    return (STACK_META[a]?.order ?? 9) - (STACK_META[b]?.order ?? 9)
  })

  let surfaceLeft = 16
  const stacks = stackNames.slice(0, 8).map((name, si) => {
    const items = byStack.get(name) || []
    const meta = STACK_META[name] || { color: '#8e8e93', order: 9 }
    const stackPriority = items[0]?.priority ?? 0
    // High-priority left expanded; long-tail collapsed piles
    const collapse = si >= 3 || stackPriority < 70 || surfaceLeft <= 0
    const take = collapse
      ? Math.min(items.length, 5)
      : Math.min(items.length, Math.max(3, Math.min(7, surfaceLeft)))
    if (!collapse) surfaceLeft -= take

    const cards = items.slice(0, take).map((item, ci) => {
      const id = item.doc.path
      const sticky = item.kind === 'sticky'
      const col = ci % 3
      const row = Math.floor(ci / 3)
      const driftX = ((ci * 17) % 23) - 11
      const driftY = ((ci * 13) % 19) - 9
      const accent = sticky ? STICKY_PALETTE[ci % STICKY_PALETTE.length] : item.accent
      return {
        id,
        title: item.title,
        summary: item.summary,
        type: item.type,
        kind: item.kind,
        status: item.priority >= 80 ? 'focus' : item.priority >= 50 ? 'active' : 'ref',
        tags: [item.stack.toLowerCase()],
        priority: item.priority,
        sourcePath: item.doc.path,
        x: sticky ? 28 + (ci % 3) * 148 + driftX : col * 236 + driftX + row * 14,
        y: 96 + row * (sticky ? 128 : 168) + (col === 1 ? -18 : col === 2 ? 12 : 0) + driftY,
        rotation: hashRot(id),
        width: sticky ? 158 : 220,
        height: sticky ? 124 : 168,
        accent
      }
    })

    // Organic cluster positions — freeform scatter, not rigid grid
    const clusterX = 80 + si * 480 + (si % 2) * 40 + ((si * 37) % 36)
    const clusterY = 100 + (si % 3) * 70 + ((si * 19) % 40)

    return {
      id: name.toLowerCase(),
      name,
      x: clusterX,
      y: clusterY,
      rotation: ((si % 5) - 2) * 0.9,
      width: 268,
      height: 74,
      folderColor: meta.color,
      collapsed: collapse,
      priority: stackPriority,
      cards
    }
  })

  return {
    width: Math.max(3200, 360 + stacks.length * 560),
    height: 1400,
    stacks,
    scannedFrom: roots || []
  }
}

function filterDesk(desk, query) {
  const q = String(query || '').trim().toLowerCase()
  if (!q) return desk
  return {
    ...desk,
    stacks: desk.stacks
      .map(stack => ({
        ...stack,
        cards: stack.cards.filter(c =>
          [c.title, c.summary, c.type, c.status, stack.name, c.sourcePath || '', ...(c.tags || [])]
            .join(' ')
            .toLowerCase()
            .includes(q)
        )
      }))
      .filter(s => s.cards.length > 0)
  }
}

function cardCount(desk) {
  return desk.stacks.reduce((n, s) => n + s.cards.length, 0)
}

function seedDesk() {
  return layoutDesk(
    [
      { path: 'docs/PRD.md', name: 'PRD.md', rel: 'docs/PRD.md' },
      { path: 'docs/FRD.md', name: 'FRD.md', rel: 'docs/FRD.md' },
      { path: 'docs/ROADMAP.md', name: 'ROADMAP.md', rel: 'docs/ROADMAP.md' },
      { path: 'docs/decisions/ADR-001-spatial-desk.md', name: 'ADR-001-spatial-desk.md', rel: 'docs/decisions/ADR-001-spatial-desk.md' },
      { path: 'docs/decisions/ADR-002-kanban-split.md', name: 'ADR-002-kanban-split.md', rel: 'docs/decisions/ADR-002-kanban-split.md' },
      { path: 'docs/specs/interaction.md', name: 'interaction.md', rel: 'docs/specs/interaction.md' },
      { path: 'docs/specs/materials.md', name: 'materials.md', rel: 'docs/specs/materials.md' },
      { path: 'docs/timeline.md', name: 'timeline.md', rel: 'docs/timeline.md' },
      { path: 'AGENTS.md', name: 'AGENTS.md', rel: 'AGENTS.md' },
      { path: 'README.md', name: 'README.md', rel: 'README.md' },
      { path: 'docs/notes/misc.md', name: 'misc.md', rel: 'docs/notes/misc.md' }
    ],
    ['(seed)']
  )
}

const SKIP = new Set([
  '.git','node_modules','.venv','venv','dist','build','.next','coverage','__pycache__','.tox','target','.cache','vendor','.turbo'
])

function shouldSkipDir(name) {
  return SKIP.has(name) || String(name || '').startsWith('.')
}

function isDocFile(name) {
  return /[.](md|mdx|txt)$/i.test(String(name || ''))
}

function planWalk(entries, depth, maxDepth) {
  const docs = []
  const dirs = []
  for (const e of entries) {
    if (e.isDirectory) {
      if (depth < maxDepth && !shouldSkipDir(e.name)) dirs.push(e.path)
    } else if (isDocFile(e.name)) {
      docs.push(e.path)
    }
  }
  return { docs, dirs }
}

function desktop() {
  return globalThis.hermesDesktop || null
}

function join(root, name) {
  const r = String(root || '')
  if (r.endsWith('/') || r.endsWith('\\')) return r + name
  return r + '/' + name
}

function basename(p) {
  const parts = String(p || '').split('\\').join('/').split('/')
  return parts[parts.length - 1] || p
}

function relTo(root, full) {
  const r = String(root || '').split('\\').join('/').replace(/[/]+$/, '')
  const f = String(full || '').split('\\').join('/')
  if (f.startsWith(r + '/')) return f.slice(r.length + 1)
  return f
}

async function listDir(path) {
  const b = desktop()
  if (!b || typeof b.readDir !== 'function') return []
  try {
    const res = await b.readDir(path)
    return (res && res.entries) || []
  } catch {
    return []
  }
}

async function walkDocs(root, maxDepth, maxFiles) {
  maxDepth = maxDepth == null ? 3 : maxDepth
  maxFiles = maxFiles == null ? 80 : maxFiles
  const out = []
  const queue = [{ path: root, depth: 0 }]
  const seen = new Set()
  while (queue.length && out.length < maxFiles) {
    const cur = queue.shift()
    if (seen.has(cur.path)) continue
    seen.add(cur.path)
    const entries = await listDir(cur.path)
    const normalized = entries.map(e => ({
      name: e.name,
      path: e.path || join(cur.path, e.name),
      isDirectory: Boolean(e.isDirectory || e.type === 'directory' || e.type === 'dir')
    }))
    const planned = planWalk(normalized, cur.depth, maxDepth)
    for (const p of planned.docs) {
      if (out.length >= maxFiles) break
      out.push({ path: p, name: basename(p), rel: relTo(root, p) })
    }
    for (const d of planned.dirs) queue.push({ path: d, depth: cur.depth + 1 })
  }
  for (const sub of ['docs', 'design', 'specs', 'architecture', '.zeros', 'product']) {
    if (out.length >= maxFiles) break
    const p = join(root, sub)
    for (const e of await listDir(p)) {
      if (out.length >= maxFiles) break
      if (shouldSkipDir(e.name)) continue
      const full = e.path || join(p, e.name)
      if (isDocFile(e.name)) out.push({ path: full, name: e.name, rel: relTo(root, full) })
    }
  }
  return [...new Map(out.map(d => [d.path, d])).values()]
}

async function resolveScanRoots(cwd, projectPaths) {
  const roots = [...(projectPaths || []), cwd]
    .map(p => String(p || '').trim())
    .filter(Boolean)
  const uniq = []
  for (const r of roots) {
    if (!uniq.some(u => u === r || r.startsWith(u + '/') || r.startsWith(u + '\\'))) uniq.push(r)
  }
  return uniq.slice(0, 4)
}

async function scanProjectDocs(roots) {
  const all = []
  for (const root of roots) all.push(...(await walkDocs(root)))
  return [...new Map(all.map(d => [d.path, d])).values()]
}

async function projectPaths() {
  try {
    const payload = await host.request('projects.list')
    const projects = (payload && payload.projects) || []
    const paths = []
    for (const p of projects) {
      if (p.primary_path) paths.push(p.primary_path)
      for (const f of p.folders || []) if (f.path) paths.push(f.path)
    }
    const activeId = payload && payload.active_id
    if (!activeId) return paths
    const ap = projects.find(p => p.id === activeId)
    if (!ap) return paths
    const prefer = [ap.primary_path, ...(ap.folders || []).map(f => f.path)].filter(Boolean)
    return [...prefer, ...paths.filter(p => prefer.indexOf(p) < 0)]
  } catch {
    return []
  }
}

function SpatialDeskPage() {
  ensureCss()
  const stageRef = useRef(null)
  const grab = useGrabScroll(stageRef)
  const cwd = useValue(host.state.cwd)
  const [query, setQuery] = useState('')
  const [theme, setTheme] = useState('light')
  const [scale, setScale] = useState(1)
  const [selected, setSelected] = useState(null)
  const [collapsed, setCollapsed] = useState({})
  const [desk, setDesk] = useState(() => seedDesk())
  const [status, setStatus] = useState('scanning')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setStatus('scanning')
      try {
        const roots = await resolveScanRoots(cwd || '', await projectPaths())
        const docs = roots.length ? await scanProjectDocs(roots) : []
        if (cancelled) return
        if (!docs.length) {
          setDesk(seedDesk())
          setStatus('seed')
          const seed = seedDesk()
          const c = {}
          for (const s of seed.stacks) c[s.id] = s.collapsed
          setCollapsed(c)
          return
        }
        const next = layoutDesk(docs, roots)
        setDesk(next)
        const c = {}
        for (const s of next.stacks) c[s.id] = s.collapsed
        setCollapsed(c)
        setStatus('ready')
        requestAnimationFrame(() => {
          const el = stageRef.current
          if (!el) return
          el.scrollLeft = Math.max(0, next.width * 0.06)
          el.scrollTop = Math.max(0, next.height * 0.04)
        })
      } catch {
        if (!cancelled) {
          setDesk(seedDesk())
          setStatus('seed')
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [cwd])

  const shown = useMemo(() => filterDesk(desk, query), [desk, query])
  const total = cardCount(desk)
  const visible = cardCount(shown)

  return _js('div', {
    className: 'spatial-desk',
    'data-theme': theme === 'dark' ? 'dark' : 'light',
    'data-testid': 'spatial-desk-root',
    children: [
      status === 'scanning' && _j('div', { className: 'spatial-status', children: 'Scanning project papers…' }),
      _j('div', {
        ref: stageRef,
        className: cn('spatial-desk__stage', grab.grabbing && 'is-grabbing'),
        'data-testid': 'spatial-stage',
        onMouseDown: grab.onMouseDown,
        children: _j('div', {
          className: 'spatial-desk__world',
          style: { width: desk.width, height: desk.height, transform: 'scale(' + scale + ')', transformOrigin: '0 0' },
          children: shown.stacks.map(stack => {
            const isCollapsed = collapsed[stack.id] != null ? collapsed[stack.id] : stack.collapsed
            const peeks = stack.cards.slice(0, 3)
            return _js('div', {
              key: stack.id,
              className: 'spatial-folder',
              style: {
                left: stack.x,
                top: stack.y,
                width: Math.max(stack.width, 280),
                transform: 'rotate(' + stack.rotation + 'deg)'
              },
              children: [
                isCollapsed &&
                  peeks.map((card, i) =>
                    _j('div', {
                      key: 'peek-' + card.id,
                      className: 'spatial-folder__peek',
                      style: {
                        width: stack.width,
                        height: stack.height + 10,
                        zIndex: 1 - i,
                        transform:
                          'translate(' +
                          (12 + i * 8) +
                          'px,' +
                          (-12 - i * 9) +
                          'px) rotate(' +
                          (-6 + i * 4) +
                          'deg)',
                        opacity: 0.62 - i * 0.14
                      }
                    })
                  ),
                _j('div', { className: 'spatial-folder__tab', style: { background: stack.folderColor } }),
                _js('div', {
                  className: 'spatial-folder__body',
                  style: { width: stack.width, minHeight: stack.height },
                  children: [
                    _js('div', {
                      className: 'spatial-folder__label',
                      children: [
                        _j('span', {
                          'aria-hidden': true,
                          style: { width: 9, height: 9, borderRadius: 3, background: stack.folderColor }
                        }),
                        _j('span', { children: stack.name }),
                        _j('span', { className: 'spatial-folder__count', children: stack.cards.length })
                      ]
                    }),
                    _j('button', {
                      type: 'button',
                      className: 'spatial-folder__toggle',
                      'aria-expanded': !isCollapsed,
                      onClick: () =>
                        setCollapsed(c => {
                          const next = { ...c }
                          next[stack.id] = !isCollapsed
                          return next
                        }),
                      children: isCollapsed ? '▸' : '▾'
                    })
                  ]
                }),
                !isCollapsed &&
                  stack.cards.map((card, i) =>
                    _js('button', {
                      key: card.id,
                      type: 'button',
                      className: cn(
                        'spatial-card',
                        card.kind === 'sticky' && 'spatial-card--sticky',
                        selected && selected.id === card.id && 'is-selected'
                      ),
                      'data-testid': 'spatial-card-' + card.id,
                      style: {
                        left: card.x + (i % 2 === 0 ? -8 : 12),
                        top: card.y + Math.floor(i / 3) * 6,
                        width: card.width,
                        height: card.height,
                        transform: 'rotate(' + card.rotation + 'deg)',
                        '--card-rot': card.rotation + 'deg',
                        '--card-accent': card.accent
                      },
                      onClick: () => setSelected(card),
                      onMouseDown: e => e.stopPropagation(),
                      children: [
                        _j('div', { className: 'spatial-card__title', children: card.title }),
                        card.kind !== 'sticky' &&
                          _j('div', { className: 'spatial-card__summary', children: card.summary }),
                        _js('div', {
                          className: 'spatial-card__meta',
                          children: [
                            _j('span', { className: 'spatial-chip', children: card.type }),
                            _j('span', {
                              className: 'spatial-chip',
                              style: { color: card.accent, borderColor: card.accent + '55' },
                              children: 'P' + card.priority
                            })
                          ]
                        })
                      ]
                    })
                  )
              ]
            })
          })
        })
      }),
      _js('div', {
        className: 'spatial-toolbar',
        onMouseDown: e => e.stopPropagation(),
        children: [
          _j('input', {
            'aria-label': 'Filter cards',
            placeholder: 'Filter papers…',
            value: query,
            onChange: e => setQuery(e.target.value)
          }),
          _j(Tip, {
            label: 'Zoom out',
            children: _j('button', {
              type: 'button',
              onClick: () => setScale(s => Math.max(0.45, +(s - 0.1).toFixed(2))),
              children: _j(icons.ZoomOut, { size: 15 })
            })
          }),
          _j('span', { className: 'spatial-toolbar__count', children: Math.round(scale * 100) + '%' }),
          _j(Tip, {
            label: 'Zoom in',
            children: _j('button', {
              type: 'button',
              onClick: () => setScale(s => Math.min(1.6, +(s + 0.1).toFixed(2))),
              children: _j(icons.ZoomIn, { size: 15 })
            })
          }),
          _j(Tip, {
            label: 'Reset view',
            children: _j('button', {
              type: 'button',
              onClick: () => {
                setScale(1)
                const el = stageRef.current
                if (el) {
                  el.scrollLeft = Math.max(0, desk.width * 0.06)
                  el.scrollTop = Math.max(0, desk.height * 0.04)
                }
              },
              children: _j(icons.Maximize, { size: 14 })
            })
          }),
          _j(Tip, {
            label: theme === 'light' ? 'Dark desk' : 'Light desk',
            children: _j('button', {
              type: 'button',
              onClick: () => setTheme(t => (t === 'light' ? 'dark' : 'light')),
              children: theme === 'light' ? _j(icons.Moon, { size: 14 }) : _j(icons.Sun, { size: 14 })
            })
          }),
          _j('span', {
            className: 'spatial-toolbar__count',
            children: status === 'scanning' ? '…' : status === 'seed' ? 'demo' : visible + '/' + total
          })
        ]
      }),
      _j(Dialog, {
        open: selected !== null,
        onOpenChange: open => {
          if (!open) setSelected(null)
        },
        children: _j(DialogContent, {
          className: 'max-w-md border-border/60 bg-background/95 backdrop-blur-xl',
          children: selected
            ? [
                _js(DialogHeader, {
                  children: [
                    _j(DialogTitle, { className: 'pr-8', children: selected.title }),
                    _j(DialogDescription, { children: selected.summary })
                  ]
                }),
                _js('div', {
                  className: 'mt-2 flex flex-wrap gap-1.5',
                  children: [
                    _j(Badge, { variant: 'muted', children: selected.type }),
                    _j(Badge, { variant: 'outline', children: 'P' + selected.priority }),
                    selected.sourcePath && _j(Badge, { variant: 'outline', children: selected.sourcePath })
                  ]
                })
              ]
            : null
        })
      })
    ]
  })
}

function open() {
  host.navigate('/spatial')
}

export default {
  id: ID,
  name: 'Spatial',
  defaultEnabled: true,
  register(ctx) {
    ensureCss()
    ctx.registerMany([
      {
        id: 'page',
        area: ROUTES_AREA,
        data: { path: '/spatial' },
        render: () => _j(SpatialDeskPage, {})
      },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        order: 55,
        data: { codicon: 'notebook', label: 'Spatial', path: '/spatial' }
      },
      {
        id: 'open',
        area: PALETTE_AREA,
        data: {
          id: 'spatial.open',
          label: 'Spatial: Open desk',
          keywords: ['spatial', 'canvas', 'desk', 'prd'],
          run: open
        }
      },
      {
        id: 'open',
        area: KEYBINDS_AREA,
        data: {
          id: 'spatial.open',
          category: 'view',
          defaults: ['mod+alt+s'],
          label: 'Spatial: Open desk',
          run: open
        }
      }
    ])
  }
}
