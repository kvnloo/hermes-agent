import { Button, cn, Codicon, ErrorState, Loader, useQuery } from '@hermes/plugin-sdk'
import { useEffect, useMemo, useRef, useState } from 'react'

import { fetchRoadmap, roadmapKey } from './api'
import type { RoadmapProjection, RoadmapScope } from './types'

interface RoadmapViewProps {
  onReturnToBoard: () => void
  slug: string
}

const TYPE_DEPTH: Record<RoadmapScope['type'], number> = {
  company: 0,
  portfolio: 1,
  workstream: 2,
  project: 3,
  epic: 4,
  sprint: 5,
  board: 6
}

function ScopeDetail({ onClose, scope }: { onClose: () => void; scope: RoadmapScope }) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const dialogRef = useRef<HTMLElement>(null)
  const statuses = Object.entries(scope.rollup.status_counts)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
      } else if (event.key === 'Tab') {
        const focusable = dialogRef.current?.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
        if (!focusable?.length) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <aside
      aria-label={`${scope.name} details`}
      aria-modal="true"
      className="fixed inset-x-0 bottom-0 z-30 max-h-[72dvh] overflow-y-auto rounded-t-xl border-t border-(--ui-stroke-secondary) bg-(--ui-bg-elevated) p-4 shadow-xl md:static md:z-auto md:max-h-none md:w-80 md:shrink-0 md:rounded-lg md:border md:shadow-none"
      ref={dialogRef}
      role="dialog"
    >
      <div className="flex min-h-11 items-center gap-2">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-foreground">{scope.name}</div>
          <div className="text-[0.6875rem] capitalize text-(--ui-text-tertiary)">{scope.type}</div>
        </div>
        <Button aria-label="Close details" onClick={onClose} ref={closeRef} size="icon-sm" variant="ghost">
          <Codicon name="close" />
        </Button>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-md bg-(--ui-bg-quinary) p-2">
          <dt className="text-(--ui-text-tertiary)">Tasks</dt>
          <dd className="mt-1 text-base font-semibold tabular-nums">{scope.rollup.task_count}</dd>
        </div>
        <div className="rounded-md bg-(--ui-bg-quinary) p-2">
          <dt className="text-(--ui-text-tertiary)">Outcomes</dt>
          <dd className="mt-1 text-base font-semibold tabular-nums">{scope.rollup.verified_outcomes}</dd>
        </div>
      </dl>
      <div className="mt-4 text-[0.6875rem] font-medium text-(--ui-text-secondary)">Status components</div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {statuses.map(([status, count]) => (
          <span className="rounded-md bg-(--ui-bg-quinary) px-2 py-1 text-[0.6875rem]" key={status}>
            {status} {count}
          </span>
        ))}
      </div>
      <div className="mt-4 space-y-1 text-[0.6875rem] text-(--ui-text-tertiary)">
        <p>Critical path: {scope.rollup.critical_path.state}</p>
        <p>Blocked: {scope.rollup.blocker_task_ids.length}</p>
        <p>Event revision: {scope.provenance.latest_event_id}</p>
        <p className="break-all font-mono">Source {scope.provenance.source_revision.slice(0, 12)}</p>
      </div>
    </aside>
  )
}

function RoadmapRows({ data, onSelect, selected }: { data: RoadmapProjection; onSelect: (scope: RoadmapScope) => void; selected: null | string }) {
  const children = useMemo(() => {
    const grouped = new Map<null | string, RoadmapScope[]>()
    for (const scope of data.scopes) {
      grouped.set(scope.parent_id, [...(grouped.get(scope.parent_id) ?? []), scope])
    }
    return grouped
  }, [data.scopes])

  const ordered: RoadmapScope[] = []
  const visit = (parent: null | string) => {
    for (const scope of children.get(parent) ?? []) {
      ordered.push(scope)
      visit(scope.id)
    }
  }
  visit(null)

  return (
    <div aria-label="Roadmap hierarchy" className="min-w-0 flex-1 overflow-y-auto" role="tree">
      {ordered.map(scope => {
        const done = scope.rollup.status_counts.done ?? 0
        const total = scope.rollup.task_count
        const progress = total > 0 ? Math.round((done / total) * 100) : 0
        return (
          <button
            aria-selected={selected === scope.id}
            className={cn(
              'grid min-h-11 w-full grid-cols-[minmax(0,1fr)_5rem] items-center gap-3 border-b border-(--ui-stroke-tertiary) px-3 text-left transition-colors hover:bg-(--chrome-action-hover) focus-visible:outline-2 focus-visible:outline-(--dt-composer-ring)',
              selected === scope.id && 'bg-primary/[0.06]'
            )}
            key={scope.id}
            onClick={() => onSelect(scope)}
            role="treeitem"
            style={{ paddingLeft: `${12 + TYPE_DEPTH[scope.type] * 14}px` }}
            type="button"
          >
            <span className="min-w-0 py-2">
              <span className="flex min-w-0 items-center gap-2">
                <Codicon className="shrink-0 text-(--ui-text-tertiary)" name={scope.board_bound ? 'project' : 'folder'} />
                <span className="truncate text-xs font-medium text-foreground">{scope.name}</span>
                {scope.rollup.blocker_task_ids.length > 0 && (
                  <span className="shrink-0 text-[0.625rem] text-destructive">{scope.rollup.blocker_task_ids.length} blocked</span>
                )}
              </span>
              <span className="mt-0.5 block pl-6 text-[0.625rem] capitalize text-(--ui-text-quaternary)">
                {scope.type} · {total} tasks
              </span>
            </span>
            <span aria-label={`${progress}% complete`} className="text-right text-[0.6875rem] tabular-nums text-(--ui-text-tertiary)">
              {done}/{total}
            </span>
          </button>
        )
      })}
    </div>
  )
}

export function RoadmapView({ onReturnToBoard, slug }: RoadmapViewProps) {
  const { data, error, isPending, refetch } = useQuery({
    queryFn: fetchRoadmap,
    queryKey: roadmapKey(slug),
    refetchInterval: 60_000
  })
  const [selectedId, setSelectedId] = useState<null | string>(null)
  const returnFocusRef = useRef<HTMLElement | null>(null)
  const selected = data?.scopes.find(scope => scope.id === selectedId) ?? null

  const openScope = (scope: RoadmapScope) => {
    returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setSelectedId(scope.id)
  }

  const closeScope = () => {
    setSelectedId(null)
    requestAnimationFrame(() => returnFocusRef.current?.focus())
  }

  if (isPending) {
    return <div className="grid flex-1 place-items-center"><Loader type="lemniscate-bloom" /></div>
  }
  if (error || !data) {
    return <div className="grid flex-1 place-items-center"><ErrorState title="Roadmap unavailable"><Button onClick={() => void refetch()} variant="outline">Retry</Button></ErrorState></div>
  }
  if (!data.capability || data.state === 'absent') {
    return <div className="grid flex-1 place-items-center px-4 text-center"><div className="space-y-3"><p className="text-xs text-(--ui-text-tertiary)">This board has no Roadmap catalog.</p><Button onClick={onReturnToBoard} variant="outline">Return to Board</Button></div></div>
  }
  if (data.state === 'invalid' || data.state === 'unavailable') {
    return <div className="grid flex-1 place-items-center"><ErrorState title={data.warnings[0] || 'Roadmap data failed closed'}><Button onClick={() => void refetch()} variant="outline">Retry</Button></ErrorState></div>
  }
  if (data.scopes.length === 0) {
    return <div className="grid flex-1 place-items-center text-xs text-(--ui-text-tertiary)">No scopes are bound to this board.</div>
  }

  return (
    <div className="flex min-h-0 flex-1 gap-3 overflow-hidden px-4 pb-3">
      <RoadmapRows data={data} onSelect={openScope} selected={selectedId} />
      {selected && <ScopeDetail onClose={closeScope} scope={selected} />}
    </div>
  )
}
