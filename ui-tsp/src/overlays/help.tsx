// `/help`: the keyboard shortcuts and every slash command, grouped by the
// backend's `commands.catalog` categories, in omp's hotkeys sheet
// (`omp.overlay.hotkeys`: sections of key/action tables, Close esc).

import type { CommandsCatalogResult } from '@hermes/shared/gateway-events'
import type { Key, SpanData } from '@stencil-hq/tern'

import type { App } from '../app.js'
import type { Overlay } from '../overlay.js'

import { SETTINGS_COMMANDS } from './settings.js'

const KEY = 'help'

/** The shortcuts this frontend handles (composer.ts, app.ts), by group. */
const HOTKEYS: { group: string; rows: [string[], string][] }[] = [
  {
    group: 'Editing',
    rows: [
      [['enter'], 'Send message'],
      [['shift+enter', 'alt+enter'], 'New line'],
      [['up', 'down'], 'Move between lines / browse history'],
      [['tab'], 'Accept the completion'],
      [['alt+left', 'alt+right', 'alt+b', 'alt+f'], 'Move by word'],
      [['ctrl+a', 'ctrl+e'], 'Start / end of line'],
      [['ctrl+w', 'alt+backspace'], 'Delete word backwards'],
      [['ctrl+u'], 'Delete to start of line'],
      [['alt+d'], 'Delete word forward'],
      [['ctrl+k'], 'Delete to end of line (joins the next line at its end)'],
      [['ctrl+y'], 'Paste the last deleted text'],
      [['ctrl+z', 'shift+ctrl+z'], 'Undo / redo']
    ]
  },
  {
    group: 'Control',
    rows: [
      [['escape'], 'Close the completion / interrupt the agent'],
      [['shift+tab'], 'Cycle the reasoning effort'],
      [['alt+up'], 'Edit the oldest queued prompt'],
      [['ctrl+c'], 'Clear the draft / interrupt / exit (twice)'],
      [['ctrl+d'], 'Delete forward / exit (empty prompt)']
    ]
  }
]

/** Opens the help sheet; the command list comes from the gateway's catalog. */
export async function openHelp(app: App) {
  const sid = app.sid
  const generation = app.sessionGeneration
  const overlayGeneration = app.overlayGeneration
  let catalog: CommandsCatalogResult = {}

  try {
    catalog = await app.gw.request<CommandsCatalogResult>('commands.catalog', sid ? { session_id: sid } : {})
  } catch (error) {
    if (app.sid !== sid || app.sessionGeneration !== generation || app.overlayGeneration !== overlayGeneration) {
      return
    }

    app.transcript.notice(
      `Could not load the command list: ${error instanceof Error ? error.message : String(error)}`,
      'warning'
    )
  }

  if (app.sid !== sid || app.sessionGeneration !== generation || app.overlayGeneration !== overlayGeneration) {
    return
  }

  if (catalog.warning) {
    app.transcript.notice(catalog.warning, 'warning')
  }

  const categories = [
    { name: 'Native Settings', pairs: SETTINGS_COMMANDS },
    ...(catalog.categories?.length ? catalog.categories : [{ name: 'Commands', pairs: catalog.pairs ?? [] }])
      .map(category => ({
        ...category,
        pairs: (category.pairs ?? []).filter(([command]) => !SETTINGS_COMMANDS.some(([name]) => name === command))
      }))
  ]
  const listed = new Set<string>()

  for (const category of categories) {
    for (const [command] of category.pairs) {
      listed.add(command)
    }
  }

  const uncategorized = (catalog.pairs ?? []).filter(([command]) => command !== undefined && !listed.has(command))

  if (uncategorized.length) {
    categories.push({ name: 'Other commands', pairs: uncategorized })
  }

  const overlay: Overlay = {
    key: KEY,
    modal: true,
    node: id => (
      <overlay anchor="center" head="Commands and shortcuts" key={id.slice('layer.'.length)} modal role="omp.overlay.hotkeys" size="lg">
        <col gap="lg" key="body">
          {HOTKEYS.map(({ group, rows }) => (
            <section head={group} key={`keys-${group}`} role="omp.hotkeys.group">
              <col gap="sm" key="rows">
                {rows.map(([keys, action], i) => (
                  <col gap="xs" key={String(i)} role="omp.hotkeys.row">
                    <text
                      key="keys"
                      role="omp.hotkeys.keys"
                      spans={keys.flatMap((k, j): SpanData[] => [...(j ? [{ t: '  ' }] : []), { s: 'key', t: k }])}
                      wrap="char"
                    />
                    <text key="action" role="omp.hotkeys.description" text={action} wrap="word" />
                  </col>
                ))}
              </col>
            </section>
          ))}
          {categories.map(c => (
            <section head={c.name} key={`cmd-${c.name}`} role="omp.hotkeys.group">
              <col gap="sm" key="rows">
                {(c.pairs ?? []).map(([command = '', text = ''], i) => (
                  <col gap="xs" key={String(i)} role="omp.hotkeys.row">
                    <text key="command" role="omp.hotkeys.command" spans={[{ s: 'mono', t: command }]} wrap="char" />
                    <text
                      key="description"
                      role="omp.hotkeys.description"
                      text={text}
                      wrap="word"
                    />
                  </col>
                ))}
              </col>
            </section>
          ))}
          <row align="center" gap="sm" key="actions" role="omp.actions">
            <spacer grow={1} key="fill" />
            <row
              align="center"
              gap="xs"
              key="close"
              onClick={() => app.close(overlay)}
              role="omp.btn"
              title="Close  escape"
            >
              <text key="label" text="Close" />
              <kbd key="keys" keys={['escape']} />
            </row>
          </row>
        </col>
      </overlay>
    ),
    onKey: (k: Key) => {
      if (k.name === 'escape' || k.name === 'enter' || k.name === 'q') {
        app.close(overlay)
      }

      return true
    }
  }

  app.open(overlay)
}
