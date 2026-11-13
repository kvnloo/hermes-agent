// Throwaway verification harness (t_74bd53a2): mounts the real desktop KanbanBoardPage
// with the app's own providers and a deterministic, privacy-safe REST fixture.
import './styles.css'
import { QueryClientProvider } from '@tanstack/react-query'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router'
import { RootTooltipProvider } from './components/ui/tooltip'
import { I18nProvider, registerPluginLocales } from './i18n'
import { KANBAN_LOCALES } from './plugins/kanban/i18n'
import { queryClient } from './lib/query-client'
import { ThemeProvider } from './themes/context'
import { bindApi } from './plugins/kanban/api'
import { KanbanBoardPage } from './plugins/kanban/board'

const task = (id: string, status: string, assignee = 'alpha', tenant = 'acme') => ({
  id, title: `${status} task ${id}`, body: 'Deterministic privacy-safe fixture', status, assignee, tenant,
  priority: 1, created_at: 1, comment_count: 0, link_counts: { parents: 0, children: 0 }
})
const statuses = ['triage', 'todo', 'ready', 'running', 'blocked', 'review', 'done', 'scheduled']
const columns = statuses.map(s => ({
  name: s,
  tasks: s === 'todo' ? [] : s === 'triage' ? Array.from({ length: 20 }, (_, i) => task(`triage-${i}`, s))
    : s === 'running' ? [task('running-alpha', s), task('running-beta', s, 'beta')]
    : s === 'review' ? [task('review-beta-other', s, 'beta', 'other')] : [task(`${s}-1`, s)]
}))
const board = { columns, tenants: ['acme', 'other'], assignees: ['alpha', 'beta'], latest_event_id: 0, now: 2 }
const all = columns.flatMap(c => c.tasks)
;(window as any).__REST_LOG__ = []
const rest = async (path: string) => {
  ;(window as any).__REST_LOG__.push(path)
  const p = path.split('?')[0]
  if (p === '/board') return board
  if (p === '/boards') return { boards: [{ slug: 'default', name: 'Default', counts: {}, total: all.length }], current: 'default' }
  if (p === '/profiles') return { profiles: [{ name: 'alpha' }, { name: 'beta' }] }
  if (p === '/projects') return { projects: [] }
  if (p === '/orchestration') return { mode: 'auto', default_assignee: 'alpha', profiles: [] }
  if (p === '/config') return { lane_by_profile: true }
  const m = p.match(/^\/tasks\/([^/]+)(\/log)?$/)
  if (m && m[2]) return { content: '', exists: false }
  if (m) return { task: all.find(t => t.id === decodeURIComponent(m[1])), comments: [], events: [], links: { parents: [], children: [] }, runs: [], attachments: [] }
  return {}
}
registerPluginLocales('kanban', KANBAN_LOCALES as any)
const mem = new Map<string, unknown>()
bindApi(rest as any, { get: (k: string, f: unknown) => (mem.has(k) ? mem.get(k) : f), set: (k: string, v: unknown) => mem.set(k, v) } as any, () => () => {})

createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <I18nProvider><ThemeProvider><RootTooltipProvider>
      <HashRouter><div style={{ height: '100vh', width: '100%' }}><KanbanBoardPage /></div></HashRouter>
    </RootTooltipProvider></ThemeProvider></I18nProvider>
  </QueryClientProvider>
)
