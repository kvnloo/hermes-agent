import type { BrowserBlock, BrowserBlocksResult, BrowserTargetResult } from '@hermes/shared/gateway-events'

import { browserBlocksKeyAction } from '../actions.js'
import type { App } from '../app.js'
import { focusBrowserBlock } from '../browser-blocks.js'
import { Composer } from '../composer.js'
import type { Overlay } from '../overlay.js'

/** No polling or mirrored ownership store: reload only on open or confirmed release. */
export function openBrowserBlocks(app: App): void {
  const sid = app.sid

  if (!sid) {
    return
  }

  let blocks: BrowserBlock[] = []
  let message = 'Loading Tern browser blocks…'
  let busy = false
  let frameTarget: string | undefined
  const frame = new Composer()
  frame.set('main')
  const live = () => app.sid === sid && app.overlays.at(-1) === overlay

  const load = async () => {
    const result = await app.gw.request<BrowserBlocksResult>('browser.blocks', { session_id: sid })

    if (live()) {
      blocks = result.blocks
      message = !result.available
        ? 'Tern browser interface unavailable; existing browser backend is unchanged.'
        : blocks.length
          ? ''
          : 'No browser blocks. The agent opens its own block on first navigation.'
      app.changed()
    }
  }

  const act = async (block: BrowserBlock, intent: 'choose' | 'release' | 'frame') => {
    if (
      !live() ||
      busy ||
      (intent !== 'choose' && (!block.owned || app.busy)) ||
      (!block.owned && (!block.available || app.busy))
    ) {
      return
    }

    busy = true
    app.changed()

    try {
      if (intent === 'release') {
        await app.gw.request('browser.release', { session_id: sid, target_id: block.target_id })

        if (live()) {
          frameTarget = undefined
          await load()
        }
      } else if (intent === 'frame') {
        const result = await app.gw.request<BrowserTargetResult>('browser.frame', {
          session_id: sid,
          target_id: block.target_id,
          frame: frame.text
        })

        if (live()) {
          message = `Block ${result.target_id} · evaluation frame ${result.frame ?? 'main'}`
          frameTarget = undefined
        }
      } else {
        if (block.owned) {
          await focusBrowserBlock(app, block.target_id, sid)
        } else {
          await app.gw.request<BrowserTargetResult>('browser.adopt', { session_id: sid, target_id: block.target_id })
        }

        if (live()) {
          app.close(overlay)
        }
      }
    } catch (error) {
      if (live()) {
        message = error instanceof Error ? error.message : String(error)
      }
    } finally {
      busy = false
      app.changed()
    }
  }

  const overlay: Overlay = {
    key: 'browser-blocks',
    modal: true,
    node: id => (
      <overlay
        anchor="center"
        head="Tern browser blocks"
        key={id.slice('layer.'.length)}
        modal
        role="omp.overlay.browser"
        size="lg"
      >
        <col gap="sm" key="body">
          <text key="title" text="Tern browser blocks" />
          <text
            key="help"
            text="Hand over only a block you want the agent to drive. Release keeps adopted pages; agent-created blocks close."
            wrap="word"
          />
          <text
            key="capabilities"
            text="Child frames support evaluation only; select main before snapshots, input or capture. Console buffering, recording and annotated capture are unavailable, not emulated."
            wrap="word"
          />
          {message ? <text key="message" text={message} wrap="word" /> : null}
          {blocks.map(block => (
            <col gap="sm" key={`target-${block.target_id}`}>
              <text
                key="identity"
                text={`${block.target_id} · ${block.title} · ${block.url} · owner ${block.owner ?? 'docked'}`}
                wrap="word"
              />
              <row gap="sm" key="actions">
                <row
                  key="choose"
                  onClick={() => void act(block, 'choose')}
                  role="omp.btn"
                  title={block.owned ? `Focus block ${block.target_id}` : `Hand over block ${block.target_id}`}
                >
                  <text
                    key="label"
                    text={
                      busy
                        ? 'Working…'
                        : block.owned
                          ? 'Focus'
                          : !block.available
                            ? 'Unavailable / already driven'
                            : app.busy
                              ? 'Wait for turn to finish'
                              : 'Hand over to agent'
                    }
                  />
                </row>
                {block.owned ? (
                  <row
                    key="release"
                    onClick={() => void act(block, 'release')}
                    role="omp.btn"
                    title={`Release block ${block.target_id}`}
                  >
                    <text key="label" text={app.busy ? 'Wait for turn to finish' : 'Release / close owned block'} />
                  </row>
                ) : null}
                {block.owned ? (
                  <row
                    key="frame"
                    onClick={() => {
                      if (live() && !busy && !app.busy) {
                        frameTarget = block.target_id
                        frame.set('main')
                        app.changed()
                      }
                    }}
                    role="omp.btn"
                    title={`Select evaluation frame for block ${block.target_id}`}
                  >
                    <text key="label" text="Evaluation frame…" />
                  </row>
                ) : null}
              </row>
              {frameTarget === block.target_id ? (
                <col key="frame-form">
                  <text
                    key="help"
                    text="Exact native path (main, 0, 1.0). The native page must verify it before selection."
                    wrap="word"
                  />
                  <input
                    cursor={frame.cursor}
                    key="frame-path"
                    onEdit={event => {
                      if (live() && !busy) {
                        frame.edit(event)
                        app.changed()
                      }
                    }}
                    role="omp.ask.input"
                    text={frame.text}
                  />
                  <row key="apply-frame" onClick={() => void act(block, 'frame')} role="omp.btn">
                    <text key="label" text="Verify and select frame" />
                  </row>
                </col>
              ) : null}
            </col>
          ))}
          <row key="close" onClick={() => app.close(overlay)} role="omp.btn">
            <text key="label" text="Close" />
          </row>
        </col>
      </overlay>
    ),
    onKey: key => {
      if (browserBlocksKeyAction(key) === 'close') {
        app.close(overlay)
      }

      return true
    }
  }

  app.open(overlay)
  void load().catch(error => {
    if (live()) {
      message = error instanceof Error ? error.message : String(error)
      app.changed()
    }
  })
}
