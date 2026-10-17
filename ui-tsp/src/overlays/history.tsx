import { load } from '@tui/lib/history.js'

import type { App } from '../app.js'
import type { Overlay } from '../overlay.js'

import { editQuery, moveSelection, rank } from './search.js'

/** Prompt history is the composer's existing profile-local history, never a second store. */
export function openHistorySearch(app: App): void {
  const items = [...load()].reverse().map((text, index) => ({ id: String(index), text }))
  let query = ''
  let selected: string | undefined
  const shown = () => rank(items, query, item => item.text).map(hit => hit.item)

  const choose = (id: string | undefined) => {
    const item = shown().find(row => row.id === id)

    if (item) {
      app.composer.set(item.text)
      app.close(overlay)
    }
  }

  const overlay: Overlay = {
    key: 'history',
    modal: true,
    node: id => {
      const rows = shown()

      if (!rows.some(row => row.id === selected)) {
        selected = rows[0]?.id
      }

      return <picker
        actions={[{ id: 'use', keys: ['enter'], label: 'Use draft', primary: true }, { id: 'close', keys: ['esc'], label: 'Close' }]}
        empty="No matching prompts"
        items={rows.map(row => ({ id: row.id, label: row.text, mono: true }))}
        key={id.slice('layer.'.length)}
        layout="rows"
        noun="prompts"
        onAction={{ close: () => app.close(overlay), use: () => choose(selected) }}
        onActivate={ev => choose(ev.item)}
        onSelect={ev => { selected = ev.item; app.changed() }}
        order={rows.map(row => row.id)}
        placeholder="Search prompt history…"
        query={query}
        selected={selected}
        size="md"
        state="ready"
        title="Prompt history"
        total={items.length}
      />
    },
    onKey: key => {
      if (key.name === 'escape' || (key.ctrl && key.name === 'c')) {
        app.close(overlay)
      } else if (key.name === 'enter') {
        choose(selected ?? shown()[0]?.id)
      } else {
        const moved = moveSelection(key, shown().map(row => row.id), selected)
        const edited = editQuery(key, query)

        if (moved !== undefined) {
          selected = moved
        } else if (edited !== undefined) {
          query = edited
          selected = shown()[0]?.id
        }
      }

      return true
    }
  }

  app.open(overlay)
}
