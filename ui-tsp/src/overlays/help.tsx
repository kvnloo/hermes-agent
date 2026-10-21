// `/help`: the keyboard shortcuts and every slash command, grouped by the
// backend's `commands.catalog` categories, in omp's hotkeys sheet
// (`omp.overlay.hotkeys`: sections of key/action tables, Close esc).

import type { CommandsCatalogResult } from '@hermes/shared/gateway-events'
import type { Key, SpanData } from '@stencil-hq/tern'

import { actionGroups, matchesAction, REPORT_ACTIONS } from '../actions.js'
import type { App } from '../app.js'
import { FORK_COMMANDS } from '../fork-session.js'
import type { Overlay } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'

import { LSP_COMMANDS } from './lsp.js'
import { TREE_COMMANDS } from './sessions.js'
import { SETTINGS_COMMANDS } from './settings.js'

const KEY = 'help'

/** The shortcuts this frontend handles (composer.ts, app.ts), by group. */
const HOTKEYS: { group: string; rows: [string[], string][] }[] = [
  {
    group: 'Editing',
    rows: [
      [['enter'], 'Send message'],
      [['shift+enter', 'alt+enter'], 'New line (Alt+Enter steers / queues while busy)'],
      [['up', 'down'], 'Move between lines / browse history'],
      [['tab', 'f6'], 'Accept completion / traverse card and composer actions'],
      [['alt+left', 'alt+right', 'alt+b', 'alt+f'], 'Move by word'],
      [['ctrl+a', 'ctrl+e'], 'Start / end of line'],
      [['ctrl+w', 'alt+backspace'], 'Delete word backwards'],
      [['ctrl+u'], 'Delete to start of line'],
      [['alt+d'], 'Delete word forward'],
      [['ctrl+k'], 'Delete to end of line (joins the next line at its end)'],
      [['ctrl+y'], 'Paste the last deleted text'],
      [['ctrl+z', 'shift+ctrl+z'], 'Undo / redo']
    ]
  }
]

/** Opens the help sheet; the command list comes from the gateway's catalog. */
export async function openHelp(app: App) {
  let catalog: CommandsCatalogResult = {}

  try {
    catalog = await app.gw.request<CommandsCatalogResult>('commands.catalog', app.sid ? { session_id: app.sid } : {})
  } catch (error) {
    app.transcript.notice(
      `Could not load the command list: ${error instanceof Error ? error.message : String(error)}`,
      'warning'
    )
  }

  const categories = [
    { name: 'Native Settings', pairs: SETTINGS_COMMANDS },
    { name: 'Native LSP', pairs: LSP_COMMANDS },
    { name: 'Native session', pairs: [...FORK_COMMANDS, ...TREE_COMMANDS] },
    ...(catalog.categories?.length ? catalog.categories : [{ name: 'Commands', pairs: catalog.pairs ?? [] }])
      .map(category => ({
        ...category,
        pairs: (category.pairs ?? []).filter(([command]) => !SETTINGS_COMMANDS.some(([name]) => name === command))
      }))
  ]

  const overlay: Overlay = {
    key: KEY,
    modal: true,
    node: id => (
      <overlay anchor="center" head="Commands and shortcuts" key={id.slice('layer.'.length)} modal role="omp.overlay.hotkeys" size="lg">
        <col gap="lg" key="body">
          <text key="host-keys" text="Host key ownership: Tern and its active preset may intercept shortcuts before Hermes. Use the paired buttons or slash commands when a chord is reserved; configure Hermes bindings in Settings. Tab accepts completions; otherwise opens Keyboard actions. F6 opens sheet/card/composer actions; Tab/Shift+Tab or arrows traverse, Enter activates, Escape returns. Shift+Tab in the composer still cycles effort. Escape belongs to the top question/sheet before interrupting a turn." wrap="word" />
          {[...HOTKEYS, ...actionGroups(app.bindings.actions)].map(({ group, rows }) => (
            <section head={group} key={`keys-${group}`} role="omp.hotkeys.group">
              <table
                cols={[
                  { head: 'Key', id: 'keys' },
                  { grow: 1, head: 'Action', id: 'action' }
                ]}
                key="table"
                role="omp.hotkeys.table"
                rows={rows.map(([keys, action], i) => ({
                  cells: {
                    action: [{ t: action }],
                    keys: keys.flatMap((k, j): SpanData[] => [...(j ? [{ s: 'dim', t: ' ' }] : []), { s: 'key', t: k }])
                  },
                  id: String(i)
                }))}
              />
            </section>
          ))}
          {categories.map(c => (
            <section head={c.name} key={`cmd-${c.name}`} role="omp.hotkeys.group">
              <table
                cols={[
                  { head: 'Command', id: 'command' },
                  { grow: 1, head: 'Description', id: 'action' }
                ]}
                key="table"
                role="omp.hotkeys.table"
                rows={(c.pairs ?? []).map(([command = '', text = ''], i) => ({
                  // The `(usage: …)` tail is `/help <command>`'s business; the table keeps the summary.
                  cells: {
                    action: [{ t: text.replace(/\s*\(usage: .+\)\s*$/, '') }],
                    command: [{ s: 'mono', t: command }]
                  },
                  id: String(i)
                }))}
              />
            </section>
          ))}
          <row align="center" gap="sm" key="actions" role="omp.actions">
            <spacer grow={1} key="fill" />
            <ActionButton
              align="center"
              gap="xs"
              key="close"
              onClick={() => app.close(overlay)}
              role="omp.btn"
              title="Close  escape"
            >
              <text key="label" text="Close" />
              <kbd key="keys" keys={['escape']} />
            </ActionButton>
          </row>
        </col>
      </overlay>
    ),
    onKey: (k: Key) => {
      if (k.name === 'escape' || k.name === 'enter' || k.name === 'q') {
        app.close(overlay)
      } else {
        const intent = REPORT_ACTIONS.find(action => matchesAction(action, k))?.intent

        if (intent?.kind === 'scroll') { app.scrollOverlay(overlay, 'body', intent.to) }
      }

      return true
    }
  }

  app.open(overlay)
}
