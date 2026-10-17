import type { BrowserBlock, BrowserBlocksResult, BrowserTargetResult } from '@hermes/shared/gateway-events'

import { browserBlocksKeyAction } from '../actions.js'
import type { App } from '../app.js'
import { focusBrowserBlock } from '../browser-blocks.js'
import type { Overlay } from '../overlay.js'

/** No polling or mirrored ownership store: reload only when this sheet is opened. */
export function openBrowserBlocks(app: App): void {
  const sid = app.sid

  if (!sid) {
    return
  }

  let blocks: BrowserBlock[] = []
  let message = 'Loading Tern browser blocks…'
  let busy = false
  const live = () => app.sid === sid && app.overlays.includes(overlay)

  const choose = async (block: BrowserBlock) => {
    if (!live() || busy || (!block.owned && (!block.available || app.busy))) {
      return
    }

    busy = true
    app.changed()

    try {
      if (block.owned) {
        await focusBrowserBlock(app, block.target_id, sid)
      } else {
        await app.gw.request<BrowserTargetResult>('browser.adopt', { session_id: sid, target_id: block.target_id })
      }

      if (live()) {
        app.close(overlay)
      }
    } catch (error) {
      if (live()) {
        message = error instanceof Error ? error.message : String(error)
      }
    }

    busy = false
    app.changed()
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
            text="Hand over only a block you want the agent to drive. Adopted blocks are released, never closed."
            wrap="word"
          />
          {message ? <text key="message" text={message} wrap="word" /> : null}
          {blocks.map(block => (
            <row gap="sm" key={`target-${block.target_id}`}>
              <text
                key="identity"
                text={`${block.target_id} · ${block.title} · ${block.url} · owner ${block.owner ?? 'docked'}`}
                wrap="word"
              />
              <row
                key="choose"
                onClick={() => void choose(block)}
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
            </row>
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
  void app.gw
    .request<BrowserBlocksResult>('browser.blocks', { session_id: sid })
    .then(result => {
      if (live()) {
        blocks = result.blocks
        message = !result.available
          ? 'Tern browser interface unavailable; existing browser backend is unchanged.'
          : blocks.length
            ? ''
            : 'No browser blocks. The agent opens its own block on first navigation.'
        app.changed()
      }
    })
    .catch(error => {
      if (live()) {
        message = error instanceof Error ? error.message : String(error)
        app.changed()
      }
    })
}
