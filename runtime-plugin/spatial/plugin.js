/** Spatial — power-user command center (Hermes projects + Paperclip pulse). Plain ESM. */
import {
  Badge, cn, Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
  host, icons, KEYBINDS_AREA, PALETTE_AREA, ROUTES_AREA, SIDEBAR_NAV_AREA
} from '@hermes/plugin-sdk'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { jsx as _j, jsxs as _js } from 'react/jsx-runtime'

const ID = 'spatial'
const PC = 'http://127.0.0.1:3100'
const PREF = 'spatial.cmd.v1'
const clamp = (n, a, b) => Math.min(b, Math.max(a, n))
const LS = {
  get() { try { return JSON.parse(localStorage.getItem(PREF) || '{}') } catch { return {} } },
  set(v) { try { localStorage.setItem(PREF, JSON.stringify(v)) } catch {} }
}

function togglePin(projectId, path) {
  const pref = LS.get()
  const pins = { ...(pref.pins || {}) }
  const list = Array.isArray(pins[projectId]) ? pins[projectId].slice() : []
  const i = list.indexOf(path)
  if (i >= 0) list.splice(i, 1)
  else if (path) list.push(path)
  pins[projectId] = list
  pref.pins = pins
  LS.set(pref)
  return pref
}


const CSS = [
'.sp{--bg:#e9e9eb;--paper:#f2f2f4;--card:#fff;--ink:#1c1c1e;--mut:#6c6c70;--line:rgba(0,0,0,.08);--acc:#0a84ff;--sh:0 .5px .5px rgba(0,0,0,.04),0 2px 6px rgba(0,0,0,.045),0 12px 28px rgba(0,0,0,.08),0 32px 64px rgba(0,0,0,.07);--shh:0 1px 2px rgba(0,0,0,.05),0 14px 32px rgba(0,0,0,.12),0 40px 80px rgba(0,0,0,.14);--spr:cubic-bezier(.34,1.45,.64,1);--ease:cubic-bezier(.22,1,.36,1);position:absolute;inset:0;display:flex;flex-direction:column;overflow:hidden;color:var(--ink);background:var(--bg);font:12.5px/1.35 ui-sans-serif,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased;min-height:100%;height:100%;width:100%}',
'.sp[data-t=d]{--bg:#1c1c1e;--paper:#2c2c2e;--card:#2c2c2e;--ink:#f5f5f7;--mut:#a1a1a6;--line:rgba(255,255,255,.1);--sh:0 1px 2px rgba(0,0,0,.4),0 16px 36px rgba(0,0,0,.5);--shh:0 4px 16px rgba(0,0,0,.55),0 28px 64px rgba(0,0,0,.55)}',
'.sp-st{position:relative;flex:1 1 auto;min-height:0;height:100%;overflow:hidden;cursor:grab;touch-action:none;background:radial-gradient(85% 65% at 50% 40%,#f3f3f5 0%,transparent 58%),radial-gradient(120% 100% at 50% 100%,rgba(0,0,0,.04),transparent 42%),radial-gradient(40% 34% at 14% 76%,rgba(10,132,255,.04),transparent 55%),radial-gradient(36% 30% at 86% 16%,rgba(191,90,242,.035),transparent 50%),var(--bg)}',
'.sp-st.p{cursor:grabbing;user-select:none}.sp-st.p .sp-i{transition:none!important;animation:none!important}',
'.sp-w{position:absolute;left:0;top:0;transform-origin:0 0;will-change:transform}',
'.sp-i{position:absolute;transform-origin:center;transform:rotate(var(--r,0deg));animation:sp-in .45s var(--spr) both;animation-fill-mode:both;transition:transform .32s var(--spr),filter .2s var(--ease);contain:layout paint}',
'.sp-i:hover{z-index:40!important;filter:drop-shadow(0 22px 40px rgba(0,0,0,.18));transform:translateY(-14px) scale(1.05) rotate(var(--r,0deg))!important}',
'.sp-i.on{z-index:50!important}@keyframes sp-in{from{opacity:.01;transform:translateY(14px) scale(.94) rotate(var(--r,0deg))}to{opacity:1;transform:translateY(0) scale(1) rotate(var(--r,0deg))}}',
'.sp-p,.sp-c,.sp-n,.sp-x{width:100%;height:100%;border:0;border-radius:20px;text-align:left;cursor:pointer;color:inherit;position:relative;overflow:hidden}',
'.sp-p,.sp-c{background:var(--card);border:1px solid rgba(0,0,0,.06);box-shadow:var(--sh);padding:0;display:flex;flex-direction:column}.sp-p{box-shadow:var(--sh),0 1px 0 rgba(0,0,0,.03),inset 0 1px 0 rgba(255,255,255,.92),inset 0 0 0 1px rgba(255,255,255,.3)}',
'.sp-p::before,.sp-c::before{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;background:linear-gradient(180deg,rgba(255,255,255,.78),transparent 32%),radial-gradient(120% 80% at 50% 0%,rgba(255,255,255,.35),transparent 50%);z-index:1}',
'.sp[data-t=d] .sp-p::before,.sp[data-t=d] .sp-c::before{background:linear-gradient(180deg,rgba(255,255,255,.06),transparent 30%)}',
'.sp-i:hover .sp-p,.sp-i:hover .sp-c,.sp-i:hover .sp-n,.sp-i:hover .sp-x{box-shadow:var(--shh)}',
'.sp-p__h{height:44%;min-height:68px;background:linear-gradient(160deg,color-mix(in srgb,var(--a,#0a84ff) 32%,#fff) 0%,color-mix(in srgb,var(--a,#0a84ff) 10%,#f3f3f5) 48%,#eaeaee 100%),repeating-linear-gradient(-14deg,transparent,transparent 9px,rgba(0,0,0,.018) 9px,rgba(0,0,0,.018) 10px);border-bottom:1px solid var(--line)}',
'.sp-p__b{position:relative;z-index:2;padding:12px 14px;display:flex;flex-direction:column;gap:6px;flex:1;min-height:0}','.sp-p__rules{display:flex;flex-direction:column;gap:7px;margin-top:4px}','.sp-p__rule{height:5px;border-radius:3px;background:color-mix(in srgb,var(--mut) 16%,transparent)}','.sp-p__rule:nth-child(2){width:92%}','.sp-p__rule:nth-child(3){width:78%}','.sp-p__rule:nth-child(4){width:84%}',
'.sp-k{font:700 9px/1 ui-sans-serif,system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase;color:var(--a,var(--acc))}',
'.sp-t{font-size:13.5px;font-weight:650;letter-spacing:-.02em;line-height:1.2}',
'.sp-s{font-size:11px;color:var(--mut);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}',
'.sp-m{display:flex;flex-wrap:wrap;gap:4px;margin-top:auto;padding-top:4px}',
'.sp-ch{padding:2px 7px;border-radius:999px;border:1px solid var(--line);font:500 8px/1.2 ui-monospace,Menlo,monospace;color:var(--mut);text-transform:uppercase;letter-spacing:.03em}',
'.sp-n{padding:14px;display:flex;flex-direction:column;justify-content:space-between;color:#1c1c1e;background:linear-gradient(155deg,color-mix(in srgb,var(--a,#ffd60a) 94%,#fff),color-mix(in srgb,var(--a,#ffd60a) 72%,#efe6c0));box-shadow:0 1px 1px rgba(0,0,0,.06),0 10px 22px color-mix(in srgb,var(--a,#ffd60a) 32%,transparent),0 24px 48px rgba(0,0,0,.08),inset 0 1px 0 rgba(255,255,255,.55);border-radius:14px;transform:rotate(var(--r,0deg))}',
'.sp[data-t=d] .sp-n{color:#f5f5f7;background:color-mix(in srgb,var(--a,#ffd60a) 40%,#2c2c2e)}',
'.sp-x{background:#0e0e10;box-shadow:var(--sh)}',
'.sp-x__a{position:absolute;inset:0;background:radial-gradient(90% 80% at 22% 18%,color-mix(in srgb,var(--a,#0a84ff) 75%,transparent),transparent 52%),radial-gradient(80% 70% at 82% 78%,color-mix(in srgb,var(--b,#bf5af2) 55%,transparent),transparent 48%),radial-gradient(circle at 70% 30%,rgba(255,255,255,.12),transparent 28%),linear-gradient(150deg,#1c1c22,#0a0a0c 60%,#121218)}','.sp-x__a[data-pat=grid]{background:linear-gradient(rgba(255,255,255,.06) 1px,transparent 1px) 0 0/26px 26px,linear-gradient(90deg,rgba(255,255,255,.06) 1px,transparent 1px) 0 0/26px 26px,radial-gradient(60% 50% at 70% 30%,color-mix(in srgb,var(--a) 55%,transparent),transparent 60%),#111114}','.sp-x__a[data-pat=soft]{background:radial-gradient(70% 60% at 40% 40%,color-mix(in srgb,var(--a) 42%,#fff),transparent 60%),linear-gradient(180deg,#f4f4f6,#d8d8de)}','.sp-x__a[data-pat=split]{background:linear-gradient(105deg,color-mix(in srgb,var(--a) 82%,#111) 0 42%,#0e0e12 42% 100%)}',
'.sp-x__c{position:absolute;left:0;right:0;bottom:0;z-index:1;padding:24px 12px 12px;background:linear-gradient(180deg,transparent,rgba(0,0,0,.72));color:#f5f5f7;font-weight:650;font-size:12px}',
'.sp-tb{position:absolute;bottom:22px;left:50%;z-index:60;transform:translateX(-50%);display:flex;gap:2px;align-items:center;padding:6px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.12);background:rgba(18,18,20,.82);color:#f5f5f7;box-shadow:0 12px 40px rgba(0,0,0,.36),inset 0 1px 0 rgba(255,255,255,.1);backdrop-filter:blur(22px) saturate(160%);-webkit-backdrop-filter:blur(22px) saturate(160%)}',
'.sp-tb input{width:min(200px,34vw);padding:7px 12px;border:0;border-radius:999px;background:rgba(255,255,255,.1);color:#f5f5f7;font:inherit;font-size:12px;outline:0}',
'.sp-tb input::placeholder{color:rgba(245,245,247,.4)}',
'.sp-tb button{width:32px;height:32px;border:0;border-radius:999px;background:transparent;color:rgba(245,245,247,.72);cursor:pointer;display:grid;place-items:center;transition:transform .18s var(--spr),background .15s}',
'.sp-tb button:hover{background:rgba(255,255,255,.12);color:#fff;transform:scale(1.08)}',
'.sp-tb .pct{min-width:2.6rem;text-align:center;font:500 10px ui-monospace,Menlo,monospace;opacity:.55}',
'.sp-top{position:absolute;top:12px;left:50%;z-index:50;transform:translateX(-50%);display:flex;gap:8px;align-items:center;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:color-mix(in srgb,var(--card) 86%,transparent);box-shadow:var(--sh);backdrop-filter:blur(12px);pointer-events:none;font-size:11px;color:var(--mut)}',
'.sp-top b{color:var(--ink);font-weight:650}',
'.sp-cr{position:absolute;z-index:55;display:flex;gap:8px}.sp-cr.l{left:18px;bottom:22px}.sp-cr.r{right:18px;bottom:22px}',
'.sp-cr button{width:38px;height:38px;border-radius:999px;border:1px solid rgba(255,255,255,.1);background:rgba(22,22,24,.72);color:rgba(245,245,247,.75);box-shadow:0 10px 28px rgba(0,0,0,.28);backdrop-filter:blur(14px);cursor:pointer;display:grid;place-items:center;transition:transform .18s var(--spr)}',
'.sp-cr button:hover{transform:scale(1.07);color:#fff}',
'@media (prefers-reduced-motion:reduce){.sp-i{animation:none!important;transition:none!important}.sp-i:hover{transform:rotate(var(--r,0deg))!important;filter:none!important}}'
].join('\n')

function css() {
  if (typeof document === 'undefined') return
  let el = document.getElementById('sp-css')
  if (!el) {
    el = document.createElement('style')
    el.id = 'sp-css'
    document.head.appendChild(el)
  }
  if (el.textContent !== CSS) el.textContent = CSS
}

function usePanZoom() {
  const [t, setT] = useState({ s: 0.86, x: 8, y: 8 })
  const drag = useRef(null)
  const [pan, setPan] = useState(0)
  const zoomAt = useCallback((f, cx = 0, cy = 0) => {
    setT(p => {
      const s = clamp(p.s * f, 0.3, 2.8)
      const k = s / p.s
      return { s, x: cx - k * (cx - p.x), y: cy - k * (cy - p.y) }
    })
  }, [])
  const onWheel = useCallback(e => {
    e.preventDefault(); e.stopPropagation()
    const r = e.currentTarget.getBoundingClientRect()
    zoomAt(e.deltaY < 0 ? 1.08 : 1 / 1.08, e.clientX - r.left - r.width / 2, e.clientY - r.top - r.height / 2)
  }, [zoomAt])
  const onDown = useCallback(e => {
    if (e.button !== 0) return
    e.currentTarget.setPointerCapture(e.pointerId)
    setT(p => { drag.current = { x: e.clientX - p.x, y: e.clientY - p.y }; return p })
    setPan(1)
  }, [])
  const onMove = useCallback(e => {
    if (!drag.current) return
    const d = drag.current
    setT(p => ({ ...p, x: e.clientX - d.x, y: e.clientY - d.y }))
  }, [])
  const end = useCallback(() => { drag.current = null; setPan(0) }, [])
  return {
    pan, s: t.s,
    reset: () => setT({ s: 0.86, x: 8, y: 8 }),
    zin: () => zoomAt(1.18), zout: () => zoomAt(1 / 1.18),
    stage: { onWheel, onPointerDown: onDown, onPointerMove: onMove, onPointerUp: end, onPointerCancel: end, onPointerLeave: end },
    world: { transform: 'translate(' + t.x + 'px,' + t.y + 'px) scale(' + t.s + ')' }
  }
}

const hn = (s, m) => { let h = 0; const t = String(s || ''); for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) | 0; return Math.abs(h) % m }
const rot = id => (hn(id, 90) - 45) / 9
const ST = ['#ffd60a', '#30d158', '#64d2ff', '#ff9f0a', '#bf5af2', '#ff375f']
const AC = ['#0a84ff', '#30d158', '#bf5af2', '#ff9f0a', '#64d2ff', '#ff375f']
const PATS = ['grad', 'grid', 'soft', 'split', 'grad']

function slots(n) {
  // Banded freeform: readable ops hierarchy with organic jitter (not a dump, not a rigid grid).
  const bands = [
    { y: 24, x0: 16, cols: 6, dx: 250, dy: 0, n: 6 },   // projects
    { y: 230, x0: 40, cols: 5, dx: 220, dy: 0, n: 8 },  // hot stickies
    { y: 430, x0: 80, cols: 5, dx: 240, dy: 0, n: 6 },  // doctrine / secondary
    { y: 640, x0: 48, cols: 6, dx: 255, dy: 0, n: 8 }   // media arc
  ]
  const out = []
  let i = 0
  for (const b of bands) {
    for (let c = 0; c < b.n && i < n; c++, i++) {
      const jx = hn('x' + i, 56) - 28 + (c % 2) * 22
      const jy = hn('y' + i, 48) - 24 + (c % 3) * 12
      out.push({ x: b.x0 + c * b.dx + jx, y: b.y + jy })
    }
  }
  while (out.length < n) {
    const k = out.length
    out.push({ x: 40 + (k % 6) * 240, y: 40 + ((k / 6) | 0) * 180 })
  }
  return out
}

async function pc(path) {
  try {
    const r = await fetch(PC + path, { headers: { Accept: 'application/json' } })
    if (!r.ok) return null
    return await r.json()
  } catch { return null }
}

async function hermesProjects() {
  try {
    const p = await host.request('projects.list')
    return (p && p.projects) || []
  } catch { return [] }
}



function layoutBands(items) {
  const projects = items.filter(it => it.k === 'paper' && it.meta && it.meta.hermes)
  const stickies = items.filter(it => it.k === 'sticky')
  const media = items.filter(it => it.k === 'media')
  const other = items.filter(it => !projects.includes(it) && !stickies.includes(it) && !media.includes(it))
  const place = (arr, y0, x0, dx, fan) => {
    arr.forEach((it, i) => {
      const jx = hn('bx' + it.id, 64) - 32 + (i % 2) * 28 - (i % 3) * 10
      const jy = hn('by' + it.id, 72) - 36 + Math.sin(i * 1.7) * fan
      it.x = x0 + i * dx + jx
      it.y = y0 + jy
      it.r = (hn(it.id, 100) - 50) / 8 // stronger freeform tilt
      it.priority = it.priority || (40 - i)
    })
  }
  // strata with intentional slight Y interleave at edges (freeform without losing scan bands)
  place(projects, 36, 24, 248, 22)
  place(stickies.slice(0, 7), 236, 56, 198, 28)
  place(other, 400, 120, 210, 24)
  place(media, 600, 36, 235, 26)
  place(stickies.slice(7), 560, 980, 180, 20)
  // gentle peek-stack: nudge every 3rd card to overlap previous slightly
  const all = projects.concat(stickies, other, media)
  all.forEach((it, i) => {
    if (i % 3 === 2 && i > 0) {
      it.x = (it.x * 0.7 + all[i - 1].x * 0.3)
      it.y = (it.y * 0.75 + all[i - 1].y * 0.25) + 12
      it.priority = (it.priority || 20) + 8
    }
  })
  return all
}


function stop(e) { e.stopPropagation() }

function Card({ it, on }) {
  if (it.k === 'sticky') {
    return _js('button', { type: 'button', className: 'sp-n', style: { '--a': it.a }, onClick: () => on(it), onPointerDown: stop, children: [
      _j('div', { className: 'sp-t', children: it.t }),
      it.s && _j('div', { className: 'sp-s', children: it.s }),
      _j('div', { className: 'sp-k', style: { opacity: 0.55 }, children: it.tag || 'pulse' })
    ]})
  }
  if (it.k === 'media') {
    return _js('button', { type: 'button', className: 'sp-x', onClick: () => on(it), onPointerDown: stop, children: [
      _j('div', { className: 'sp-x__a', 'data-pat': it.pat || 'grad', style: { '--a': it.a || AC[0], '--b': it.b || AC[2] } }),
      _j('div', { className: 'sp-x__c', children: it.t })
    ]})
  }
  const hasBody = !!(it.s && String(it.s).trim())
  return _js('button', { type: 'button', className: 'sp-p', style: { '--a': it.a }, onClick: () => on(it), onPointerDown: stop, children: [
    _j('div', { className: 'sp-p__h', 'data-tone': it.tone || 'a' }),
    _js('div', { className: 'sp-p__b', children: [
      _j('div', { className: 'sp-k', children: it.tag || 'project' }),
      _j('div', { className: 'sp-t', children: it.t }),
      hasBody
        ? _j('div', { className: 'sp-s', children: it.s })
        : _js('div', { className: 'sp-p__rules', children: [0,1,2,3].map(i => _j('div', { key: i, className: 'sp-p__rule' })) }),
      _js('div', { className: 'sp-m', children: (it.chips || []).slice(0, 4).map((c, i) =>
        _j('span', { key: i, className: 'sp-ch', children: c })
      ) })
    ]})
  ]})
}

function buildHome(hp, companies, pcProjects, issues, prefs) {
  const items = []
  const sl = slots(Math.max(hp.length + 36, 48))
  const byPath = new Map()
  for (const p of pcProjects || []) {
    const cwd = p.codebase && (p.codebase.effectiveLocalFolder || p.codebase.localFolder)
    if (cwd) byPath.set(String(cwd).replace(/[/]+$/, ''), p)
    byPath.set(String(p.name || '').toLowerCase(), p)
  }
  hp.forEach((p, i) => {
    const path = p.primary_path || (p.folders && p.folders[0] && p.folders[0].path) || ''
    const key = String(path).replace(/[/]+$/, '')
    const pcP = byPath.get(key) || byPath.get(String(p.name || '').toLowerCase())
    const iss = (issues || []).filter(x => pcP && x.projectId === pcP.id)
    const open = iss.filter(x => !/done|cancelled|canceled/i.test(x.status || '')).length
    const hot = iss.filter(x => /in_progress|in_review|blocked/i.test(x.status || '')).slice(0, 2)
    const pin = (prefs.pins && prefs.pins[p.id]) || []
    items.push({
      id: p.id, k: 'paper', t: p.name || p.slug || 'project',
      s: p.description || path || 'Hermes project',
      tag: pcP ? 'hermes · paperclip' : 'hermes',
      a: AC[i % AC.length],
      chips: [
        pcP ? (pcP.status || 'pc') : 'local',
        open ? open + ' open' : (pcP ? '0 open' : 'no pc'),
        pin.length ? pin.length + ' pin' : null,
        hot[0] ? (hot[0].identifier || hot[0].status) : null
      ].filter(Boolean),
      x: sl[i].x, y: sl[i].y, r: rot(p.id), w: 178 + hn(p.id, 36), h: 164 + hn(p.id + 'h', 40),
      d: Math.min(i * 0.03, 0.45),
      href: pcP ? PC + '/' : null,
      meta: { hermes: p, pc: pcP, issues: iss, pins: pin }
    })
  })
  // company pulse stickies
  const pulse = (issues || []).filter(x => !/done|cancelled|canceled/i.test(x.status || '')).slice(0, 8)
  pulse.forEach((iss, j) => {
    const i = hp.length + j
    const sl0 = sl[i] || { x: 900 + j * 40, y: 600 }
    items.push({
      id: 'iss-' + iss.id, k: 'sticky', t: iss.identifier || 'issue',
      s: iss.title || '', tag: iss.status, a: ST[j % ST.length],
      x: sl0.x, y: sl0.y, r: rot(iss.id), w: 158 + hn(iss.id, 16), h: 148 + hn(iss.id + 'h', 18),
      d: Math.min(i * 0.03, 0.5),
      href: PC + '/issues/' + (iss.id || ''), meta: { issue: iss }
    })
  })
  // media tiles for company goals
  const co = (companies || [])[0]
  if (co) {
    const i = items.length
    const sl0 = sl[i] || { x: 1000, y: 200 }
    items.push({
      id: 'co-' + co.id, k: 'media', t: co.name + ' · live OS', a: '#0a84ff', b: '#bf5af2',
      x: sl0.x, y: sl0.y, r: rot(co.id), w: 200, h: 240, d: 0.2, href: PC + '/',
      meta: { company: co }
    })
  }
  // density fillers (doctrine stickies) so field is not sparse
  const fill = [
    { t: 'Kanban = execution', s: 'Spatial = scope + ops pulse', a: '#ffd60a' },
    { t: 'Paperclip owns runs', s: 'Read-only. Deep work in PC UI.', a: '#30d158' },
    { t: 'Pins stay local', s: 'localStorage only — no second DB.', a: '#64d2ff' },
    { t: '24/7 command', s: 'Projects + hot issues on one desk.', a: '#ff9f0a' }
  ]
  fill.forEach((f, j) => {
    const i = items.length + j
    const sl0 = sl[i % sl.length] || { x: 700 + j * 30, y: 700 }
    items.push({
      id: 'fill-' + j, k: 'sticky', t: f.t, s: f.s, tag: 'doctrine', a: f.a,
      x: sl0.x + 28, y: sl0.y + 18, r: rot('f' + j), w: 156 + hn('fw'+j, 18), h: 146 + hn('fh'+j, 16), d: 0.32
    })
  })
  // abstract media tiles pad empty field (reference place-memory)
  for (let m = 0; m < 5; m++) {
    const i = items.length
    const sl0 = sl[i % sl.length] || { x: 900 + m * 40, y: 200 + m * 50 }
    items.push({
      id: 'med-' + m, k: 'media', t: ['Mood', 'Clip', 'Depth', 'Light', 'Chrome'][m],
      a: AC[m % AC.length], b: AC[(m + 2) % AC.length], pat: PATS[m % PATS.length],
      x: sl0.x, y: sl0.y, r: rot('m' + m), w: 176 + hn('mw'+m, 36), h: 210 + hn('mh'+m, 44), d: 0.4
    })
  }
  return { w: 1750, h: 1100, items: layoutBands(items) }
}

function buildProject(meta, prefs) {
  const items = []
  const iss = (meta.issues || []).slice().sort((a, b) => {
    const rank = s => (/in_progress/.test(s) ? 3 : /blocked|in_review/.test(s) ? 2 : /todo|backlog/.test(s) ? 1 : 0)
    return rank(b.status || '') - rank(a.status || '')
  })
  const sl = slots(Math.max(iss.length + 12, 24))
  iss.slice(0, 18).forEach((x, i) => {
    const hot = /in_progress|blocked|in_review/i.test(x.status || '')
    items.push({
      id: x.id, k: hot ? 'sticky' : 'paper', t: x.identifier || x.title,
      s: x.title, tag: x.status, a: hot ? ST[i % ST.length] : AC[i % AC.length],
      chips: [x.priority, x.status].filter(Boolean),
      x: sl[i].x, y: sl[i].y, r: rot(x.id), w: hot ? 160 : 210, h: hot ? 150 : 190,
      d: Math.min(i * 0.028, 0.45), href: PC + '/issues/' + (x.id || ''), meta: { issue: x }
    })
  })
  const pins = meta.pins || []
  pins.forEach((p, j) => {
    const i = iss.length + j
    const sl0 = sl[i] || { x: 100 + j * 40, y: 700 }
    items.push({
      id: 'pin-' + p, k: 'paper', t: String(p).split('/').pop(), s: p, tag: 'pinned',
      a: '#64d2ff', chips: ['pin'], x: sl0.x, y: sl0.y, r: rot(p), w: 200, h: 170,
      d: 0.3, meta: { path: p }
    })
  })
  if (!items.length) {
    items.push({ id: 'empty', k: 'paper', t: 'No open pulse', s: 'Paperclip issues will land here. Open full board for deep work.', tag: 'hint', a: '#8e8e93', chips: ['paperclip'], x: 400, y: 300, r: -1, w: 240, h: 180, d: 0, href: PC + '/' })
  }
  return { w: 1400, h: 960, items }
}

function SpatialPage() {
  css()
  const zp = usePanZoom()
  const [q, setQ] = useState('')
  const [theme, setTheme] = useState('light')
  const [sel, setSel] = useState(null)
  const [view, setView] = useState({ mode: 'home' }) // home | project
  const [desk, setDesk] = useState({ w: 1500, h: 1000, items: [] })
  const [st, setSt] = useState('…')
  const [tick, setTick] = useState(0)
  const prefs = useRef(LS.get())

  useEffect(() => {
    let dead = 0
    ;(async () => {
      setSt('sync')
      const [hp, cos] = await Promise.all([hermesProjects(), pc('/api/companies')])
      const companies = Array.isArray(cos) ? cos : []
      const co = companies[0]
      let pcProjects = [], issues = []
      if (co) {
        const [pp, iss] = await Promise.all([
          pc('/api/companies/' + co.id + '/projects'),
          pc('/api/companies/' + co.id + '/issues?limit=80')
        ])
        pcProjects = Array.isArray(pp) ? pp : []
        issues = Array.isArray(iss) ? iss : []
      }
      if (dead) return
      if (view.mode === 'project' && view.meta) {
        // refresh issues for open project; fall back to company open issues if no PC link
        const pid = view.meta.pc && view.meta.pc.id
        let mine = pid ? issues.filter(x => x.projectId === pid) : (view.meta.issues || [])
        if (!mine.length) mine = issues.filter(x => !/done|cancelled|canceled/i.test(x.status || '')).slice(0, 18)
        setDesk(buildProject({ ...view.meta, issues: mine, pins: (prefs.current.pins || {})[view.meta.hermes && view.meta.hermes.id] || view.meta.pins || [] }, prefs.current))
        setSt((mine && mine.length) + ' pulse')
      } else {
        const h = hp.length ? hp : [{ id: 'seed', name: 'Add a Hermes project', description: 'Projects appear from the sidebar workspace list.', primary_path: '' }]
        setDesk(buildHome(h, companies, pcProjects, issues, prefs.current))
        setSt(h.length + ' proj · ' + issues.filter(x => !/done|cancelled|canceled/i.test(x.status || '')).length + ' open')
      }
    })()
    return () => { dead = 1 }
  }, [tick, view.mode, view.key])

  // soft poll for 24/7 ops — 45s, no new backend
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 45000)
    return () => clearInterval(id)
  }, [])

  const shown = useMemo(() => {
    const qq = q.trim().toLowerCase()
    if (!qq) return desk.items
    return desk.items.filter(it => [it.t, it.s, it.tag, ...(it.chips || [])].join(' ').toLowerCase().includes(qq))
  }, [desk, q])

  const open = it => {
    if (view.mode === 'home' && it.meta && it.meta.hermes) {
      setView({ mode: 'project', key: it.id, meta: it.meta })
      zp.reset()
      setSel(null)
      return
    }
    setSel(it)
  }

  const back = () => { setView({ mode: 'home' }); zp.reset(); setSel(null) }
  const openPc = () => { try { window.open(PC + '/', '_blank', 'noopener') } catch {} }

  return _js('div', {
    className: 'sp', 'data-t': theme === 'dark' ? 'd' : 'l', 'data-testid': 'spatial-desk-root',
    children: [
      _js('div', { className: 'sp-top', children: [
        _j('b', { children: view.mode === 'project' ? (view.meta && view.meta.hermes && view.meta.hermes.name) || 'Project' : 'Command' }),
        _j('span', { children: st })
      ]}),
      _j('div', {
        className: cn('sp-st', zp.pan && 'p'), 'data-testid': 'spatial-stage', ...zp.stage,
        children: _js('div', {
          className: 'sp-w',
          style: { width: desk.w, height: desk.h, ...zp.world },
          children: shown.map(it =>
            _j('div', {
              key: it.id,
              className: cn('sp-i', sel && sel.id === it.id && 'on'),
              style: { left: it.x, top: it.y, width: it.w, height: it.h, zIndex: 4 + Math.round((it.priority || 20) / 12), '--r': it.r + 'deg', animationDelay: (it.d || 0) + 's' },
              children: _j(Card, { it, on: open })
            })
          )
        })
      }),
      _js('div', { className: 'sp-tb', onPointerDown: stop, children: [
        _j('input', { 'aria-label': 'Filter', placeholder: view.mode === 'home' ? 'Filter projects…' : 'Filter pulse…', value: q, onChange: e => setQ(e.target.value) }),
        _j('button', { type: 'button', title: 'Zoom out', onClick: zp.zout, children: '−' }),
        _j('span', { className: 'pct', children: Math.round(zp.s * 100) + '%' }),
        _j('button', { type: 'button', title: 'Zoom in', onClick: zp.zin, children: '+' }),
        _j('button', { type: 'button', title: 'Reset', onClick: zp.reset, children: '⌂' }),
        _j('button', { type: 'button', title: 'Theme', onClick: () => setTheme(t => t === 'light' ? 'dark' : 'light'), children: theme === 'light' ? '☾' : '☀' }),
        _j('button', { type: 'button', title: 'Refresh', onClick: () => setTick(t => t + 1), children: '↻' }),
        _j('button', { type: 'button', title: 'Paperclip', onClick: openPc, children: 'P' })
      ]}),
      _js('div', { className: 'sp-cr l', onPointerDown: stop, children: [
        view.mode === 'project'
          ? _j('button', { type: 'button', title: 'Back', onClick: back, children: '←' })
          : _j('button', { type: 'button', title: 'Chat', onClick: () => host.navigate('/'), children: '⌘' })
      ]}),
      _js('div', { className: 'sp-cr r', onPointerDown: stop, children: [
        _j('button', { type: 'button', title: 'Kanban', onClick: () => host.navigate('/kanban'), children: 'K' }),
        _j('button', { type: 'button', title: 'Paperclip board', onClick: openPc, children: '↗' })
      ]}),
      _j(Dialog, {
        open: !!sel, onOpenChange: o => { if (!o) setSel(null) },
        children: _j(DialogContent, {
          className: 'max-w-md border-border/60 bg-background/95 backdrop-blur-xl',
          children: sel ? [
            _js(DialogHeader, { key: 'h', children: [
              _j(DialogTitle, { children: sel.t }),
              _j(DialogDescription, { children: sel.s || '' })
            ]}),
            _js('div', { key: 'b', style: { display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }, children: [
              _j(Badge, { variant: 'muted', children: sel.tag || sel.k }),
              ...(sel.chips || []).map((c, i) => _j(Badge, { key: i, variant: 'outline', children: c })),
              sel.href && _j('button', {
                type: 'button', className: 'sp-ch', style: { cursor: 'pointer', color: 'var(--acc,#0a84ff)' },
                onClick: () => { try { window.open(sel.href, '_blank', 'noopener') } catch {} },
                children: 'Open Paperclip'
              }),
              view.mode === 'project' && view.meta && view.meta.hermes && (sel.meta && (sel.meta.path || (sel.meta.issue && sel.meta.issue.id))) && _j('button', {
                type: 'button', className: 'sp-ch', style: { cursor: 'pointer' },
                onClick: () => {
                  const path = (sel.meta && sel.meta.path) || ('issue:' + sel.meta.issue.id)
                  prefs.current = togglePin(view.meta.hermes.id, path)
                  setTick(t => t + 1)
                },
                children: 'Pin/Unpin'
              })
            ]})
          ] : null
        })
      })
    ]
  })
}

function go() { host.navigate('/spatial') }

export default {
  id: ID, name: 'Spatial', defaultEnabled: true,
  register(ctx) {
    css()
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: '/spatial' }, render: () => _j(SpatialPage, {}) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, order: 54, data: { codicon: 'dashboard', label: 'Spatial', path: '/spatial' } },
      { id: 'open', area: PALETTE_AREA, data: { id: 'spatial.open', label: 'Spatial: Command center', keywords: ['spatial', 'paperclip', 'projects', 'command'], run: go } },
      { id: 'key', area: KEYBINDS_AREA, data: { id: 'spatial.open', category: 'view', defaults: ['mod+alt+s'], label: 'Spatial: Command center', run: go } }
    ])
  }
}
