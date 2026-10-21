import type { Tree } from '@stencil-hq/tern'

import { KEYBOARD_ACTIONS, matchesAction } from '../actions.js'
import type { App } from '../app.js'
import type { Overlay } from '../overlay.js'

export interface RenderedAction { id: string; label: string; group: string }

/** Traverse only enabled, mounted actions. Labels come from the same rendered nodes. */
export function renderedActions(trees: readonly Tree[]): RenderedAction[] {
  const text = (tree: Tree): string => typeof tree.props.text === 'string' ? tree.props.text : tree.children.map(text).join(' ').trim()

  return trees.flatMap(tree => {
    if (tree.props.hidden) { return [] }

    if (!tree.props.disabled && tree.node.handlers?.onClick) {
      const label = String(tree.props.aria ?? tree.props.title ?? text(tree))

      return label ? [{ id: tree.id, label, group: tree.id.startsWith('main.') ? 'Transcript' : tree.id.startsWith('dock.') ? 'Composer' : 'Sheet' }] : []
    }

    return renderedActions(tree.children)
  })
}

/** TSP focus is caret-only. Use the native picker for visible and AX-selected action focus. */
export function openKeyboardActions(app: App, actions: RenderedAction[], activate: (id: string) => void): void {
  let selected = actions[0]?.id

  const choose = (id = selected) => {
    if (!id || !actions.some(action => action.id === id)) { return }
    app.close(overlay)
    activate(id)
  }

  const overlay: Overlay = {
    key: 'keyboard-actions', modal: true,
    node: id => <picker
      actions={[{ id: 'activate', label: 'Activate', keys: ['enter'], primary: true }, { id: 'close', label: 'Back to draft', keys: ['esc'] }]} empty="No enabled actions"
      items={actions.map(action => ({ id: action.id, label: action.label, group: action.group }))} key={id.slice('layer.'.length)} layout="rows" noun="actions" onAction={{ activate: () => choose(), close: () => app.close(overlay) }} onActivate={event => choose(event.item)}
      onSelect={event => { selected = event.item; app.changed() }}
      order={actions.map(action => action.id)} placeholder="Rendered card and composer actions" query="" selected={selected}
      size="md" state="ready"
      title="Keyboard actions"
      total={actions.length}
    />,
    onKey: key => {
      const action = KEYBOARD_ACTIONS.find(action => matchesAction(action, key))?.action

      if (action === 'close') { app.close(overlay) }

      if (action === 'activate') { choose() }

      if (action === 'next' || action === 'previous') {
        const index = actions.findIndex(action => action.id === selected)
        selected = actions[(index + (action === 'next' ? 1 : -1) + actions.length) % actions.length]?.id
        app.changed()
      }

      return true
    }
  }

  app.open(overlay)
}
