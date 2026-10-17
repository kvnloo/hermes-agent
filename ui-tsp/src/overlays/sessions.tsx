// /sessions is a resume list; /tree is a copied-session lineage projection.
// Both browse metadata only. Selection never resumes, forks or rewinds.
import type { SessionRenameResult, SessionTreeResult, SessionTreeRow, SessionTreeSort } from '@hermes/shared/gateway-events'
import type { JSX, Key, PickerItem } from '@stencil-hq/tern'

import { SESSION_ACTIONS, sessionKeyAction } from '../actions.js'
import type { App } from '../app.js'
import { forkSession } from '../fork-session.js'
import type { Overlay } from '../overlay.js'
import { adjacentBranch, projectSessionTree } from '../session-tree.js'

import { confirmOverlay } from './prompts.js'
import { editQuery, moveSelection } from './search.js'

export const TREE_COMMANDS: [string, string][] = [
  ['/tree', 'Browse copied-session branches; selection only highlights, activation confirms resume']
]

const SORTS: readonly SessionTreeSort[] = ['recent', 'title', 'path']

export function openSessionPicker(app: App, tree = false) {
  const sid = app.sid
  const storedSid = app.storedSid
  let alive = true
  let revision = 0
  let state: 'loading' | 'ready' | 'error' = 'loading'
  let message = ''
  let rows: SessionTreeRow[] = []
  let visible = new Set<string>()
  let query = ''
  let selected: string | undefined
  let pageSelection: string | undefined
  let nextOffset: number | null = null
  let total = 0
  let sort: SessionTreeSort = 'recent'
  let paths = true
  let rename: { id: string; title: string } | null = null
  let writing = false
  const current = () => alive && app.sid === sid && app.storedSid === storedSid && app.overlays.includes(overlay)
  const top = () => current() && app.overlays.at(-1) === overlay
  const projection = () => projectSessionTree(rows, visible, storedSid)
  const shown = () => tree ? projection().entries.map(entry => entry.row.id) : [...visible]

  const repairSelection = () => {
    const ids = shown()

    if (!selected || !ids.includes(selected)) {
      selected = ids.includes(storedSid ?? '') ? storedSid ?? undefined : ids[0]
    }
  }

  const load = async (offset = 0) => {
    const token = ++revision

    if (!offset) {
      pageSelection = selected
    }

    state = 'loading'
    message = ''
    app.changed()

    try {
      const result = await app.gw.request<SessionTreeResult>('session.tree', {
        active_session_id: storedSid, limit: 200, offset, query,
        selected_session_id: pageSelection ?? null, sort
      })

      if (!current() || token !== revision) {
        return
      }

      const merged = new Map((offset ? rows : []).map(row => [row.id, row]))

      // A page row supersedes its older ancestor-context copy.
      for (const row of [...result.ancestors, ...result.sessions]) {
        merged.set(row.id, row)
      }

      rows = [...merged.values()]
      visible = new Set([...(offset ? visible : []), ...result.sessions.map(row => row.id)])
      nextOffset = result.next_offset
      total = result.total
      state = 'ready'
      repairSelection()
    } catch (error) {
      if (!current() || token !== revision) {
        return
      }

      state = 'error'
      message = error instanceof Error ? error.message : String(error)
    }

    app.changed()
  }

  const changeQuery = (value: string) => {
    query = value
    void load()
  }

  const report = (error: unknown) => {
    if (current()) {
      message = error instanceof Error ? error.message : String(error)
      app.changed()
    }
  }

  const saveName = async () => {
    if (!top() || !rename || writing || !rename.title.trim()) {
      return
    }

    const edit = { ...rename }
    writing = true
    app.changed()

    try {
      const result = await app.gw.request<SessionRenameResult>('session.rename', { session_key: edit.id, title: edit.title.trim() })

      if (!current()) {
        return
      }

      rows = rows.map(row => row.id === result.session_key ? { ...row, title: result.title } : row)
      rename = null
      await load()
    } catch (error) {
      report(error)
    } finally {
      writing = false
      app.changed()
    }
  }

  const confirm = (kind: 'resume' | 'fork' | 'delete', id: string | undefined) => {
    if (!top() || state !== 'ready' || !id || !visible.has(id) || writing || rename) {
      return
    }

    const row = rows.find(row => row.id === id)

    if (!row || (kind === 'resume' && id === storedSid)) {
      return
    }

    if ((kind === 'fork' && id !== storedSid) || (kind === 'delete' && id === storedSid)) {
      message = kind === 'fork' ? 'Resume this branch before forking it.' : 'The open session cannot be deleted.'
      app.changed()

      return
    }

    const titles = { delete: 'Delete saved session?', fork: 'Fork current session into a new pane?', resume: 'Resume saved session?' }
    const labels = { delete: 'Delete', fork: 'Fork', resume: 'Resume' }
    app.open(confirmOverlay(app, {
      confirm: labels[kind],
      detail: `${labelOf(row)} · ${row.cwd || 'No workspace'} · ${row.id}. ${kind === 'resume' ? 'Replaces this pane’s transcript; no history is undone.' : kind === 'fork' ? 'Copies history into a separate stored session.' : 'Permanently removes its stored transcript.'}`,
      onConfirm: () => {
        if (!current() || selected !== id || app.busy || app.rewinding || writing) {
          return
        }

        const operations = {
          delete: async () => {
            writing = true

            try {
              await app.gw.request('session.delete', { session_id: id })

              if (current()) {
                await load()
              }
            } finally {
              writing = false
              app.changed()
            }
          },
          fork: async () => {
            app.close(overlay)
            await forkSession(app)
          },
          resume: async () => {
            app.close(overlay)
            await app.resume(row.resolved_id || row.id)
          }
        }

        void operations[kind]().catch(error => {
          // Resume/fork close the picker intentionally, but still report errors
          // only to the original session, never a newly focused pane/session.
          if (app.sid === sid) {
            app.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
            app.changed()
          }
        })
      },
      title: titles[kind]
    }))
  }

  const actions = {
    activate: () => rename ? void saveName() : confirm('resume', selected),
    clear: () => changeQuery(''),
    close: () => {
      if (rename && !writing) {
        rename = null
        app.changed()
      } else if (!writing) {
        app.close(overlay)
      }
    },
    delete: () => confirm('delete', selected),
    fork: () => confirm('fork', selected),
    more: () => {
      if (nextOffset !== null && state !== 'loading') {
        void load(nextOffset)
      }
    },
    nextBranch: () => { selected = adjacentBranch(projection(), selected, 1) },
    path: () => { paths = !paths },
    previousBranch: () => { selected = adjacentBranch(projection(), selected, -1) },
    rename: () => {
      const row = rows.find(row => row.id === selected)

      if (row && state === 'ready' && !writing) {
        rename = { id: row.id, title: row.title ?? '' }
      }
    },
    retry: () => void load(),
    search: () => changeQuery(''),
    sort: () => {
      sort = SORTS[(SORTS.indexOf(sort) + 1) % SORTS.length] ?? 'recent'
      void load()
    }
  }

  const invoke = (intent: keyof typeof actions) => {
    if (top() && !writing && (!rename || intent === 'activate' || intent === 'close')) {
      actions[intent]()
      app.changed()
    }
  }

  const overlay: Overlay = {
    key: tree ? 'session-tree' : 'sessions',
    modal: true,
    onClose: () => { alive = false; revision++ },
    node: id => {
      const projected = projection()
      const depths = new Map(projected.entries.map(entry => [entry.row.id, entry.depth]))
      const row = rows.find(row => row.id === selected)
      const order = shown()

      return (
        <picker
          actions={SESSION_ACTIONS.map(action => ({
            ...action,
            disabled: writing || (action.id === 'more' && nextOffset === null) || (action.id === 'fork' && selected !== storedSid) ? true : undefined,
            label: action.id === 'sort' ? `Sort: ${sort}` : action.id === 'path' ? `Paths: ${paths ? 'on' : 'off'}` : action.label
          }))}
          columns={[{ format: 'dim', id: 'size' }, ...(paths ? [{ format: 'dim', id: 'path' }] : [])]}
          current={storedSid ? [storedSid] : []}
          empty="No saved sessions match"
          items={rows.filter(row => visible.has(row.id)).map(row => itemOf(row, tree ? depths.get(row.id) : undefined, paths))}
          key={id.slice('layer.'.length)}
          layout={tree ? 'tree' : 'cards'}
          message={message || (rename ? 'Editing title · Enter saves · Escape cancels' : undefined)}
          noun="sessions"
          onAction={{
            ...Object.fromEntries(SESSION_ACTIONS.map(action => [action.id, () => invoke(action.id)])),
            clear: () => invoke('clear'),
            retry: () => invoke('retry')
          }}
          onActivate={ev => {
            if (top() && visible.has(ev.item) && !rename) {
              selected = ev.item
              confirm('resume', selected)
            }
          }}
          onSelect={ev => {
            if (top() && visible.has(ev.item) && !rename) {
              selected = ev.item
              app.changed()
            }
          }}
          order={order}
          placeholder={rename ? 'New session title…' : 'Search all sessions by title, ID or path…'}
          preview="side"
          query={rename?.title ?? query}
          selected={selected}
          size="lg"
          state={state}
          subtitle={`Copied sessions, not an entry DAG · ${visible.size} of ${total} matches${nextOffset === null ? '' : ' · Load more available'}`}
          title={tree ? 'Session / branch tree' : 'Saved sessions'}
          total={total}
        >
          {row ? preview(row, row.id === storedSid) : null}
        </picker>
      )
    },
    onKey: (key: Key) => {
      if (!top()) {
        return true
      }

      const intent = sessionKeyAction(key)

      if (intent) {
        invoke(intent)
      } else if (!writing && rename) {
        const edited = editQuery(key, rename.title)

        if (edited !== undefined) {
          rename.title = edited
        }
      } else if (!writing) {
        const moved = moveSelection(key, shown(), selected)
        const edited = moved === undefined ? editQuery(key, query) : undefined

        if (moved !== undefined) {
          selected = moved
        } else if (edited !== undefined) {
          changeQuery(edited)
        }
      }

      return true
    }
  }

  app.open(overlay)
  void load()
}

function labelOf(row: SessionTreeRow): string {
  return row.title?.trim() || row.preview?.trim() || 'Untitled session'
}

function itemOf(row: SessionTreeRow, depth: number | undefined, paths: boolean): PickerItem {
  return {
    badges: row.parent_session_id ? [{ text: row.edge_kind === 'fork' ? 'copied fork' : row.edge_kind }] : undefined,
    depth,
    detail: row.preview || undefined,
    facts: { size: `${row.message_count} msgs`, ...(paths ? { path: row.cwd || 'No workspace' } : {}) },
    id: row.id,
    label: labelOf(row),
    title: row.id
  }
}

function preview(row: SessionTreeRow, isCurrent: boolean): JSX.Element[] {
  return [
    <text key="title" role="omp.picker.title" text={labelOf(row)} />,
    <kv items={[
      { k: [{ t: 'Workspace' }], v: row.cwd || 'No workspace' },
      { k: [{ t: 'ID' }], v: row.id },
      { k: [{ t: 'Messages' }], v: String(row.message_count) },
      { k: [{ t: 'Started' }], v: row.started_at ? new Date(row.started_at * 1000).toLocaleString() : 'Unknown' },
      { k: [{ t: 'Source' }], v: row.source ?? '' },
      ...(row.parent_session_id ? [
        { k: [{ t: 'Parent session' }], v: row.parent_session_id },
        { k: [{ t: 'Edge' }], v: row.edge_kind },
        { k: [{ t: 'Parent branch-point row' }], v: row.branch_message_id == null ? 'Unknown (legacy or unstored tail)' : String(row.branch_message_id) },
        { k: [{ t: 'Copied messages at fork' }], v: row.copied_message_count == null ? 'Unknown' : String(row.copied_message_count) }
      ] : []),
      ...(isCurrent ? [{ k: [{ t: 'Status' }], v: 'Open in this pane' }] : [])
    ]} key="facts" />,
    <text key="model" role="omp.picker.detail" text="Hermes branches copy history into separate sessions. Navigation never undoes messages." wrap="word" />
  ]
}
