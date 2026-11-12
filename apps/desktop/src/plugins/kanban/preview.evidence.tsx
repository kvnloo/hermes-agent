import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'
import { useState } from 'react'

import '../../styles.css'
import './kanban.css'
import { bindApi } from './api'
import { AttentionControls, KanbanBoardPage } from './board'
import { TaskDrawer } from './drawer'
import type { KanbanTask } from './types'

const exactSha = 'eee96a0d021640f62cac5de73360cc0f1a7ec2ac'
let revision = 0
let state: 'active' | 'settled' | 'snoozed' = 'active'
let failNextWake = true
let refreshProof: (() => void) | undefined
const makeTask = (): KanbanTask => ({ assignee: 'canary-worker', attention: { reason: 'receipt', revision, state, wake_at: state === 'snoozed' ? Math.floor(Date.now() / 1_000) + 3_600 : null }, id: 'task-safe', status: 'running', title: 'Privacy-safe evidence task' })
const makeBoard = () => ({ assignees: ['canary-worker'], columns: [{ name: 'running', tasks: [makeTask()] }, { name: 'review', tasks: [{ ...makeTask(), id: 'task-review', status: 'review', title: 'Production review task' }] }], latest_event_id: revision + 2, now: Math.floor(Date.now() / 1_000), tenants: [] })

const rest = async <T,>(path: string, opts?: { body?: unknown; method?: string }): Promise<T> => {
  if (path.includes('/tasks/task-safe/attention')) {
    const body = (opts?.body ?? {}) as { action?: string }
    if (body.action === 'wake' && failNextWake) {
      failNextWake = false
      throw new Error('Wake was not accepted — synthetic failure proof')
    }
    state = body.action === 'settle' ? 'settled' : body.action === 'snooze' ? 'snoozed' : 'active'
    revision += 1
    refreshProof?.()
    return { attention: makeTask().attention, idempotent: false } as T
  }
  if (path.startsWith('/tasks/task-safe/log')) return { content: '', exists: false, size_bytes: 0, truncated: false } as T
  if (path.startsWith('/tasks/task-safe')) return { attachments: [], comments: [], events: [], links: { children: [], parents: [] }, runs: [], task: makeTask() } as T
  if (path.startsWith('/boards')) return { boards: [{ default_workspace_kind: 'scratch', slug: 'default' }], current: 'default' } as T
  if (path.startsWith('/board')) return makeBoard() as T
  if (path.startsWith('/profiles')) return { profiles: [] } as T
  if (path.startsWith('/projects')) return { projects: [] } as T
  throw new Error(`Unexpected preview request: ${path}`)
}

bindApi(rest, { get: <T,>(_key: string, fallback: T) => fallback, remove: () => undefined, set: () => undefined }, () => () => undefined)
const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } })

function Preview() {
  const [, refresh] = useState(0)
  refreshProof = () => refresh(value => value + 1)
  return <div className="h-screen w-screen overflow-hidden bg-(--ui-bg-canvas)">
    <header style={{ background: '#201609', borderBottom: '1px solid #d49b32', color: '#ffe2a5', fontFamily: 'ui-monospace, monospace', fontSize: 11, lineHeight: 1.35, padding: '6px 10px', pointerEvents: 'none', position: 'relative', zIndex: 100 }}>
      <strong>SYNTHETIC ONLY</strong> · PR #88752 · exact SHA <span style={{ overflowWrap: 'anywhere' }}>{exactSha}</span><br />
      Production Desktop source. First Wake intentionally fails; second Wake succeeds. Dashboard bundle: <a href="/kanban-dashboard-evidence.html" style={{ color: '#fff' }}>open surface</a>.
    </header>
    <section aria-label="Attention lifecycle proof" style={{ background: '#151515', color: '#eee', padding: '120px 10px 4px', position: 'relative', zIndex: 99 }}>
      <AttentionControls task={makeTask()} />
    </section>
    <main style={{ height: 'calc(100vh - 96px)' }} data-production-surface="desktop">
      <KanbanBoardPage />
      <TaskDrawer columns={['running', 'review']} id="task-safe" onClose={() => undefined} onOpen={() => undefined} />
    </main>
  </div>
}

createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queryClient}><Preview /></QueryClientProvider>)
