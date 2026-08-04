/** Spatial desk — fidelity runtime plugin for packaged Hermes Desktop.
 *  Inline pan/zoom + CSS springs (packaged SDK has no motion/useZoomPan until rebuild).
 */
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
  useValue
} from '@hermes/plugin-sdk'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { jsx as _j, jsxs as _js } from 'react/jsx-runtime'

const ID = 'spatial'
const CSS = `
.spatial-desk{
  --sp-canvas:#e8e8ea;
  --sp-paper:#f4f4f5;
  --sp-card:#ffffff;
  --sp-ink:#1c1c1e;
  --sp-muted:#636366;
  --sp-dim:#8e8e93;
  --sp-hair:rgba(0,0,0,.08);
  --sp-hair2:rgba(0,0,0,.045);
  --sp-accent:#0a84ff;
  --sp-sh:
    0 .5px 1px rgba(0,0,0,.04),
    0 2px 4px rgba(0,0,0,.035),
    0 10px 24px rgba(0,0,0,.07),
    0 28px 56px rgba(0,0,0,.06);
  --sp-sh-h:
    0 1px 2px rgba(0,0,0,.05),
    0 12px 28px rgba(0,0,0,.1),
    0 36px 72px rgba(0,0,0,.12);
  --sp-r:20px;
  --sp-spring:cubic-bezier(.34,1.56,.64,1);
  --sp-ease:cubic-bezier(.22,1,.36,1);
  position:relative;display:flex;min-height:0;flex:1;flex-direction:column;overflow:hidden;
  color:var(--sp-ink);background:var(--sp-canvas);
  font-family:ui-sans-serif,system-ui,-apple-system,"SF Pro Text","Segoe UI",sans-serif;
  -webkit-font-smoothing:antialiased;
}
.spatial-desk[data-theme=dark]{
  --sp-canvas:#1c1c1e;--sp-paper:#2c2c2e;--sp-card:#2c2c2e;--sp-ink:#f5f5f7;--sp-muted:#a1a1a6;--sp-dim:#6c6c70;
  --sp-hair:rgba(255,255,255,.1);--sp-hair2:rgba(255,255,255,.06);
  --sp-sh:0 1px 2px rgba(0,0,0,.4),0 12px 28px rgba(0,0,0,.45),0 32px 64px rgba(0,0,0,.4);
  --sp-sh-h:0 2px 6px rgba(0,0,0,.5),0 20px 40px rgba(0,0,0,.55),0 48px 80px rgba(0,0,0,.45);
}
.spatial-desk__stage{
  position:relative;min-height:0;flex:1;overflow:hidden;cursor:grab;touch-action:none;
  background:
    radial-gradient(100% 80% at 50% 40%, color-mix(in srgb,var(--sp-paper) 90%,transparent) 0%, transparent 68%),
    radial-gradient(50% 40% at 15% 85%, rgba(10,132,255,.035), transparent 55%),
    radial-gradient(40% 35% at 88% 20%, rgba(191,90,242,.03), transparent 50%),
    var(--sp-canvas);
}
.spatial-desk__stage.is-panning{cursor:grabbing;user-select:none}
.spatial-desk__stage.is-panning .spatial-item{transition:none!important}
.spatial-desk__world{
  position:absolute;left:50%;top:45%;
  transform-origin:0 0;will-change:transform;
}
.spatial-item{
  position:absolute;transform-origin:center center;
  transform:rotate(var(--rot,0deg));
  animation:spatial-enter 520ms var(--sp-spring) both;
  transition:transform 320ms var(--sp-spring), box-shadow 280ms var(--sp-ease), filter 200ms var(--sp-ease);
  contain:layout paint;
}
.spatial-item:hover{z-index:40!important;filter:drop-shadow(0 18px 28px rgba(0,0,0,.14))}
.spatial-item:hover{transform:translateY(-12px) scale(1.04) rotate(var(--rot,0deg))!important}
@keyframes spatial-enter{
  from{opacity:0;transform:translateY(18px) scale(.9) rotate(var(--rot,0deg))}
  to{opacity:1;transform:translateY(0) scale(1) rotate(var(--rot,0deg))}
}
/* paper card */
.spatial-paper{
  display:flex;flex-direction:column;gap:8px;
  padding:18px 18px 14px;overflow:hidden;text-align:left;cursor:pointer;
  border:1px solid var(--sp-hair2);border-radius:var(--sp-r);
  background:var(--sp-card);box-shadow:var(--sp-sh);color:inherit;
  width:100%;height:100%;
}
.spatial-paper::before{
  content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  background:linear-gradient(180deg,rgba(255,255,255,.65),transparent 32%);
}
.spatial-desk[data-theme=dark] .spatial-paper::before{background:linear-gradient(180deg,rgba(255,255,255,.05),transparent 30%)}
.spatial-paper::after{
  content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.7);
}
.spatial-item:hover .spatial-paper{box-shadow:var(--sp-sh-h)}
.spatial-item.is-selected .spatial-paper{
  box-shadow:var(--sp-sh-h),0 0 0 1.5px color-mix(in srgb,var(--accent,var(--sp-accent)) 55%,transparent);
}
.spatial-paper__title{position:relative;z-index:1;font-size:14px;font-weight:650;letter-spacing:-.022em;line-height:1.25}
.spatial-paper__body{
  position:relative;z-index:1;flex:1;overflow:hidden;color:var(--sp-muted);
  font-size:12px;line-height:1.45;white-space:pre-wrap;
  display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:6;
}
.spatial-paper__meta{position:relative;z-index:1;display:flex;flex-wrap:wrap;gap:5px;margin-top:auto}
.spatial-chip{
  padding:2px 7px;border:1px solid var(--sp-hair2);border-radius:999px;
  color:var(--sp-dim);font:500 8.5px/1.2 ui-monospace,SFMono-Regular,Menlo,monospace;
  letter-spacing:.04em;text-transform:uppercase;
  background:color-mix(in srgb,var(--sp-paper) 55%,transparent);
}
/* sticky */
.spatial-sticky{
  display:flex;flex-direction:column;justify-content:space-between;
  width:100%;height:100%;padding:16px;border:0;border-radius:14px;cursor:pointer;text-align:left;color:#1c1c1e;
  background:color-mix(in srgb,var(--accent,#ffd60a) 86%,#fff);
  box-shadow:0 1px 1px rgba(0,0,0,.05),0 10px 22px color-mix(in srgb,var(--accent,#ffd60a) 34%,transparent);
}
.spatial-desk[data-theme=dark] .spatial-sticky{color:#f5f5f7;background:color-mix(in srgb,var(--accent,#ffd60a) 48%,#2c2c2e)}
.spatial-item:hover .spatial-sticky{box-shadow:0 16px 36px color-mix(in srgb,var(--accent,#ffd60a) 40%,transparent)}
.spatial-sticky__title{font-size:13px;font-weight:700;line-height:1.3;letter-spacing:-.01em}
.spatial-sticky__hint{font-size:10px;opacity:.55;font-weight:600;letter-spacing:.06em;text-transform:uppercase}
/* media tile (visual density — original abstract, not Spatial assets) */
.spatial-media{
  width:100%;height:100%;border:1px solid var(--sp-hair2);border-radius:var(--sp-r);overflow:hidden;
  box-shadow:var(--sp-sh);cursor:pointer;position:relative;padding:0;background:#111;
}
.spatial-media__art{
  position:absolute;inset:0;
  background:
    radial-gradient(80% 70% at 30% 20%, color-mix(in srgb,var(--accent,#0a84ff) 55%,transparent), transparent 55%),
    radial-gradient(70% 60% at 80% 80%, color-mix(in srgb,var(--accent2,#bf5af2) 45%,transparent), transparent 50%),
    linear-gradient(145deg,#1a1a1e,#0c0c0e 55%,#151518);
}
.spatial-media__label{
  position:absolute;left:12px;right:12px;bottom:12px;z-index:1;
  color:#f5f5f7;font-size:12px;font-weight:600;letter-spacing:-.01em;
  text-shadow:0 1px 8px rgba(0,0,0,.55);
}
.spatial-item:hover .spatial-media{box-shadow:var(--sp-sh-h)}
/* folder pile */
.spatial-pile{position:absolute;pointer-events:auto}
.spatial-pile__peek{
  position:absolute;left:0;top:0;border:1px solid var(--sp-hair2);border-radius:18px;
  background:linear-gradient(180deg,#fff,var(--sp-paper));box-shadow:var(--sp-sh);pointer-events:none;
}
.spatial-desk[data-theme=dark] .spatial-pile__peek{background:var(--sp-paper)}
.spatial-pile__tab{
  position:absolute;top:-12px;left:18px;z-index:4;width:92px;height:15px;border-radius:9px 9px 0 0;
  box-shadow:0 -1px 0 rgba(255,255,255,.35) inset;
}
.spatial-pile__body{
  position:relative;z-index:3;display:flex;align-items:center;justify-content:space-between;
  min-height:70px;padding:14px 16px;border:1px solid var(--sp-hair);border-radius:18px;
  background:linear-gradient(180deg,color-mix(in srgb,var(--sp-card) 88%,transparent),var(--sp-paper));
  box-shadow:0 1px 2px rgba(0,0,0,.04),0 10px 24px rgba(0,0,0,.08);
  transition:transform 280ms var(--sp-spring),box-shadow 280ms var(--sp-ease);
}
.spatial-pile__body:hover{transform:translateY(-4px);box-shadow:var(--sp-sh-h)}
.spatial-pile__label{display:flex;gap:10px;align-items:center;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
.spatial-pile__count{font:500 9px ui-monospace,Menlo,monospace;color:var(--sp-dim);letter-spacing:.04em;text-transform:none}
.spatial-pile__toggle{
  width:28px;height:28px;border-radius:999px;border:1px solid var(--sp-hair2);
  background:color-mix(in srgb,var(--sp-card) 85%,transparent);color:var(--sp-muted);cursor:pointer;
  display:grid;place-items:center;transition:transform 220ms var(--sp-spring);
}
.spatial-pile__toggle:hover{transform:scale(1.08);color:var(--sp-ink)}
/* chrome */
.spatial-toolbar{
  position:absolute;bottom:22px;left:50%;z-index:50;transform:translateX(-50%);
  display:flex;gap:2px;align-items:center;padding:6px 8px;border-radius:999px;
  border:1px solid rgba(255,255,255,.1);
  background:rgba(22,22,24,.78);
  box-shadow:0 10px 40px rgba(0,0,0,.32), inset 0 1px 0 rgba(255,255,255,.1);
  backdrop-filter:blur(22px) saturate(160%);-webkit-backdrop-filter:blur(22px) saturate(160%);
  color:#f5f5f7;
}
.spatial-desk[data-theme=light] .spatial-toolbar{
  border-color:var(--sp-hair2);background:color-mix(in srgb,var(--sp-card) 78%,transparent);
  box-shadow:var(--sp-sh-h);color:var(--sp-ink);
}
.spatial-toolbar input{
  width:min(210px,34vw);padding:7px 12px;border:0;border-radius:999px;
  background:rgba(255,255,255,.1);color:inherit;font:inherit;font-size:12.5px;outline:none;
}
.spatial-desk[data-theme=light] .spatial-toolbar input{background:color-mix(in srgb,var(--sp-paper) 75%,transparent)}
.spatial-toolbar button{
  width:32px;height:32px;border:0;border-radius:999px;background:transparent;
  color:rgba(245,245,247,.72);cursor:pointer;display:grid;place-items:center;
  transition:transform 200ms var(--sp-spring),background 160ms var(--sp-ease),color 160ms;
}
.spatial-desk[data-theme=light] .spatial-toolbar button{color:var(--sp-muted)}
.spatial-toolbar button:hover{background:rgba(255,255,255,.12);color:#fff;transform:scale(1.08)}
.spatial-desk[data-theme=light] .spatial-toolbar button:hover{background:color-mix(in srgb,var(--sp-paper) 80%,transparent);color:var(--sp-ink)}
.spatial-toolbar__pct{
  min-width:3rem;text-align:center;font:500 10px ui-monospace,Menlo,monospace;opacity:.55;padding:0 4px;
}
.spatial-status{
  position:absolute;top:14px;left:50%;z-index:45;transform:translateX(-50%);
  padding:6px 14px;border-radius:999px;border:1px solid var(--sp-hair2);
  background:color-mix(in srgb,var(--sp-card) 82%,transparent);color:var(--sp-muted);
  font-size:11px;box-shadow:var(--sp-sh);backdrop-filter:blur(12px);pointer-events:none;
}
.spatial-corner{position:absolute;z-index:48;display:flex;gap:8px}
.spatial-corner--bl{left:18px;bottom:22px}
.spatial-corner--br{right:18px;bottom:22px}
.spatial-corner button{
  width:38px;height:38px;border-radius:999px;border:1px solid var(--sp-hair2);
  background:color-mix(in srgb,var(--sp-card) 82%,transparent);color:var(--sp-muted);
  box-shadow:var(--sp-sh);backdrop-filter:blur(14px);cursor:pointer;display:grid;place-items:center;
  transition:transform 200ms var(--sp-spring);
}
.spatial-corner button:hover{transform:scale(1.07);color:var(--sp-ink);box-shadow:var(--sp-sh-h)}
@media (prefers-reduced-motion:reduce){
  .spatial-item{animation:none!important;transition:none!important}
  .spatial-item:hover .spatial-paper,.spatial-item:hover .spatial-sticky,.spatial-item:hover .spatial-media{transform:none!important}
}
`

function ensureCss() {
  if (typeof document === 'undefined') return
  let el = document.getElementById('spatial-desk-css')
  if (!el) {
    el = document.createElement('style')
    el.id = 'spatial-desk-css'
    document.head.appendChild(el)
  }
  if (el.textContent !== CSS) el.textContent = CSS
}

const MIN_S = 0.28
const MAX_S = 3.2
const clamp = (n, a, b) => Math.min(b, Math.max(a, n))

/** Local pan/zoom — packaged Desktop SDK lacks useZoomPan. */
function useLocalZoomPan() {
  const [t, setT] = useState({ s: 0.85, x: 0, y: 0 })
  const drag = useRef(null)
  const [panning, setPanning] = useState(false)

  const zoomAt = useCallback((factor, cx = 0, cy = 0) => {
    setT(prev => {
      const s = clamp(prev.s * factor, MIN_S, MAX_S)
      const k = s / prev.s
      return { s, x: cx - k * (cx - prev.x), y: cy - k * (cy - prev.y) }
    })
  }, [])

  const onWheel = useCallback(
    e => {
      e.preventDefault()
      e.stopPropagation()
      const rect = e.currentTarget.getBoundingClientRect()
      const cx = e.clientX - rect.left - rect.width / 2
      const cy = e.clientY - rect.top - rect.height / 2
      zoomAt(e.deltaY < 0 ? 1.08 : 1 / 1.08, cx, cy)
    },
    [zoomAt]
  )

  const onPointerDown = useCallback(e => {
    if (e.button !== 0) return
    e.currentTarget.setPointerCapture(e.pointerId)
    setT(prev => {
      drag.current = { x: e.clientX - prev.x, y: e.clientY - prev.y }
      return prev
    })
    setPanning(true)
  }, [])

  const onPointerMove = useCallback(e => {
    if (!drag.current) return
    const st = drag.current
    setT(prev => ({ ...prev, x: e.clientX - st.x, y: e.clientY - st.y }))
  }, [])

  const endPan = useCallback(() => {
    drag.current = null
    setPanning(false)
  }, [])

  const reset = useCallback(() => setT({ s: 0.85, x: 0, y: 0 }), [])
  const zoomIn = useCallback(() => zoomAt(1.2), [zoomAt])
  const zoomOut = useCallback(() => zoomAt(1 / 1.2), [zoomAt])

  return {
    panning,
    scale: t.s,
    reset,
    zoomIn,
    zoomOut,
    stageProps: {
      onWheel,
      onPointerDown,
      onPointerMove,
      onPointerUp: endPan,
      onPointerLeave: endPan,
      onPointerCancel: endPan
    },
    worldStyle: {
      transform: 'translate(calc(-50% + ' + t.x + 'px), calc(-50% + ' + t.y + 'px)) scale(' + t.s + ')'
    }
  }
}

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
    if (r.re.test(s)) return { type: r.type, priority: r.priority, stack: r.stack, accent: r.accent, kind: r.kind || 'paper' }
  }
  return { type: 'doc', priority: 20, stack: 'Docs', accent: '#8e8e93', kind: 'paper' }
}

function titleFromPath(name) {
  return String(name || '')
    .replace(/[.](md|mdx|txt)$/i, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function hashN(id, mod) {
  let h = 0
  const s = String(id || '')
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h) % mod
}

function hashRot(id) {
  return (hashN(id, 70) - 35) / 12
}

const STICKY = ['#ffd60a', '#30d158', '#64d2ff', '#ff9f0a', '#bf5af2', '#ff375f', '#ac8e68']
const MEDIA_A = ['#0a84ff', '#bf5af2', '#ff375f', '#30d158', '#ff9f0a', '#64d2ff']
const MEDIA_B = ['#ff375f', '#0a84ff', '#ffd60a', '#bf5af2', '#30d158', '#ff9f0a']

/**
 * Freeform place-memory layout — papers scatter on the field.
 * Folders only for long-tail collapsed stacks (not the primary read).
 */
function layoutDesk(docs, roots) {
  const ranked = docs
    .map(doc => {
      const cls = classifyDoc(doc.rel || doc.name)
      return { doc, ...cls, title: titleFromPath(doc.name), summary: doc.body || doc.rel || doc.path }
    })
    .sort((a, b) => b.priority - a.priority || a.title.localeCompare(b.title))

  const items = []
  const piles = []
  const take = ranked.slice(0, 22)

  // Spiral / band scatter — dense center-left like Spatial boards
  const slots = []
  for (let i = 0; i < 28; i++) {
    const band = i % 4
    const col = Math.floor(i / 4)
    const baseX = 80 + col * 250 + (band === 1 ? 40 : band === 3 ? -20 : 0) + hashN('x' + i, 48) - 24
    const baseY = 70 + band * 210 + hashN('y' + i, 56) - 28 + (col % 2) * 30
    slots.push({ x: baseX, y: baseY })
  }

  take.forEach((item, i) => {
    const id = item.doc.path
    const slot = slots[i] || { x: 100 + i * 40, y: 100 + i * 30 }
    const rot = hashRot(id)
    const sticky = item.kind === 'sticky'
    // every 4th non-sticky becomes a media-like tile for visual density
    const media = !sticky && i % 4 === 2
    const kind = sticky ? 'sticky' : media ? 'media' : 'paper'
    const w = sticky ? 168 : media ? 210 : 236
    const h = sticky ? 148 : media ? 248 : 188
    items.push({
      id,
      kind,
      title: item.title,
      summary: item.summary,
      type: item.type,
      priority: item.priority,
      sourcePath: item.doc.path,
      x: slot.x,
      y: slot.y,
      rotation: rot,
      width: w,
      height: h,
      accent: sticky ? STICKY[i % STICKY.length] : item.accent,
      accent2: MEDIA_B[i % MEDIA_B.length],
      delay: Math.min(i * 0.035, 0.45)
    })
  })

  // Long-tail piles bottom-right
  const tail = ranked.slice(22, 40)
  if (tail.length) {
    const by = new Map()
    for (const t of tail) {
      const list = by.get(t.stack) || []
      list.push(t)
      by.set(t.stack, list)
    }
    let pi = 0
    for (const [name, list] of by) {
      piles.push({
        id: 'pile-' + name.toLowerCase(),
        name,
        x: 980 + (pi % 2) * 300,
        y: 720 + Math.floor(pi / 2) * 140,
        rotation: ((pi % 5) - 2) * 0.8,
        color: list[0].accent,
        count: list.length,
        collapsed: true,
        cards: list.slice(0, 4).map((c, ci) => ({
          id: c.doc.path + '-tail',
          title: c.title,
          summary: c.summary,
          type: c.type,
          priority: c.priority,
          kind: 'paper',
          accent: c.accent,
          x: 20 + ci * 12,
          y: 80 + ci * 10,
          rotation: hashRot(c.doc.path),
          width: 200,
          height: 140,
          sourcePath: c.doc.path,
          delay: 0
        }))
      })
      pi++
    }
  }

  return {
    width: 1800,
    height: 1200,
    items,
    piles,
    scannedFrom: roots || []
  }
}

function filterDesk(desk, query) {
  const q = String(query || '').trim().toLowerCase()
  if (!q) return desk
  const items = desk.items.filter(c =>
    [c.title, c.summary, c.type, c.sourcePath || ''].join(' ').toLowerCase().includes(q)
  )
  const piles = desk.piles
    .map(p => ({
      ...p,
      cards: (p.cards || []).filter(c =>
        [c.title, c.summary, c.type, p.name].join(' ').toLowerCase().includes(q)
      )
    }))
    .filter(p => p.cards.length > 0)
  return { ...desk, items, piles }
}

function seedDesk() {
  const bodies = {
    'PRD.md':
      'Spatial is the project-knowledge desk.\nKanban keeps execution; this surface holds PRD, FRD, roadmap, and decisions.\nRank by priority. Lay out only the most important papers first.',
    'FRD.md':
      'Functional requirements for desk scan, ranking, piles, pan/zoom, and paper open.\nMust load as a Desktop plugin without SyntaxError.',
    'ROADMAP.md': 'Wave 0 — load + materials.\nWave 1 — curator + freeform memory.\nWave 2 — motion parity with Spatial springs.',
    'ADR-001-spatial-desk.md': 'Decision: Spatial owns scope docs as collaborative paper.\nNot a tldraw fork. Original Hermes code.',
    'ADR-002-kanban-split.md': 'Kanban = execution state.\nSpatial = project scope projection.',
    'interaction.md':
      'Spring hover lift, folder fan-out, grab-pan stage, frosted pill chrome.\nStop propagation on cards so pan does not steal clicks.',
    'materials.md':
      'Cool canvas #e8e8ea, radius ~20px, multi-stop soft shadows, inset highlight, sticky full-fill.',
    'timeline.md': 'Milestones track load gate → fidelity slices → blind win vs references.',
    'AGENTS.md': 'Agents and humans curate the desk together.\nScan active project roots on open.',
    'README.md': 'Hermes Spatial desk — complementary to Kanban.\nOpen via sidebar or ⌘⌥S.',
    'vision.md': 'North star: paper place-memory at Spatial-app craft.\nDense freeform field, not a sparse folder list.',
    'epic-desk.md': 'Epic: freeform desk as the scope surface for every project.',
    'sprint-01.md': 'Sprint 01: materials, motion, pan/zoom, curator ranking.',
    'misc.md': 'Long-tail notes land collapsed until promoted.'
  }
  const files = [
    'docs/PRD.md',
    'docs/FRD.md',
    'docs/ROADMAP.md',
    'docs/decisions/ADR-001-spatial-desk.md',
    'docs/decisions/ADR-002-kanban-split.md',
    'docs/specs/interaction.md',
    'docs/specs/materials.md',
    'docs/timeline.md',
    'docs/vision.md',
    'docs/epics/epic-desk.md',
    'docs/sprints/sprint-01.md',
    'AGENTS.md',
    'README.md',
    'docs/notes/misc.md',
    'docs/specs/architecture.md',
    'docs/decisions/ADR-003-motion.md'
  ]
  return layoutDesk(
    files.map(rel => {
      const name = rel.split('/').pop()
      return { path: rel, name, rel, body: bodies[name] || '' }
    }),
    ['(seed)']
  )
}

const SKIP = new Set([
  '.git',
  'node_modules',
  '.venv',
  'venv',
  'dist',
  'build',
  '.next',
  'coverage',
  '__pycache__',
  '.tox',
  'target',
  '.cache',
  'vendor',
  '.turbo'
])

function shouldSkipDir(name) {
  return SKIP.has(name) || String(name || '').startsWith('.')
}
function isDocFile(name) {
  return /[.](md|mdx|txt)$/i.test(String(name || ''))
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
  const r = String(root || '')
    .split('\\')
    .join('/')
    .replace(/[/]+$/, '')
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
    for (const e of entries) {
      const full = e.path || join(cur.path, e.name)
      const isDir = Boolean(e.isDirectory || e.type === 'directory' || e.type === 'dir')
      if (isDir) {
        if (cur.depth < maxDepth && !shouldSkipDir(e.name)) queue.push({ path: full, depth: cur.depth + 1 })
      } else if (isDocFile(e.name)) {
        out.push({ path: full, name: e.name, rel: relTo(root, full) })
      }
    }
  }
  return [...new Map(out.map(d => [d.path, d])).values()]
}

async function readPreview(path) {
  const b = desktop()
  if (!b || typeof b.readFileText !== 'function') return ''
  try {
    const txt = await b.readFileText(path)
    if (!txt) return ''
    return String(txt)
      .split(/\r?\n/)
      .filter(l => l.trim())
      .slice(0, 6)
      .join('\n')
      .slice(0, 420)
  } catch {
    return ''
  }
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
    return paths
  } catch {
    return []
  }
}

async function scanProjectDocs(roots) {
  const all = []
  for (const root of roots) all.push(...(await walkDocs(root)))
  const uniq = [...new Map(all.map(d => [d.path, d])).values()]
  const ranked = uniq
    .map(d => ({ d, p: classifyDoc(d.rel || d.name).priority }))
    .sort((a, b) => b.p - a.p)
    .slice(0, 16)
  for (const { d } of ranked) {
    const body = await readPreview(d.path)
    if (body) d.body = body
  }
  return uniq
}

function PaperFace({ card, selected, onSelect }) {
  const stop = e => e.stopPropagation()
  if (card.kind === 'sticky') {
    return _js('button', {
      type: 'button',
      className: 'spatial-sticky',
      style: { '--accent': card.accent },
      onClick: () => onSelect(card),
      onPointerDown: stop,
      children: [
        _j('div', { className: 'spatial-sticky__title', children: card.title }),
        _j('div', { className: 'spatial-sticky__hint', children: card.type })
      ]
    })
  }
  if (card.kind === 'media') {
    return _js('button', {
      type: 'button',
      className: 'spatial-media',
      onClick: () => onSelect(card),
      onPointerDown: stop,
      children: [
        _j('div', {
          className: 'spatial-media__art',
          style: { '--accent': card.accent || MEDIA_A[0], '--accent2': card.accent2 || MEDIA_B[0] }
        }),
        _j('div', { className: 'spatial-media__label', children: card.title })
      ]
    })
  }
  return _js('button', {
    type: 'button',
    className: cn('spatial-paper', selected && 'is-selected'),
    style: { '--accent': card.accent },
    onClick: () => onSelect(card),
    onPointerDown: stop,
    children: [
      _j('div', { className: 'spatial-paper__title', children: card.title }),
      card.summary && _j('div', { className: 'spatial-paper__body', children: card.summary }),
      _js('div', {
        className: 'spatial-paper__meta',
        children: [
          _j('span', { className: 'spatial-chip', children: card.type }),
          _j('span', {
            className: 'spatial-chip',
            style: { color: card.accent, borderColor: (card.accent || '') + '55' },
            children: 'P' + card.priority
          })
        ]
      })
    ]
  })
}

function SpatialDeskPage() {
  ensureCss()
  const cwd = useValue(host.state.cwd)
  const zp = useLocalZoomPan()
  const [query, setQuery] = useState('')
  const [theme, setTheme] = useState('light')
  const [selected, setSelected] = useState(null)
  const [openPiles, setOpenPiles] = useState({})
  const [desk, setDesk] = useState(() => seedDesk())
  const [status, setStatus] = useState('scanning')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setStatus('scanning')
      try {
        const roots = [...(await projectPaths()), cwd || ''].map(p => String(p || '').trim()).filter(Boolean)
        const uniq = []
        for (const r of roots) {
          if (!uniq.some(u => u === r || r.startsWith(u + '/'))) uniq.push(r)
        }
        const docs = uniq.length ? await scanProjectDocs(uniq.slice(0, 4)) : []
        if (cancelled) return
        if (!docs.length) {
          setDesk(seedDesk())
          setStatus('seed')
          return
        }
        setDesk(layoutDesk(docs, uniq))
        setStatus('ready')
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
  const total = desk.items.length + desk.piles.reduce((n, p) => n + (p.cards?.length || 0), 0)
  const visible = shown.items.length

  return _js('div', {
    className: 'spatial-desk',
    'data-theme': theme === 'dark' ? 'dark' : 'light',
    'data-testid': 'spatial-desk-root',
    children: [
      status === 'scanning' && _j('div', { className: 'spatial-status', children: 'Scanning project papers…' }),
      _j('div', {
        className: cn('spatial-desk__stage', zp.panning && 'is-panning'),
        'data-testid': 'spatial-stage',
        ...zp.stageProps,
        children: _js('div', {
          className: 'spatial-desk__world',
          style: {
            width: desk.width,
            height: desk.height,
            marginLeft: -desk.width / 2,
            marginTop: -desk.height / 2,
            ...zp.worldStyle
          },
          children: [
            ...shown.items.map(card =>
              _j('div', {
                key: card.id,
                className: cn('spatial-item', selected && selected.id === card.id && 'is-selected'),
                style: {
                  left: card.x,
                  top: card.y,
                  width: card.width,
                  height: card.height,
                  zIndex: 5 + Math.round(card.priority / 10),
                  '--rot': card.rotation + 'deg',
                  animationDelay: card.delay + 's'
                },
                children: _j(PaperFace, { card, selected: !!(selected && selected.id === card.id), onSelect: setSelected })
              })
            ),
            ...shown.piles.map(pile => {
              const open = openPiles[pile.id]
              return _js('div', {
                key: pile.id,
                className: 'spatial-pile',
                style: {
                  left: pile.x,
                  top: pile.y,
                  width: 280,
                  transform: 'rotate(' + pile.rotation + 'deg)'
                },
                children: [
                  !open &&
                    [0, 1, 2].map(i =>
                      _j('div', {
                        key: 'pk' + i,
                        className: 'spatial-pile__peek',
                        style: {
                          width: 250,
                          height: 72,
                          zIndex: 1 - i,
                          transform:
                            'translate(' + (10 + i * 8) + 'px,' + (-12 - i * 9) + 'px) rotate(' + (-6 + i * 4) + 'deg)',
                          opacity: 0.62 - i * 0.14
                        }
                      })
                    ),
                  _j('div', { className: 'spatial-pile__tab', style: { background: pile.color } }),
                  _js('div', {
                    className: 'spatial-pile__body',
                    style: { width: 250 },
                    children: [
                      _js('div', {
                        className: 'spatial-pile__label',
                        children: [
                          _j('span', {
                            'aria-hidden': true,
                            style: { width: 9, height: 9, borderRadius: 3, background: pile.color }
                          }),
                          _j('span', { children: pile.name }),
                          _j('span', { className: 'spatial-pile__count', children: pile.count })
                        ]
                      }),
                      _j('button', {
                        type: 'button',
                        className: 'spatial-pile__toggle',
                        'aria-expanded': !!open,
                        onPointerDown: e => e.stopPropagation(),
                        onClick: () => setOpenPiles(c => ({ ...c, [pile.id]: !open })),
                        children: open ? '▾' : '▸'
                      })
                    ]
                  }),
                  open &&
                    (pile.cards || []).map((card, ci) =>
                      _j('div', {
                        key: card.id,
                        className: 'spatial-item',
                        style: {
                          left: card.x,
                          top: card.y,
                          width: card.width,
                          height: card.height,
                          zIndex: 8 + ci,
                          '--rot': card.rotation + 'deg',
                          transform: 'rotate(' + card.rotation + 'deg)'
                        },
                        children: _j(PaperFace, {
                          card,
                          selected: !!(selected && selected.id === card.id),
                          onSelect: setSelected
                        })
                      })
                    )
                ]
              })
            })
          ]
        })
      }),
      _js('div', {
        className: 'spatial-toolbar',
        onPointerDown: e => e.stopPropagation(),
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
              onClick: zp.zoomOut,
              children: _j(icons.ZoomOut, { size: 15 })
            })
          }),
          _j('span', { className: 'spatial-toolbar__pct', children: Math.round(zp.scale * 100) + '%' }),
          _j(Tip, {
            label: 'Zoom in',
            children: _j('button', {
              type: 'button',
              onClick: zp.zoomIn,
              children: _j(icons.ZoomIn, { size: 15 })
            })
          }),
          _j(Tip, {
            label: 'Reset view',
            children: _j('button', {
              type: 'button',
              onClick: zp.reset,
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
            className: 'spatial-toolbar__pct',
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
                    _j(DialogDescription, {
                      children: selected.summary || selected.sourcePath || ''
                    })
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
