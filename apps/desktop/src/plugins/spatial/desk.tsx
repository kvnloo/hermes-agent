import { type CSSProperties, useEffect, useMemo, useState } from 'react'

import {
  AnimatePresence,
  Badge,
  cn,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  host,
  icons,
  motion,
  Tip,
  useReducedMotion,
  useValue,
  useZoomPan
} from '@hermes/plugin-sdk'

import { resolveScanRoots, scanProjectDocs } from './discover'
import { type Desk, type DeskCard, type DeskStack, cardCount, filterDesk, layoutDesk, seedDesk } from './model'
import './spatial.css'

const SPRING = { type: 'spring' as const, stiffness: 340, damping: 28, mass: 0.85 }
const SPRING_SOFT = { type: 'spring' as const, stiffness: 240, damping: 26, mass: 1 }

async function projectPaths(): Promise<string[]> {
  try {
    const payload = await host.request<{
      active_id?: null | string
      projects?: Array<{
        folders?: Array<{ path?: string }>
        id?: string
        primary_path?: null | string
      }>
    }>('projects.list')
    const projects = payload?.projects ?? []
    const paths: string[] = []
    for (const p of projects) {
      if (p.primary_path) paths.push(p.primary_path)
      for (const f of p.folders ?? []) if (f.path) paths.push(f.path)
    }
    const activeId = payload?.active_id
    if (!activeId) return paths
    const ap = projects.find(p => p.id === activeId)
    if (!ap) return paths
    const prefer = [ap.primary_path, ...(ap.folders ?? []).map(f => f.path)].filter(Boolean) as string[]
    return [...prefer, ...paths.filter(p => !prefer.includes(p))]
  } catch {
    return []
  }
}

function PaperCard({
  card,
  selected,
  onSelect,
  reduceMotion
}: {
  card: DeskCard
  selected: boolean
  onSelect: (c: DeskCard) => void
  reduceMotion: boolean | null
}) {
  return (
    <motion.button
      animate={{
        opacity: 1,
        scale: selected ? 1.03 : 1,
        y: selected ? -8 : 0,
        rotate: reduceMotion ? 0 : card.rotation
      }}
      className={cn(
        'spatial-card',
        card.kind === 'sticky' && 'spatial-card--sticky',
        selected && 'is-selected'
      )}
      data-testid={`spatial-card-${card.id}`}
      exit={{ opacity: 0, scale: 0.92, y: 12 }}
      initial={reduceMotion ? false : { opacity: 0, scale: 0.92, y: 16 }}
      layout={!reduceMotion}
      onClick={() => onSelect(card)}
      onPointerDown={e => e.stopPropagation()}
      style={
        {
          left: card.x,
          top: card.y,
          width: card.width,
          height: card.height,
          ['--card-accent']: card.accent
        } as CSSProperties
      }
      transition={reduceMotion ? { duration: 0 } : SPRING}
      type="button"
      whileHover={reduceMotion ? undefined : { y: -10, scale: 1.035 }}
      whileTap={reduceMotion ? undefined : { scale: 0.985 }}
    >
      <div className="spatial-card__title">{card.title}</div>
      {card.kind !== 'sticky' && <div className="spatial-card__summary">{card.summary}</div>}
      <div className="spatial-card__meta">
        <span className="spatial-chip">{card.type}</span>
        <span className="spatial-chip" style={{ color: card.accent, borderColor: `${card.accent}55` }}>
          P{card.priority}
        </span>
      </div>
    </motion.button>
  )
}

function FolderPile({
  stack,
  collapsed,
  onToggle,
  selectedId,
  onSelect,
  reduceMotion
}: {
  stack: DeskStack
  collapsed: boolean
  onToggle: () => void
  selectedId: string | null
  onSelect: (c: DeskCard) => void
  reduceMotion: boolean | null
}) {
  const peeks = stack.cards.slice(0, 3)

  return (
    <motion.div
      className="spatial-folder"
      initial={false}
      style={{
        left: stack.x,
        top: stack.y,
        width: Math.max(stack.width, 280),
        rotate: reduceMotion ? 0 : stack.rotation
      }}
      transition={SPRING_SOFT}
    >
      {/* Physical peek sheets under the folder when collapsed */}
      <AnimatePresence>
        {collapsed &&
          peeks.map((card, i) => (
            <motion.div
              animate={{
                opacity: 0.55 - i * 0.12,
                x: 10 + i * 7,
                y: -10 - i * 8,
                rotate: -5 + i * 3.5
              }}
              className="spatial-folder__peek"
              exit={{ opacity: 0, y: 0 }}
              initial={reduceMotion ? false : { opacity: 0, y: 0 }}
              key={`peek-${card.id}`}
              style={{
                width: stack.width,
                height: stack.height + 8,
                zIndex: 1 - i
              }}
              transition={SPRING_SOFT}
            />
          ))}
      </AnimatePresence>

      <div className="spatial-folder__tab" style={{ background: stack.folderColor }} />

      <div className="spatial-folder__body" style={{ width: stack.width, minHeight: stack.height }}>
        <div className="spatial-folder__label">
          <span aria-hidden style={{ width: 9, height: 9, borderRadius: 3, background: stack.folderColor }} />
          <span>{stack.name}</span>
          <span className="spatial-folder__count">{stack.cards.length}</span>
        </div>
        <button
          aria-expanded={!collapsed}
          aria-label={`${collapsed ? 'Expand' : 'Collapse'} ${stack.name}`}
          className="spatial-folder__toggle"
          onClick={onToggle}
          onPointerDown={e => e.stopPropagation()}
          type="button"
        >
          {collapsed ? '▸' : '▾'}
        </button>
      </div>

      <AnimatePresence>
        {!collapsed &&
          stack.cards.map((card, i) => (
            <PaperCard
              card={{
                ...card,
                // Fan slightly more organic when expanded
                x: card.x + (i % 2 === 0 ? -6 : 10),
                y: card.y + Math.floor(i / 3) * 4
              }}
              key={card.id}
              onSelect={onSelect}
              reduceMotion={reduceMotion}
              selected={selectedId === card.id}
            />
          ))}
      </AnimatePresence>
    </motion.div>
  )
}

export function SpatialDeskPage() {
  const cwd = useValue(host.state.cwd)
  const reduceMotion = useReducedMotion()
  const { panning, reset, scale, stageProps, style, zoomIn, zoomOut } = useZoomPan()
  const [query, setQuery] = useState('')
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [selected, setSelected] = useState<DeskCard | null>(null)
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const [desk, setDesk] = useState<Desk>(() => seedDesk())
  const [status, setStatus] = useState<'scanning' | 'ready' | 'seed'>('scanning')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setStatus('scanning')
      try {
        const roots = await resolveScanRoots(cwd || '', await projectPaths())
        const docs = roots.length ? await scanProjectDocs(roots) : []
        if (cancelled) return
        if (docs.length === 0) {
          setDesk(seedDesk())
          setStatus('seed')
          return
        }
        const next = layoutDesk(docs, roots)
        setDesk(next)
        setCollapsed(Object.fromEntries(next.stacks.map(s => [s.id, s.collapsed])))
        setStatus('ready')
        reset()
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
  }, [cwd, reset])

  const shown = useMemo(() => filterDesk(desk, query), [desk, query])
  const total = cardCount(desk)
  const visible = cardCount(shown)

  return (
    <div className="spatial-desk" data-theme={theme === 'dark' ? 'dark' : 'light'}>
      <div
        className={cn('spatial-desk__stage', panning && 'is-grabbing')}
        data-testid="spatial-stage"
        {...stageProps}
      >
        <div
          className="spatial-desk__world"
          style={{
            ...style,
            width: desk.width,
            height: desk.height,
            left: '50%',
            top: '45%',
            marginLeft: -desk.width / 2,
            marginTop: -desk.height / 2
          }}
        >
          {shown.stacks.map(stack => (
            <FolderPile
              collapsed={collapsed[stack.id] ?? stack.collapsed}
              key={stack.id}
              onSelect={setSelected}
              onToggle={() => setCollapsed(c => ({ ...c, [stack.id]: !(c[stack.id] ?? stack.collapsed) }))}
              reduceMotion={reduceMotion}
              selectedId={selected?.id ?? null}
              stack={stack}
            />
          ))}
        </div>
      </div>

      {status === 'scanning' && <div className="spatial-status">Scanning project papers…</div>}

      <div className="spatial-toolbar" onPointerDown={e => e.stopPropagation()}>
        <input
          aria-label="Filter cards"
          onChange={e => setQuery(e.target.value)}
          placeholder="Filter papers…"
          value={query}
        />
        <Tip label="Zoom out">
          <button onClick={zoomOut} type="button">
            <icons.ZoomOut size={15} />
          </button>
        </Tip>
        <span className="spatial-toolbar__count">{Math.round(scale * 100)}%</span>
        <Tip label="Zoom in">
          <button onClick={zoomIn} type="button">
            <icons.ZoomIn size={15} />
          </button>
        </Tip>
        <Tip label="Reset view">
          <button onClick={reset} type="button">
            <icons.Maximize size={14} />
          </button>
        </Tip>
        <Tip label={theme === 'light' ? 'Dark desk' : 'Light desk'}>
          <button onClick={() => setTheme(t => (t === 'light' ? 'dark' : 'light'))} type="button">
            {theme === 'light' ? <icons.Moon size={14} /> : <icons.Sun size={14} />}
          </button>
        </Tip>
        <span className="spatial-toolbar__count">
          {status === 'scanning' ? '…' : status === 'seed' ? 'demo' : `${visible}/${total}`}
        </span>
      </div>

      <Dialog onOpenChange={open => !open && setSelected(null)} open={selected !== null}>
        <DialogContent className="max-w-md border-border/60 bg-background/95 backdrop-blur-xl">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="pr-8">{selected.title}</DialogTitle>
                <DialogDescription>{selected.summary}</DialogDescription>
              </DialogHeader>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge variant="muted">{selected.type}</Badge>
                <Badge variant="outline">P{selected.priority}</Badge>
                {selected.sourcePath && <Badge variant="outline">{selected.sourcePath}</Badge>}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
