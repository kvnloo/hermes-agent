// The app: one inline Tern surface (role `omp.session`, so Tern's chat styles
// apply) over one tui_gateway session. Gateway events fold into the
// transcript, keys go to the top overlay or the composer, and every change
// schedules one render of the whole view; the SDK diffs it into frame ops.

import type {
  ConfigGetResult,
  ConfigSetResult,
  SessionLiveInfo,
  SessionResumeResult,
  SkinPayload,
  TranscriptMessage,
  Usage
} from '@hermes/shared/gateway-events'
import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import { parseCommandDispatch, parseSlashCommand } from '@hermes/shared/slash'
import type { Key, Session, Surface, TspEvent } from '@stencil-hq/tern'
import { describeSlashExecError, shouldFallbackToDispatch } from '@tui/app/userMessages.js'
import type { GatewayClient } from '@tui/gatewayClient.js'
import type { AnyGatewayEvent } from '@tui/gatewayTypes.js'
import { writeActiveSessionFile } from '@tui/lib/activeSessionFile.js'

import logo from '../assets/logo.png'

import { localCommand } from './commands.js'
import { Composer } from './composer.js'
import { type Busy, busyFrom, ownsEvent, Switches } from './flow.js'
import type { Overlay, OverlayHost } from './overlay.js'
import { Completion } from './overlays/completion.js'
import { openModelPicker } from './overlays/models.js'
import { promptOverlay } from './overlays/prompts.js'
import { openSettings } from './overlays/settings.js'
import { paletteOf } from './palette.js'
import { Transcript } from './transcript.js'
import { dockNodes } from './view/dock.js'
import { entryNode } from './view/transcript.js'
import { randomTip, type WelcomeContext } from './view/welcome.js'

/** The composer's `editor` node id (dock → composer → line → input). */
export const INPUT_ID = 'dock.composer.line.input'

const EXIT_ARM_MS = 1500
/** What Shift+Tab / the effort chip cycle through (hermes's `none` turns reasoning off). */
const EFFORTS = ['none', 'low', 'medium', 'high', 'xhigh']

const cancellationKey = (generation: number, sessionId: string | undefined, id: string) =>
  `${generation}\u0000${sessionId ?? ''}\u0000${id}`

interface CreateResult extends Partial<
  Pick<SessionResumeResult, 'inflight' | 'running' | 'status' | 'turn_started_at'>
> {
  session_id: string
  stored_session_id?: string | null
  info?: SessionLiveInfo
  messages?: TranscriptMessage[]
}

interface HistoryUndo {
  events: AnyGatewayEvent[]
  generation: number
  phase: 'pending' | 'replaying'
  sid: string
}

/** Runs the Tern frontend until the user quits; resolves the exit code. */
export class App implements OverlayHost {
  readonly transcript = new Transcript()
  readonly composer = new Composer()
  readonly overlays: Overlay[] = []
  sid: string | null = null
  /** The stored (database) id of the open session: what `session.list` rows are keyed by. */
  storedSid: string | null = null
  info: SessionLiveInfo | null = null
  usage: Usage | null = null
  busy: Busy | null = null
  queue: { text: string; display?: string }[] = []
  readonly #tern: Session
  readonly #gw: GatewayClient
  readonly #completion: Completion
  readonly #welcome: WelcomeContext
  #surface!: Surface
  /** Owners of native handlers in the last rendered layer, not the current stack. */
  readonly #layerOwners = new Map<string, Overlay>()
  readonly #overlayIds = new WeakMap<Overlay, string>()
  #overlaySerial = 0
  #scheduled = false
  /** The field holding Tern's caret, as last sent. */
  #focus: string | null = INPUT_ID
  #exitArmed = 0
  #done = Promise.withResolvers<number>()
  readonly #switches = new Switches()
  /** Changes on every new/resume/reattach request, even before a new sid is adopted. */
  #sessionGeneration = 0
  /** Destination traffic received during a switch, owned by its generation and transport order. */
  #switchTraffic: (
    | { generation: number; event: AnyGatewayEvent }
    | { generation: number; request: ServerRequest }
  )[] = []
  #historyUndo: HistoryUndo | null = null
  readonly #cancelledRequestIds = new Set<string>()
  readonly #cancelledApprovalIds = new Set<string>()
  /** Open approval prompts' overlay keys → their approval-queue `request_id` (what approval.cancelled names). */
  readonly #approvalIds = new Map<string, string>()
  /** The launcher's startup image until it is attached to the first session (the queue waits for it). */
  #startupImage = process.env.HERMES_TUI_IMAGE?.trim() ?? ''
  #effortWrites: Promise<unknown> = Promise.resolve()
  #effortRequested: { generation: number; sid: string; value: string } | null = null

  constructor(tern: Session, gw: GatewayClient, version: string) {
    this.#tern = tern
    this.#gw = gw
    this.#completion = new Completion(this, gw, () => this.sid, () => this.sessionGeneration)
    this.#welcome = {
      tip: randomTip(process.env.HERMES_PYTHON_SRC_ROOT ?? ''),
      version: version && version !== 'unknown' ? `v${version}` : ''
    }
  }

  /** The gateway, for overlays that issue their own RPCs. */
  get gw(): GatewayClient {
    return this.#gw
  }

  /** Monotonic owner token; changes as soon as any new/resume/reattach switch begins. */
  get sessionGeneration(): number {
    return this.#sessionGeneration
  }

  /** Invalidates asynchronous overlay work when a newer overlay has opened. */
  get overlayGeneration(): number {
    return this.#overlaySerial
  }

  async run(): Promise<number> {
    this.#surface = this.#tern.open({ id: 'hermes', mode: 'inline', role: 'omp.session', title: 'hermes' })
    const dispatch = this.#surface.dispatch.bind(this.#surface)

    this.#surface.dispatch = event => {
      const handler = dispatch(event)

      if (!handler || !('id' in event) || typeof event.id !== 'string' || !event.id.startsWith('layer.')) {
        return handler
      }

      let owner: Overlay | undefined
      let rootId = ''

      for (const [root, overlay] of this.#layerOwners) {
        if (
          root.length > rootId.length &&
          event.id.startsWith(root) &&
          (event.id.length === root.length || event.id[root.length] === '.')
        ) {
          owner = overlay
          rootId = root
        }
      }

      if (!owner) {
        return handler
      }

      // Session queues handler calls. Ownership must still hold when the call runs.
      return () => {
        if (!this.#surface.closed && this.overlays.at(-1) === owner && this.#overlayIds.get(owner) === rootId) {
          return handler()
        }
      }
    }

    if (this.#tern.caps.features.includes('blobs')) {
      this.#welcome.logo = this.#tern.blob(logo, 'image/png')
    }

    this.transcript.push({ id: 'welcome', kind: 'welcome' })

    // `hermes -q …`: the launcher's query is the first prompt, sent literally once the first session is adopted.
    const query = process.env.HERMES_TUI_QUERY?.trim()

    if (query || this.#startupImage) {
      this.queue.push({ text: query || 'What do you see in this image?' })
    }

    this.#gw.on('event', (ev: AnyGatewayEvent) => this.#onGatewayEvent(ev))
    this.#gw.on('request', (req: ServerRequest) => this.#onRequest(req))
    this.#gw.on('exit', (code: null | number) => {
      this.transcript.notice(`The agent backend exited${code === null ? '' : ` (${code})`}.`, 'error')
      // The runtime session died with the process: prompts queue until the next gateway.ready reattaches.
      this.sid = null
      this.busy = null
      this.transcript.interrupt()
      this.changed()
    })
    this.#gw.drain()
    this.#render()
    this.#surface.focus(INPUT_ID)
    void this.#readInput()

    const code = await this.#done.promise
    await this.#tern.close()
    this.#gw.kill('exit')

    return code
  }

  // ── OverlayHost ────────────────────────────────────────────────────

  open(overlay: Overlay) {
    const same = this.overlays.find(o => o.key === overlay.key)

    if (same) {
      this.close(same)
    }

    this.overlays.push(overlay)
    this.#overlayIds.set(overlay, `layer.${overlay.key}:${++this.#overlaySerial}`)

    if (overlay.modal) {
      // The sheet owns the keys now: a list or reply for the composer would only land under it.
      this.#completion.dismiss()
    }

    this.changed()
  }

  close(overlay: Overlay) {
    // By identity: a stale callback of a replaced overlay must not close its same-key successor.
    const at = this.overlays.indexOf(overlay)

    if (at >= 0) {
      this.overlays.splice(at, 1)
      this.#overlayIds.delete(overlay)
      this.#approvalIds.delete(overlay.key)
      this.changed()
    }
  }

  changed() {
    if (this.#scheduled) {
      return
    }

    this.#scheduled = true
    setImmediate(() => {
      this.#scheduled = false
      this.#render()
    })
  }

  // ── Input ──────────────────────────────────────────────────────────

  async #readInput() {
    try {
      for await (const input of this.#tern) {
        if (input.type === 'key') {
          this.#onKey(input.key)
        } else {
          this.#onTernEvent(input.event)
        }

        this.changed()
      }
    } catch (error) {
      this.transcript.notice(`Input failed: ${error instanceof Error ? error.message : String(error)}`, 'error')
    }

    this.quit()
  }

  #onKey(key: Key) {
    const top = this.overlays.at(-1)

    if (key.ctrl && key.name === 'c') {
      return top?.key === 'settings' ? top.onKey(key) : this.#ctrlC()
    }

    if (top?.onKey(key)) {
      return
    }

    if (top?.modal) {
      return
    }

    if (this.#completion.onKey(key)) {
      return
    }

    if (key.name === 'escape') {
      if (this.busy) {
        this.#interrupt()
      }

      return
    }

    if (key.shift && key.name === 'tab') {
      return this.#cycleEffort()
    }

    if (key.alt && key.name === 'up' && this.queue.length) {
      return this.#dequeue()
    }

    if (key.ctrl && key.name === 'd' && !this.composer.text) {
      return this.quit()
    }

    const action = this.composer.key(key)

    if (action === 'submit') {
      this.#submit(this.composer.take())
    }
  }

  #onTernEvent(ev: TspEvent) {
    if (ev.ev === 'focus' && ev.id === INPUT_ID && !this.overlays.at(-1)?.modal) {
      this.#focus = INPUT_ID
      this.#surface.focus(INPUT_ID)
    }
  }

  #ctrlC() {
    if (this.composer.text) {
      this.composer.set('')

      return
    }

    if (this.busy) {
      return this.#interrupt()
    }

    const now = Date.now()

    if (now - this.#exitArmed < EXIT_ARM_MS) {
      return this.quit()
    }

    this.#exitArmed = now
    this.transcript.notice('Press Ctrl+C again to exit.')
  }

  quit(code = 0) {
    this.#done.resolve(code)
  }

  // ── Prompts and commands ───────────────────────────────────────────

  #submit(raw: string) {
    const text = raw.trim()

    if (!text) {
      return
    }

    if (text.startsWith('/')) {
      if (this.#historyUndo) {
        this.transcript.notice('Wait for the current rewind to finish before running slash commands.', 'warning')
        this.changed()

        return
      }

      void this.#slash(text)

      return
    }

    if (this.busy || !this.sid || this.#switches.pending || this.#historyUndo) {
      this.queue.push({ text })

      return
    }

    this.#send(text)
  }

  /** Sends `text` now; `queued` marks a drained queue entry (the gateway must queue it, never steer with it). */
  #send(text: string, { queued = false, display }: { queued?: boolean; display?: string } = {}) {
    // A session switch in flight: the prompt belongs to the session it adopts.
    if (this.busy || !this.sid || this.#switches.pending || this.#historyUndo) {
      this.queue.unshift({ text, display })

      return
    }

    const sid = this.sid
    const generation = this.#sessionGeneration
    const user = this.transcript.user(display ?? text)
    this.#startBusy('Working…')
    this.#gw
      .request<{ user_row_id?: number }>('prompt.submit', {
        session_id: sid,
        text,
        ...(queued ? { queued } : {})
      })
      .then(r => {
        if (
          typeof r?.user_row_id === 'number' &&
          this.sid === sid &&
          this.#sessionGeneration === generation
        ) {
          this.transcript.setUserRowId(user.id, r.user_row_id)
          this.changed()
        }
      })
      .catch((error: Error) => {
        if (this.sid !== sid || this.#sessionGeneration !== generation) {
          return
        }

        this.transcript.notice(error.message, 'error')
        this.busy = null
        this.changed()
      })
  }

  async #slash(text: string, aliasDepth = 0) {
    if (this.#historyUndo) {
      this.transcript.notice('Wait for the current rewind to finish before running slash commands.', 'warning')
      this.changed()

      return
    }

    const sid = this.sid
    const generation = this.#sessionGeneration
    const current = () => this.sid === sid && this.#sessionGeneration === generation
    const { name, arg } = parseSlashCommand(text)
    const local = localCommand(name)

    if (local) {
      try {
        const handled = await local.run(this, arg)

        if (handled !== false) {
          return this.changed()
        }
      } catch (error) {
        if (current()) {
          this.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
          this.changed()
        }

        return
      }
    }

    if (!current()) {
      return
    }

    if (aliasDepth > 8) {
      this.transcript.notice(`/${name}: too many command aliases`, 'error')
      this.changed()

      return
    }

    if (!sid) {
      return
    }

    const title = `/${name}${arg ? ` ${arg}` : ''}`
    const handle = (raw: unknown) => {
      if (!current()) {
        return
      }

      const dispatch = parseCommandDispatch(raw)

      if (!dispatch) {
        const result = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : null

        if (result && 'type' in result) {
          this.transcript.notice(`/${name}: invalid command dispatch response`, 'error')

          return
        }

        if (result && 'output' in result && typeof result.output === 'string' && result.output.trim()) {
          this.transcript.panel(title, result.output)
        }

        if (result && 'warning' in result && typeof result.warning === 'string' && result.warning.trim()) {
          this.transcript.notice(result.warning, 'warning')
        }

        return
      }

      switch (dispatch.type) {
        case 'exec':
        case 'plugin':
          if (dispatch.output?.trim()) {
            this.transcript.panel(title, dispatch.output)
          }

          return

        case 'alias':
          void this.#slash(`/${dispatch.target}${arg ? ` ${arg}` : ''}`, aliasDepth + 1)

          return

        case 'skill':
          if (!dispatch.message?.trim()) {
            this.transcript.notice(`/${dispatch.name}: skill payload missing message`, 'error')

            return
          }

          this.#send(dispatch.message, {
            display: dispatch.display?.trim() || `/${dispatch.name}${arg ? ` ${arg}` : ''}`
          })

          return

        case 'prefill':
        case 'send':
          if (dispatch.notice?.trim()) {
            this.transcript.notice(dispatch.notice, 'info')
          }

          if (dispatch.type === 'prefill') {
            this.composer.set(dispatch.message)
            this.changed()

            return
          }

          if (!dispatch.message.trim()) {
            this.transcript.notice(`/${name}: empty dispatch message`, 'error')

            return
          }

          this.#send(dispatch.message, {
            ...(dispatch.display?.trim() ? { display: dispatch.display.trim() } : {})
          })
      }
    }

    try {
      const result = await this.#gw.request<unknown>('slash.exec', {
        command: text.slice(1),
        session_id: sid
      })

      if (current()) {
        handle(result)
      }
    } catch (error) {
      if (!current()) {
        return
      }


      if (!shouldFallbackToDispatch(error)) {
        if (current()) {
          this.transcript.notice(describeSlashExecError(name, error), 'error')
        }
      } else {
        try {
          const result = await this.#gw.request<unknown>('command.dispatch', { arg, name, session_id: sid })

          if (current()) {
            handle(result)
          }
        } catch (dispatchError) {
          if (current()) {
            this.transcript.notice(
              dispatchError instanceof Error ? dispatchError.message : String(dispatchError),
              'error'
            )
          }
        }
      }
    }

    if (current()) {
      this.changed()
    }
  }

  #interrupt() {
    if (!this.sid) {
      return
    }

    if (this.busy) {
      this.busy.label = 'Stopping…'
    }

    this.#gw.request('session.interrupt', { session_id: this.sid }).catch(() => undefined)
    this.changed()
  }

  #startBusy(label: string) {
    this.busy = { label, since: {}, startedAt: Date.now() }
    this.changed()
  }

  // ── Sessions ───────────────────────────────────────────────────────

  /** The first session: HERMES_TUI_RESUME's, else a new one; then the launcher's startup image, if any. */
  async #bootstrap() {
    const resume = process.env.HERMES_TUI_RESUME?.trim()

    try {
      await (resume ? this.resume(resume) : this.newSession())
    } catch (error) {
      this.transcript.notice(
        `Could not start a session: ${error instanceof Error ? error.message : String(error)}`,
        'error'
      )
      this.changed()

      return
    }

    if (this.sid && this.#startupImage) {
      await this.#attachStartupImage(this.sid)
    }
  }

  /** `hermes -q … --image …`: attaches the image to the first session, then lets the startup query go. */
  async #attachStartupImage(sid: string) {
    const path = this.#startupImage

    try {
      await this.#gw.request('image.attach', { path, session_id: sid })
    } catch (error) {
      this.transcript.notice(
        `Could not attach ${path}: ${error instanceof Error ? error.message : String(error)}`,
        'warning'
      )
    }

    this.#startupImage = ''
    this.#drainQueue()
    this.changed()
  }

  /** After a reconnect: resumes the shown session in the new backend (its runtime id died with the old one). */
  async #reattach(id: string) {
    const resumed = this.#resume(id)
    const generation = this.#sessionGeneration

    try {
      if (await resumed && this.#sessionGeneration === generation) {
        this.transcript.notice('Reconnected to the agent backend.')
      }
    } catch (error) {
      if (this.#sessionGeneration !== generation) {
        return
      }

      this.transcript.notice(
        `Could not reattach the session: ${error instanceof Error ? error.message : String(error)}`,
        'error'
      )
    }

    this.changed()
  }

  /** Closes the open session and starts a fresh one with an empty transcript. */
  async newSession() {
    const token = this.#beginSwitch()
    let adopted = false

    try {
      const setup = await this.#gw.request<{ provider_configured?: boolean | null }>('setup.status', {})

      if (!this.#switches.current(token)) {
        return
      }

      if (setup?.provider_configured === false) {
        this.transcript.notice('No model provider is configured. Run `hermes setup`, then start again.', 'warning')

        return
      }

      if (this.sid) {
        await this.#gw.request('session.close', { session_id: this.sid }).catch(() => undefined)
      }

      const cwd = process.env.HERMES_TUI_CWD?.trim()

      const r = await this.#gw.request<CreateResult>('session.create', {
        cols: this.#tern.caps.cols,
        ...(cwd ? { cwd } : {})
      })

      if (!this.#switches.current(token)) {
        // A later switch won; nothing will ever show this session.
        this.#gw.request('session.close', { session_id: r.session_id }).catch(() => undefined)

        return
      }

      this.transcript.clear()
      this.transcript.push({ id: this.transcript.id('w'), kind: 'welcome' })
      this.#adopt(r)
      adopted = true
    } finally {
      this.#settle(token, adopted)
    }
  }

  /** Resumes stored session `id`: its history replaces the transcript, and the session it leaves is closed. */
  async resume(id: string): Promise<boolean> {
    if (this.busy) {
      this.transcript.notice('Wait for the current turn to finish (or press Esc) before switching sessions.', 'warning')
      this.changed()

      return false
    }

    const previous = this.sid
    const r = await this.#resume(id)

    if (r && previous && previous !== r.session_id) {
      this.#gw.request('session.close', { session_id: previous }).catch(() => undefined)
    }

    return Boolean(r)
  }

  /** Resumes and adopts stored session `id`; undefined when a later switch superseded this one. */
  async #resume(id: string): Promise<CreateResult | undefined> {
    const token = this.#beginSwitch()
    let adopted = false

    try {
      const r = await this.#gw.request<CreateResult>('session.resume', { cols: this.#tern.caps.cols, session_id: id })

      if (!this.#switches.current(token)) {
        return undefined
      }

      this.transcript.clear()
      this.transcript.push({ id: this.transcript.id('w'), kind: 'welcome' })
      this.#adopt(r)
      adopted = true

      return r
    } finally {
      this.#settle(token, adopted)
    }
  }

  #adopt(r: CreateResult) {
    this.sid = r.session_id
    this.storedSid = r.info?.stored_session_id || r.stored_session_id || null
    writeActiveSessionFile(this.storedSid ?? r.session_id)
    this.info = r.info ?? this.info
    this.usage = r.info?.usage ?? null
    // A resumed session may be mid-turn: Esc stops it and new prompts queue behind it.
    this.busy = busyFrom(r)
    this.transcript.usageBase(r.info?.usage ?? undefined)

    if (r.messages?.length) {
      this.transcript.load(r.messages)
    }

    if (r.inflight) {
      this.transcript.inflight(r.inflight, this.busy?.startedAt)
    }

    this.changed()
  }

  /** Starts a new/resume/reattach generation before any asynchronous switch work begins. */
  #beginSwitch() {
    const token = this.#switches.begin()
    this.#sessionGeneration = token
    this.#historyUndo = null

    return token
  }
  /** Ends a switch; failed destination prompts return to the composer, never to the previous session. */
  #settle(token: number, adopted: boolean) {
    this.#switches.end(token)

    if (this.#switches.pending || this.#sessionGeneration !== token) {
      return
    }

    if (!adopted && this.queue.length) {
      const restored = this.queue.splice(0).map(prompt => prompt.text).join('\n\n')

      this.composer.set(this.composer.text ? `${restored}\n\n${this.composer.text}` : restored)
      this.transcript.notice('The session switch failed. Queued prompts are back in the composer; nothing was sent.', 'warning')
    }

    const traffic = this.#switchTraffic

    this.#switchTraffic = []

    for (const buffered of traffic) {
      if (this.#switches.pending || this.#sessionGeneration !== token || buffered.generation !== token) {
        if ('request' in buffered) {
          buffered.request.fail(-32002, 'A newer session switch superseded this request')
        }

        continue
      }

      if ('event' in buffered) {
        if (buffered.event.session_id === this.sid) {
          this.#onGatewayEvent(buffered.event)
        }
      } else {
        this.#onRequest(buffered.request)
      }
    }

    this.#drainQueue()
    this.changed()
  }

  // ── Gateway ────────────────────────────────────────────────────────

  #onGatewayEvent(ev: AnyGatewayEvent) {
    if (ev.type === 'request.cancel') {
      if (ev.payload?.id === undefined || ev.payload.id === null) {
        return
      }

      const id = String(ev.payload.id)
      const before = this.#switchTraffic.length
      this.#switchTraffic = this.#switchTraffic.filter(buffered =>
        !('request' in buffered &&
          String(buffered.request.id) === id &&
          buffered.request.params.session_id === ev.session_id)
      )
      const held = before !== this.#switchTraffic.length
      const shown = ownsEvent(this.sid, ev) && this.overlays.some(overlay => overlay.key === `prompt:${id}`)

      if (!held && !shown) {
        this.#cancelledRequestIds.add(cancellationKey(this.#sessionGeneration, ev.session_id, id))
      }

      if (shown) {
        this.#dropPrompts(key => key === `prompt:${id}`)
      }

      return
    }

    if (ev.type === 'approval.cancelled') {
      for (const id of ev.payload?.request_ids ?? []) {
        const before = this.#switchTraffic.length
        this.#switchTraffic = this.#switchTraffic.filter(buffered =>
          !('request' in buffered &&
            buffered.request.method === 'approval' &&
            buffered.request.params.request_id === id &&
            buffered.request.params.session_id === ev.session_id)
        )
        const held = before !== this.#switchTraffic.length
        const shown = ownsEvent(this.sid, ev) &&
          this.overlays.some(overlay => this.#approvalIds.get(overlay.key) === id)

        if (!held && !shown) {
          this.#cancelledApprovalIds.add(cancellationKey(this.#sessionGeneration, ev.session_id, id))
        }

        if (shown) {
          this.#dropPrompts(key => this.#approvalIds.get(key) === id)
        }
      }

      return
    }

    const historyUndo = this.#historyUndo

    if (
      historyUndo?.phase === 'pending' &&
      historyUndo.sid === this.sid &&
      historyUndo.generation === this.#sessionGeneration &&
      ev.session_id === historyUndo.sid
    ) {
      historyUndo.events.push(ev)

      return
    }

    if (this.#switches.pending && ev.session_id) {
      this.#switchTraffic.push({ event: ev, generation: this.#sessionGeneration })

      return
    }

    // Another session's traffic (one being closed, or left by a switch) never reaches this transcript.
    if (!ownsEvent(this.sid, ev)) {
      return
    }

    const t = this.transcript

    switch (ev.type) {
      case 'gateway.ready':
        this.#applySkin(ev.payload?.skin)
        // A reconnect's ready reattaches the shown session; only a sessionless app bootstraps.
        void (this.storedSid ? this.#reattach(this.storedSid) : this.#bootstrap())

        break

      case 'skin.changed':
        this.#applySkin(ev.payload)

        break

      case 'session.info':
        this.info = ev.payload ?? this.info
        this.usage = ev.payload?.usage ?? this.usage

        break

      case 'session.usage':
        this.usage = ev.payload?.usage ?? this.usage

        break

      case 'session.title':
        if (ev.payload?.title) {
          // eslint-disable-next-line no-control-regex -- a title must not end the OSC early
          process.stdout.write(`\x1b]2;${ev.payload.title.replace(/[\x00-\x1f]/g, ' ')}\x07`)
        }

        break

      case 'message.start':
        if (!this.busy) {
          this.#startBusy('Working…')
        }

        t.start()

        break

      case 'message.delta':
        t.text(ev.payload?.text ?? '')
        this.#label('Writing…')

        break

      case 'reasoning.delta':
        t.reasoning(ev.payload?.text ?? '')
        this.#label('Thinking…')

        break

      case 'reasoning.available':
        t.reasoningBlock(ev.payload?.text ?? '')

        break

      case 'thinking.delta':
        this.#label(kaomojiLabel(ev.payload?.text ?? ''))

        break

      case 'message.interim':
        t.interim(ev.payload?.text ?? '', { alreadyStreamed: Boolean(ev.payload?.already_streamed) })

        break

      case 'tool.generating':
        this.#label(`Preparing ${ev.payload?.name ?? 'a tool'}…`)

        break

      case 'tool.start':
        if (ev.payload) {
          t.toolStart(ev.payload)
          this.#label(`Running ${ev.payload.name}…`)
        }

        break

      case 'tool.complete':
        if (ev.payload) {
          t.toolComplete(ev.payload)
        }

        break

      case 'todo.updated':
        t.todos(ev.payload?.todos ?? [])

        break

      case 'subagent.spawn_requested':

      case 'subagent.start':

      case 'subagent.thinking':

      case 'subagent.tool':

      case 'subagent.progress':

      case 'subagent.complete':
        if (ev.payload) {
          t.subagent(ev.type, ev.payload)
        }

        break

      case 'message.complete':
        t.complete(ev.payload ?? {})
        this.busy = null
        this.#drainQueue()

        break

      case 'status.update':
        if (this.busy && ev.payload?.text && ev.payload.kind === 'status') {
          this.#label(ev.payload.text)
        }

        break

      case 'notice':
        t.notice(ev.payload?.message ?? '')

        break

      case 'error':
        t.notice(ev.payload?.message ?? 'error', 'error')

        break

      case 'gateway.start_timeout':
        t.notice('The agent backend did not start in time.', 'error')

        break

      case 'gateway.protocol_error':
        t.notice(`Protocol error from the agent backend: ${ev.payload?.preview ?? ''}`, 'error')

        break

      case 'background.complete':

      case 'btw.complete':
        if (ev.payload && 'text' in ev.payload && typeof ev.payload.text === 'string' && ev.payload.text.trim()) {
          t.panel(ev.type === 'btw.complete' ? '/btw' : 'Background task', ev.payload.text)
        }

        break


      default:
        return
    }

    this.changed()
  }

  #onRequest(req: ServerRequest) {
    const sessionId = typeof req.params.session_id === 'string' ? req.params.session_id : undefined

    if (this.#cancelledRequestIds.delete(cancellationKey(this.#sessionGeneration, sessionId, String(req.id)))) {
      return
    }

    if (
      req.method === 'approval' &&
      typeof req.params.request_id === 'string' &&
      this.#cancelledApprovalIds.delete(
        cancellationKey(this.#sessionGeneration, sessionId, req.params.request_id)
      )
    ) {
      return
    }
    const route = this.#switches.pending ? 'hold' : this.#switches.route(this.sid, req.params.session_id)

    if (route === 'hold') {
      this.#switchTraffic.push({ generation: this.#sessionGeneration, request: req })

      return
    }

    // Another session's prompt: it settles when that session closes.
    if (route === 'drop') {
      return
    }

    const overlay = promptOverlay(this, req)

    if (!overlay) {
      req.fail(-32601, `${req.method} is not supported by the Tern frontend`)

      return
    }

    this.open(overlay)

    if (req.method === 'approval' && typeof req.params.request_id === 'string') {
      this.#approvalIds.set(overlay.key, req.params.request_id)
    }
  }

  /** Closes the prompt overlays whose key `cancelled` picks (the gateway withdrew their requests). */
  #dropPrompts(cancelled: (key: string) => boolean) {
    for (const o of [...this.overlays]) {
      if (o.key.startsWith('prompt:') && cancelled(o.key)) {
        this.close(o)
      }
    }
  }

  #applySkin(skin: SkinPayload | null | undefined) {
    if (skin) {
      this.#surface.palette(paletteOf(skin))
    }
  }

  #label(label: string) {
    if (this.busy && label) {
      this.busy.label = label
    }
  }

  /** The single live effort owner, including a lazy session before its first model turn. */
  setReasoning(value: string, scope?: 'session' | 'global', sid = this.sid): Promise<ConfigSetResult | undefined> {
    const generation = this.#sessionGeneration

    const write = async () => {
      if (!sid || this.sid !== sid || this.#sessionGeneration !== generation) {
        return undefined
      }

      const result = await this.#gw.request<ConfigSetResult>('config.set', {
        key: 'reasoning',
        session_id: sid,
        value,
        ...(scope ? { scope } : {})
      })

      if (this.sid !== sid || this.#sessionGeneration !== generation) {
        return undefined
      }

      const current = await this.#gw.request<ConfigGetResult>('config.get', { key: 'reasoning', session_id: sid })

      if (this.sid === sid && this.#sessionGeneration === generation && typeof current.value === 'string') {
        this.info = { ...this.info, reasoning_effort: current.value }
        this.changed()

        return result
      }
      if (this.sid === sid && this.#sessionGeneration === generation) {
        throw new Error('The backend did not confirm the live reasoning effort.')
      }


      return undefined
    }

    const result = this.#effortWrites.then(write, write)
    this.#effortWrites = result.catch(() => undefined)

    return result
  }

  /** Steps the session's reasoning effort. The native glyph changes only after readback. */
  #cycleEffort() {
    const sid = this.sid
    const generation = this.#sessionGeneration

    if (!sid) {
      return
    }

    const current = this.#effortRequested?.sid === sid && this.#effortRequested.generation === generation
      ? this.#effortRequested.value : this.info?.reasoning_effort ?? ''
    const at = EFFORTS.indexOf(current)
    const request = { generation, sid, value: EFFORTS[at < 0 ? EFFORTS.indexOf('medium') : (at + 1) % EFFORTS.length]! }
    this.#effortRequested = request
    this.setReasoning(request.value, 'session', sid).catch((error: Error) => {
      if (this.sid === sid && this.#sessionGeneration === generation) {
        this.transcript.notice(error.message, 'error')
        this.changed()
      }
    }).finally(() => {
      if (this.#effortRequested === request) {
        this.#effortRequested = null
      }
    })
  }

  /** Alt+Up / the queue's Edit: the oldest queued prompt back into an empty composer. */
  #dequeue() {
    const next = this.queue.shift()

    if (next !== undefined) {
      this.composer.set(this.composer.text ? `${next.text}\n${this.composer.text}` : next.text)
      this.changed()
    }
  }

  /** Sends the oldest queued prompt once the session is adopted and idle (no turn, switch or startup image pending). */
  #drainQueue() {
    if (this.busy || !this.sid || this.#switches.pending || this.#startupImage || this.#historyUndo) {
      return
    }

    const next = this.queue.shift()

    if (next) {
      this.#send(next.text, { display: next.display, queued: true })
    }
  }

  // ── View ───────────────────────────────────────────────────────────

  #render() {
    if (this.#surface.closed) {
      return
    }

    const now = Date.now()
    const info = this.info
    const usage = this.usage
    const backend = info?.version && info.version !== 'unknown' ? `v${info.version}` : ''

    const cx = {
      copy: (text: string) => copyToClipboard(text),
      now,
      rewind: (rowId: number) => {
        const sid = this.sid

        if (!sid) {
          return
        }

        if (this.busy || this.#switches.pending || this.#historyUndo) {
          const message = this.#historyUndo
            ? 'A rewind is already in progress.'
            : 'Cannot rewind while a turn or session switch is active.'
          this.transcript.notice(message, 'warning')
          this.changed()

          return
        }

        const generation = this.#sessionGeneration
        const operation: HistoryUndo = { events: [], generation, phase: 'pending', sid }
        const current = () =>
          this.#historyUndo === operation && this.sid === sid && this.#sessionGeneration === generation
        this.#historyUndo = operation

        void (async () => {
          try {
            const result = await this.#gw.request<{ count: number; messages: TranscriptMessage[]; removed: number }>(
              'session.undo',
              { row_id: rowId, session_id: sid }
            )

            if (!current()) {
              return
            }

            if (!Array.isArray(result.messages)) {
              throw new Error('The gateway did not return the rewound transcript.')
            }

            this.transcript.load(result.messages)
          } catch (error) {
            if (current()) {
              this.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
            }
          } finally {
            if (this.#historyUndo === operation) {
              if (current()) {
                operation.phase = 'replaying'

                for (const event of operation.events) {
                  this.#onGatewayEvent(event)
                }
              }

              this.#historyUndo = null
              this.#drainQueue()
              this.changed()
            }
          }
        })()
      },
      welcome: { ...this.#welcome, version: this.#welcome.version || backend }
    }

    const used = usage?.context_used ?? 0
    const max = usage?.context_max ?? 0
    const modal = this.overlays.at(-1)?.modal === true

    // Every composer change (keys, native edits and undo, submits, queue edits) ends in a render: refresh here.
    if (!modal) {
      this.#completion.update(this.composer)
    }

    this.#layerOwners.clear()
    this.#surface.render({
      dock: dockNodes({
        branch: info?.branch ?? '',
        busy: this.busy ?? undefined,
        composer: this.composer,
        context: max > 0 ? { max, used } : undefined,
        cost: usage?.cost_usd ?? undefined,
        cwd: info?.cwd ? shortPath(info.cwd) : '',
        effort: info?.reasoning_effort ?? '',
        ghost: modal ? '' : this.#completion.ghost,
        inputId: INPUT_ID,
        model: info?.model ?? '',
        now,
        onContext: () => void this.#slash('/usage'),
        onEdit: ev => {
          this.composer.edit(ev)
          this.changed()
        },
        onEffort: () => this.#cycleEffort(),
        onInterrupt: () => this.#interrupt(),
        onSettings: () => openSettings(this),
        onModel: () => openModelPicker(this),
        onQueueEdit: () => this.#dequeue(),
        onSend: ev => {
          this.#submit(this.composer.take(ev.text))
          this.changed()
        },
        onSubmit: () => {
          this.#submit(this.composer.take())
          this.changed()
        },
        onUndo: () => {
          this.composer.undo()
          this.changed()
        },
        placeholder: 'Ask Hermes — / commands · @ files',
        queued: this.queue,
        ready: this.sid !== null
      }),
      layer: [
        ...this.overlays.map(o => {
          const id = this.#overlayIds.get(o)!
          this.#layerOwners.set(id, o)

          return o.node(id)
        }),
        ...(modal ? [] : this.#completion.nodes(INPUT_ID))
      ],
      main: this.transcript.entries.map(e => entryNode(e, `main.${e.id}`, cx))
    })

    // The top overlay's field holds the caret; a modal sheet without one takes it from the composer.
    const top = this.overlays.at(-1)
    const focus = top?.focus ? top.focus(this.#overlayIds.get(top)!) : top?.modal ? null : INPUT_ID

    if (focus !== this.#focus) {
      this.#focus = focus
      this.#surface.focus(focus)
    }
  }
}

/** `( •_•)>⌐■-■ cogitating...` → `Cogitating…`: hermes's kawaii status without the face. */
function kaomojiLabel(text: string): string {
  const word = text.match(/([A-Za-z][A-Za-z ]*[A-Za-z])\.{2,}\s*$/)?.[1]

  return word ? `${word.charAt(0).toUpperCase()}${word.slice(1)}…` : ''
}

function shortPath(path: string): string {
  const home = process.env.HOME

  return home && path.startsWith(home) ? `~${path.slice(home.length)}` : path
}

/** Copies through OSC 52, which Tern (and most terminals) honor. */
function copyToClipboard(text: string) {
  process.stdout.write(`\x1b]52;c;${Buffer.from(text).toString('base64')}\x07`)
}
