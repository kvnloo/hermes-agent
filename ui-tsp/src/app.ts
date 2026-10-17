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
import type { Key, Session, Surface, TspEvent } from '@stencil-hq/tern'
import type { GatewayClient } from '@tui/gatewayClient.js'
import type { AnyGatewayEvent } from '@tui/gatewayTypes.js'
import { writeActiveSessionFile } from '@tui/lib/activeSessionFile.js'

import logo from '../assets/logo.png'

import { type ActionContext, actionForKey, APP_ACTIONS, matchesAction } from './actions.js'
import { Dispatches } from './attention.js'
import { localCommand } from './commands.js'
import { Composer } from './composer.js'
import { type Busy, busyFrom, ownsEvent, Switches } from './flow.js'
import { OrbActivity, ThinkingOrb } from './orb.js'
import type { Overlay, OverlayHost } from './overlay.js'
import { Completion } from './overlays/completion.js'
import { openModelPicker } from './overlays/models.js'
import { promptOverlay } from './overlays/prompts.js'
import { openSettings } from './overlays/settings.js'
import { programPaletteOf } from './palette.js'
import { SPLASH_ROLE } from './splash/index.js'
import { LaunchSplash, pickSplashDesign, splashInsets, splashSetting, splashTickMs } from './splash/launch.js'
import { TodoHud } from './todo-hud.js'
import { Transcript } from './transcript.js'
import { dockNodes } from './view/dock.js'
import { toolFoldState } from './view/tools.js'
import { entryNode } from './view/transcript.js'
import { randomTip, type WelcomeContext } from './view/welcome.js'

/** The composer's `editor` node id (dock → composer → line → input). */
export const INPUT_ID = 'dock.composer.line.input'

const EXIT_ARM_MS = 1500
/** What Shift+Tab / the effort chip cycle through (hermes's `none` turns reasoning off). */
const EFFORTS = ['none', 'low', 'medium', 'high', 'xhigh']

/** session.create's result, or session.resume's with the state of a turn it may be in. */
interface CreateResult extends Partial<
  Pick<SessionResumeResult, 'inflight' | 'running' | 'status' | 'turn_started_at'>
> {
  session_id: string
  stored_session_id?: string | null
  info?: SessionLiveInfo
  messages?: TranscriptMessage[]
}

/** Runs the Tern frontend until the user quits; resolves the exit code. */
export class App implements OverlayHost {
  readonly transcript = new Transcript()
  readonly dispatches = new Dispatches()
  readonly todoHud = new TodoHud()
  readonly composer = new Composer()
  readonly overlays: Overlay[] = []
  /** Presentation-only collapse overrides, scoped by transcript turn and tool identity. */
  readonly #folds = new Map<string, boolean>()
  readonly #foldRevs = new Map<string, number>()
  sid: string | null = null
  /** The stored (database) id of the open session: what `session.list` rows are keyed by. */
  storedSid: string | null = null
  info: SessionLiveInfo | null = null
  usage: Usage | null = null
  busy: Busy | null = null
  queue: string[] = []
  readonly #tern: Session
  readonly #gw: GatewayClient
  readonly #completion: Completion
  readonly #welcome: WelcomeContext
  #surface!: Surface
  /** Owners of native handlers in the last rendered layer, not the current stack. */
  readonly #layerOwners = new Map<string, Overlay>()
  readonly #overlayIds = new WeakMap<Overlay, string>()
  #overlaySerial = 0
  readonly #activity = new OrbActivity()
  #orb: ThinkingOrb | undefined
  #scheduled = false
  #dispatchTimer: ReturnType<typeof setTimeout> | undefined
  #dispatchDeadline: number | null = null
  #visible = true
  #lastSubmitted: { sid: string; text: string; replayable: boolean } | null = null
  #retry: { sid: string; text: string; turnId: string } | null = null
  #startupAttachmentPending = false
  /** The field holding Tern's caret, as last sent. */
  #focus: string | null = INPUT_ID
  #exitArmed = 0
  #done = Promise.withResolvers<number>()
  readonly #switches = new Switches()
  /** Server requests for another session, kept while a switch is in flight. */
  #heldRequests: ServerRequest[] = []
  /** Open approval prompts' overlay keys → their approval-queue `request_id` (what approval.cancelled names). */
  readonly #approvalIds = new Map<string, string>()
  /** The launcher's startup image until it is attached to the first session (the queue waits for it). */
  #startupImage = process.env.HERMES_TUI_IMAGE?.trim() ?? ''
  #effortWrites: Promise<unknown> = Promise.resolve()
  #reasoningToggles: Promise<unknown> = Promise.resolve()
  #effortRequested: { sid: string; value: string } | null = null
  /** The launch splash while it covers the session chrome (it takes the keys until it leaves). */
  #splash: LaunchSplash | undefined

  constructor(tern: Session, gw: GatewayClient, version: string) {
    this.#tern = tern
    this.#gw = gw
    this.#completion = new Completion(this, gw, () => this.sid)
    this.#welcome = {
      tip: randomTip(process.env.HERMES_PYTHON_SRC_ROOT ?? ''),
      version: version && version !== 'unknown' ? `v${version}` : ''
    }
  }

  /** The gateway, for overlays that issue their own RPCs. */
  get gw(): GatewayClient {
    return this.#gw
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
      this.#orb = new ThinkingOrb(this.#tern, this.#surface)
    }

    this.transcript.push({ id: 'welcome', kind: 'welcome' })

    // `hermes -q …`: the launcher's query is the first prompt, sent literally once the first session is adopted.
    const query = process.env.HERMES_TUI_QUERY?.trim()

    if (query || this.#startupImage) {
      this.queue.push(query || 'What do you see in this image?')
    }

    this.#startSplash()
    this.#gw.on('event', (ev: AnyGatewayEvent) => this.#onGatewayEvent(ev))
    this.#gw.on('request', (req: ServerRequest) => this.#onRequest(req))
    this.#gw.on('exit', (code: null | number) => {
      this.transcript.notice(`The agent backend exited${code === null ? '' : ` (${code})`}.`, 'error')
      // The runtime session died with the process: prompts queue until the next gateway.ready reattaches.
      this.sid = null
      this.todoHud.adopt(null)
      this.busy = null
      this.transcript.interrupt()
      this.dispatches.reset()
      this.#lastSubmitted = null
      this.#retry = null
      // Whatever went wrong is in the transcript: let it be seen.
      this.#splash?.ready()
      this.#activity.event({ type: 'error' } as AnyGatewayEvent)
      this.changed()
    })
    this.#gw.drain()
    this.#render()
    this.#surface.focus(INPUT_ID)
    void this.#readInput()

    const code = await this.#done.promise
    this.#orb?.close()
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
      // A modal needs the pane and its first key, not the splash's exit animation.
      this.#splash?.dismiss()
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
    // Any key skips the launch splash, and is spent doing so.
    if (this.#splash?.active) {
      return this.#splash.skip()
    }

    const top = this.overlays.at(-1)

    // Ctrl+C retains its pre-overlay priority, except Settings owns cancellation.
    const clear = APP_ACTIONS.find(action => action.id === 'app.clear')!

    if (matchesAction(clear, key)) {
      return top?.key === 'settings' ? top.onKey(key) : clear.run(this)
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

    const ctx: ActionContext = {
      composerEmpty: !this.composer.text,
      busy: Boolean(this.busy),
      queued: this.queue.length > 0,
      overlayOpen: this.overlays.length > 0,
      completionOpen: this.#completion.open
    }

    const shortcut = actionForKey(key, ctx)

    if (shortcut) {
      return shortcut.run(this)
    }

    // Unbound Alt letters are commands, never literal typing. Keep readline's
    // Alt+B/F/D editing behavior by forwarding the key without printable text.
    const action = this.composer.key(key.alt && /^[a-z]$/i.test(key.name) ? { ...key, text: undefined } : key)

    if (action === 'submit') {
      this.#submit(this.composer.take())
    }
  }

  /** Copy the draft literally, without submitting it or disturbing the caret. */
  copyPrompt() {
    try {
      copyToClipboard(this.composer.text)
      // OSC52 has no acknowledgement; don't claim the terminal accepted it.
      this.transcript.notice('Composer text sent to the terminal clipboard (OSC 52).')
    } catch {
      this.transcript.notice('Could not copy the composer text to the clipboard.', 'warning')
    }

    this.changed()
  }

  /** Use Hermes's existing display command, not an independent UI preference.
   * Display show/hide is profile-scoped in the gateway, unlike effort levels.
   * Serialize read→toggle so rapid repeats use canonical backend state.
   */
  toggleReasoning() {
    const sid = this.sid

    const toggle = async () => {
      if (!sid || this.sid !== sid) {
        return
      }

      const current = await this.#gw.request<ConfigGetResult>('config.get', { key: 'reasoning', session_id: sid })

      if (this.sid === sid) {
        await this.slash(`/reasoning ${current.display === 'hide' ? 'show' : 'hide'}`)
      }
    }

    this.#reasoningToggles = this.#reasoningToggles.then(toggle).catch((error: Error) => {
      if (this.sid === sid) {
        this.transcript.notice(error.message, 'error')
        this.changed()
      }
    })
  }

  /** Toggle the newest foldable tool without altering Hermes tool results. */
  toggleRecentTool(): void {
    for (let i = this.transcript.entries.length - 1; i >= 0; i--) {
      const entry = this.transcript.entries[i]

      if (entry?.kind !== 'turn') {
        continue
      }

      for (let j = entry.blocks.length - 1; j >= 0; j--) {
        const block = entry.blocks[j]

        if (block?.kind !== 'tool') {
          continue
        }

        const fold = toolFoldState(block.call)

        if (!fold.collapsible) {
          continue
        }

        const key = entry.id + ':' + block.call.id
        this.#folds.set(key, !(this.#folds.get(key) ?? fold.collapsed))
        this.#foldRevs.set(entry.id, (this.#foldRevs.get(entry.id) ?? 0) + 1)
        this.changed()

        return
      }
    }
  }

  #onTernEvent(ev: TspEvent) {
    if (ev.ev === 'gone' && ev.ids.includes(this.#surface.id)) {
      // Rendering short-circuits after gone: dispose now, not on another animation tick.
      this.#orb?.close()
    }

    if (ev.ev === 'toggle' && ev.sf === 'hermes' && ev.key) {
      // Tern owns mouse folding. Mirror only the clicked tool's presentation
      // state, so the subsequent Ctrl+O reverses what the person actually saw.
      for (const entry of this.transcript.entries) {
        if (entry.kind !== 'turn' || !ev.id.startsWith('main.' + entry.id + '.')) {
          continue
        }

        const match = entry.blocks.some(b => b.kind === 'tool' && b.call.id === ev.key)

        if (match) {
          this.#folds.set(entry.id + ':' + ev.key, ev.collapsed)
          this.#foldRevs.set(entry.id, (this.#foldRevs.get(entry.id) ?? 0) + 1)

          break
        }
      }
    }

    if (
      (ev.ev === 'visible' || ev.ev === 'resize') &&
      (!ev.sf || ev.sf === this.#surface.id) &&
      ev.visible !== undefined
    ) {
      // The orb and held completion notices share the same pane visibility.
      this.#visible = ev.visible
      this.#orb?.environment({ visible: ev.visible })

      if (ev.visible) {
        this.dispatches.resume()
      }
    }

    if (ev.ev === 'theme') {
      this.#orb?.environment({ dark: ev.dark })
    }

    if (ev.ev === 'motion') {
      this.#orb?.environment({ reduce: ev.reduce })
    }

    if (ev.ev === 'focus' && ev.id === INPUT_ID && !this.overlays.at(-1)?.modal) {
      this.#focus = INPUT_ID
      this.#surface.focus(INPUT_ID)
    }
  }

  ctrlC() {
    if (this.composer.text) {
      this.composer.set('')

      return
    }

    if (this.busy) {
      return this.interrupt()
    }

    const now = Date.now()

    if (now - this.#exitArmed < EXIT_ARM_MS) {
      return this.quit()
    }

    this.#exitArmed = now
    this.transcript.notice('Press Ctrl+C again to exit.')
  }

  quit(code = 0) {
    if (this.#dispatchTimer) {
      clearTimeout(this.#dispatchTimer)
      this.#dispatchTimer = undefined
      this.#dispatchDeadline = null
    }

    this.#done.resolve(code)
  }

  // ── Prompts and commands ───────────────────────────────────────────

  #submit(raw: string) {
    const text = raw.trim()

    if (!text) {
      if (this.#retry) {
        this.retryFailed(this.#retry.turnId)
      }

      return
    }

    if (text.startsWith('/')) {
      void this.slash(text)

      return
    }

    if (this.busy || !this.sid || this.#switches.pending) {
      this.queue.push(text)

      return
    }

    this.#send(text)
  }

  /** Sends `text` now; `queued` marks a drained queue entry (the gateway must queue it, never steer with it). */
  #send(text: string, { queued = false }: { queued?: boolean } = {}) {
    // A session switch in flight: the prompt belongs to the session it adopts.
    if (!this.sid || this.#switches.pending) {
      this.queue.unshift(text)

      return
    }

    this.#retry = null
    const submitted = { sid: this.sid, text, replayable: !this.#startupAttachmentPending }
    this.#lastSubmitted = submitted
    this.#startupAttachmentPending = false
    this.transcript.user(text)
    this.#startBusy('Working…')
    this.#gw
      .request('prompt.submit', { session_id: this.sid, text, ...(queued ? { queued } : {}) })
      .catch((error: Error) => {
        if (this.#lastSubmitted !== submitted || this.sid !== submitted.sid) {
          return
        }

        this.transcript.notice(error.message, 'error')
        this.#lastSubmitted = null
        this.busy = null
        this.#activity.event({ type: 'error' } as AnyGatewayEvent)
        this.changed()
      })
  }

  /** Retry only the exact latest error, on the same idle session, never a stale or image-backed request. */
  canRetry(turnId: string): boolean {
    const candidate = this.#retry

    if (!candidate || candidate.turnId !== turnId || !this.sid || candidate.sid !== this.sid ||
        this.busy || this.#switches.pending || this.queue.length) {
      return false
    }

    const latest = this.transcript.entries.findLast(e => e.kind === 'turn')

    return latest?.kind === 'turn' && latest.id === turnId && latest.retryable === true && latest.status === 'error'
  }

  retryFailed(turnId: string) {
    if (!this.canRetry(turnId)) {
      return
    }

    const candidate = this.#retry!
    this.#retry = null
    this.#send(candidate.text)
  }

  async slash(text: string) {
    const [name = '', ...rest] = text.slice(1).split(/\s+/)
    const arg = rest.join(' ')
    const local = localCommand(name)

    if (local) {
      try {
        const handled = await local.run(this, arg)

        if (handled !== false) {
          return this.changed()
        }
      } catch (error) {
        this.transcript.notice(error instanceof Error ? error.message : String(error), 'error')

        return this.changed()
      }
    }

    if (!this.sid) {
      return
    }

    try {
      const r = await this.#gw.request<{ output?: string; warning?: string; type?: string; message?: string }>(
        'slash.exec',
        {
          command: text.slice(1),
          session_id: this.sid
        }
      )

      if (r?.type === 'send' && r.message) {
        this.#send(r.message)
      } else if (r?.output?.trim()) {
        this.transcript.panel(`/${name}${arg ? ` ${arg}` : ''}`, r.output)
      }

      if (r?.warning) {
        this.transcript.notice(r.warning, 'warning')
      }
    } catch (error) {
      this.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
    }

    this.changed()
  }

  interrupt() {
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
    this.#activity.reset(true)
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

      if (this.sid === sid) {
        this.#startupAttachmentPending = true
      }
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
    try {
      if (await this.#resume(id)) {
        this.transcript.notice('Reconnected to the agent backend.')
      }
    } catch (error) {
      this.transcript.notice(
        `Could not reattach the session: ${error instanceof Error ? error.message : String(error)}`,
        'error'
      )
    }

    this.changed()
  }

  /** Closes the open session and starts a fresh one with an empty transcript. */
  async newSession() {
    const token = this.#switches.begin()

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
    } finally {
      this.#settle(token)
    }
  }

  /** Resumes stored session `id`: its history replaces the transcript, and the session it leaves is closed. */
  async resume(id: string) {
    if (this.busy) {
      this.transcript.notice('Wait for the current turn to finish (or press Esc) before switching sessions.', 'warning')
      this.changed()

      return
    }

    const previous = this.sid
    const r = await this.#resume(id)

    if (r && previous && previous !== r.session_id) {
      this.#gw.request('session.close', { session_id: previous }).catch(() => undefined)
    }
  }

  /** Resumes and adopts stored session `id`; undefined when a later switch superseded this one. */
  async #resume(id: string): Promise<CreateResult | undefined> {
    const token = this.#switches.begin()

    try {
      const r = await this.#gw.request<CreateResult>('session.resume', { cols: this.#tern.caps.cols, session_id: id })

      if (!this.#switches.current(token)) {
        return undefined
      }

      this.transcript.clear()
      this.transcript.push({ id: this.transcript.id('w'), kind: 'welcome' })
      this.#adopt(r)

      return r
    } finally {
      this.#settle(token)
    }
  }

  #adopt(r: CreateResult) {
    if (this.sid !== r.session_id) {
      this.dispatches.reset()
      this.#folds.clear()
      this.#foldRevs.clear()
      this.#lastSubmitted = null
      this.#retry = null
      this.#startupAttachmentPending = false
    }

    this.sid = r.session_id
    this.storedSid = r.info?.stored_session_id || r.stored_session_id || null
    this.todoHud.adopt(this.storedSid ?? r.session_id)
    writeActiveSessionFile(this.storedSid ?? r.session_id)
    this.info = r.info ?? this.info
    this.usage = r.info?.usage ?? null
    // A resumed session may be mid-turn: Esc stops it and new prompts queue behind it.
    this.busy = busyFrom(r)
    this.#activity.reset(this.busy !== null)
    this.transcript.usageBase(r.info?.usage ?? undefined)

    if (r.messages?.length) {
      this.transcript.load(r.messages)
    }

    if (r.inflight) {
      this.transcript.inflight(r.inflight, this.busy?.startedAt)
    }

    this.changed()
  }

  /** Ends switch `token`; once none is in flight, held requests for the adopted session open and the queue drains. */
  #settle(token: number) {
    this.#switches.end(token)

    if (this.#switches.pending) {
      return
    }

    const held = this.#heldRequests
    this.#heldRequests = []

    for (const req of held) {
      this.#onRequest(req)
    }

    this.#drainQueue()
    this.changed()
  }

  // ── Gateway ────────────────────────────────────────────────────────

  #onGatewayEvent(ev: AnyGatewayEvent) {
    // Another session's traffic (one being closed, or left by a switch) never reaches this transcript.
    if (!ownsEvent(this.sid, ev)) {
      return
    }

    const t = this.transcript
    this.#activity.event(ev)

    switch (ev.type) {
      case 'gateway.ready':
        this.#applySkin(ev.payload?.skin)
        this.#splash?.ready()
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
        if (this.sid) {
          this.todoHud.update(t.todos(ev.payload?.todos ?? []))
        }

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
      case 'message.complete': {
        if (!this.#visible && this.busy) {
          const status = ev.payload?.status
          this.dispatches.show({
            key: `turn:${t.id('done')}`,
            text: status === 'error' ? 'A Hermes turn failed while this pane was hidden.' :
              status === 'interrupted' ? 'A Hermes turn was stopped while this pane was hidden.' :
              'A Hermes turn finished while this pane was hidden.',
            level: status === 'error' ? 'error' : status === 'interrupted' ? 'warn' : 'success',
            kind: 'ttl'
          }, Date.now(), true)
        }

        t.complete(ev.payload ?? {})
        const failed = t.entries.findLast(entry => entry.kind === 'turn')
        const submitted = this.#lastSubmitted
        this.#retry = ev.payload?.status === 'error' && submitted?.replayable && submitted.sid === this.sid &&
          failed?.kind === 'turn' && failed.retryable
          ? { sid: submitted.sid, text: submitted.text, turnId: failed.id }
          : null
        this.#lastSubmitted = null
        this.busy = null
        this.#drainQueue()

        break
      }

      case 'status.update':
        if (this.busy && ev.payload?.text && ev.payload.kind === 'status') {
          this.#label(ev.payload.text)
        }

        break

      case 'notification.show':
        if (ev.payload) {
          this.dispatches.show(ev.payload, Date.now(), !this.#visible)
        }

        break

      case 'notification.clear':
        if (ev.payload?.key) {
          this.dispatches.clear(ev.payload.key)
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
        this.#splash?.ready()

        break

      case 'gateway.protocol_error':
        t.notice(`Protocol error from the agent backend: ${ev.payload?.preview ?? ''}`, 'error')

        break

      case 'background.complete':

      case 'btw.complete':
        if (ev.payload && 'text' in ev.payload && typeof ev.payload.text === 'string' && ev.payload.text.trim()) {
          t.panel(ev.type === 'btw.complete' ? '/btw' : 'Background task', ev.payload.text)

          if (!this.#visible) {
            this.dispatches.show({
              key: `task:${ev.payload.task_id}`,
              text: ev.type === 'btw.complete' ? 'A side question was answered while this pane was hidden.' :
                'A background task finished while this pane was hidden.',
              level: 'success',
              kind: 'ttl'
            }, Date.now(), true)
          }
        }

        break

      case 'request.cancel':
        this.#heldRequests = this.#heldRequests.filter(r => r.id !== ev.payload?.id)
        this.#dropPrompts(key => key === `prompt:${ev.payload?.id}`)

        break

      case 'approval.cancelled':
        this.#dropPrompts(key => ev.payload?.request_ids.includes(this.#approvalIds.get(key) ?? '') ?? false)

        break

      case 'voice.status':
        break

      default:
        return
    }

    this.changed()
  }

  #onRequest(req: ServerRequest) {
    const route = this.#switches.route(this.sid, req.params.session_id)

    if (route === 'hold') {
      this.#heldRequests.push(req)

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
      const palette = programPaletteOf(skin)

      this.#surface.palette(palette)
      // The splash draws in theme tokens only, so this recolours its next frame.
      this.#splash?.palette(palette)
    }
  }

  /**
   * Covers the session chrome with the launch splash until the gateway is
   * ready (`HERMES_TUI_SPLASH`; see `splash/launch.ts`). It draws on its own
   * `screen` surface in Tern's theme, until the gateway names a skin the user chose.
   */
  #startSplash() {
    const setting = splashSetting()

    if (!setting.enabled || this.#tern.caps.reduceMotion) {
      return
    }

    this.#splash = new LaunchSplash({
      design: pickSplashDesign(setting.design),
      onDone: () => {
        this.#splash = undefined
        // The caret was the composer's all along; say so again now that it shows.
        this.#surface.focus(this.#focus)
        this.changed()
      },
      open: () => this.#tern.open({ id: 'splash', mode: 'screen', role: SPLASH_ROLE, title: 'hermes' }),
      size: () => splashInsets(this.#tern.caps.cols, process.stdout.rows ?? 24),
      status: 'summoning hermes…',
      tickMs: splashTickMs()
    })
    this.#splash.start()
  }

  #label(label: string) {
    if (this.busy && label) {
      this.busy.label = label
    }
  }

  /** The single live effort owner, including a lazy session before its first model turn. */
  setReasoning(value: string, scope?: 'session' | 'global', sid = this.sid): Promise<ConfigSetResult | undefined> {
    const write = async () => {
      if (!sid || this.sid !== sid) {
        return undefined
      }

      const result = await this.#gw.request<ConfigSetResult>('config.set', {
        key: 'reasoning',
        session_id: sid,
        value,
        ...(scope ? { scope } : {})
      })

      if (this.sid !== sid) {
        return undefined
      }

      const current = await this.#gw.request<ConfigGetResult>('config.get', { key: 'reasoning', session_id: sid })

      if (this.sid === sid && typeof current.value === 'string') {
        this.info = { ...this.info, reasoning_effort: current.value }
        this.changed()

        return result
      }

      if (this.sid === sid) {
        throw new Error('The backend did not confirm the live reasoning effort.')
      }


      return undefined
    }

    const result = this.#effortWrites.then(write, write)
    this.#effortWrites = result.catch(() => undefined)

    return result
  }

  /** Steps the session's reasoning effort. The native glyph changes only after readback. */
  cycleEffort() {
    const sid = this.sid

    if (!sid) {
      return
    }

    const current = this.#effortRequested?.sid === sid ? this.#effortRequested.value : this.info?.reasoning_effort ?? ''
    const at = EFFORTS.indexOf(current)
    const request = { sid, value: EFFORTS[at < 0 ? EFFORTS.indexOf('medium') : (at + 1) % EFFORTS.length]! }
    this.#effortRequested = request
    this.setReasoning(request.value, 'session', sid).catch((error: Error) => {
      if (this.sid === sid) {
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
  dequeue() {
    const next = this.queue.shift()

    if (next !== undefined) {
      this.composer.set(this.composer.text ? `${next}\n${this.composer.text}` : next)
      this.changed()
    }
  }

  /** Sends the oldest queued prompt once the session is adopted and idle (no turn, switch or startup image pending). */
  #drainQueue() {
    if (this.busy || !this.sid || this.#switches.pending || this.#startupImage) {
      return
    }

    const next = this.queue.shift()

    if (next) {
      this.#send(next, { queued: true })
    }
  }

  // ── View ───────────────────────────────────────────────────────────

  /** Keep exactly one expiry wake-up; the SDK still owns painting and frame credits. */
  #scheduleDispatchExpiry(now: number) {
    const deadline = this.dispatches.nextExpiry(now)

    if (deadline === this.#dispatchDeadline) {
      return
    }

    if (this.#dispatchTimer) {
      clearTimeout(this.#dispatchTimer)
      this.#dispatchTimer = undefined
    }

    this.#dispatchDeadline = deadline

    if (deadline !== null) {
      this.#dispatchTimer = setTimeout(() => {
        this.#dispatchTimer = undefined
        this.#dispatchDeadline = null
        this.changed()
      }, Math.max(1, deadline - now))
    }
  }

  #render() {
    if (this.#surface.closed) {
      return
    }

    const now = Date.now()
    const dispatches = this.dispatches.active(now)
    this.#scheduleDispatchExpiry(now)
    const info = this.info
    const usage = this.usage
    const backend = info?.version && info.version !== 'unknown' ? `v${info.version}` : ''

    const cx = {
      copy: (text: string) => copyToClipboard(text),
      cwd: info?.cwd ?? '',
      onCopyError: () => {
        this.transcript.notice('Could not copy the answer to the clipboard.', 'warning')
        this.changed()
      },
      foldRevision: (turnId: string) => this.#foldRevs.get(turnId) ?? 0,
      toolCollapsed: (turnId: string, callId: string) => this.#folds.get(turnId + ':' + callId),

      canRetry: (turnId: string) => this.canRetry(turnId),
      retry: (turnId: string) => this.retryFailed(turnId),
      now,
      rewind: () => {
        if (!this.sid) {
          return
        }

        this.#gw.request('session.undo', { session_id: this.sid }).catch((error: Error) => {
          this.transcript.notice(error.message, 'error')
          this.changed()
        })
      },
      welcome: { ...this.#welcome, version: this.#welcome.version || backend }
    }

    const used = usage?.context_used ?? 0
    const max = usage?.context_max ?? 0
    const modal = this.overlays.at(-1)?.modal === true
    this.#orb?.update(this.#activity.state(this.overlays.some(o => o.key.startsWith('prompt:'))), modal)

    // Every composer change (keys, native edits and undo, submits, queue edits) ends in a render: refresh here.
    if (!modal) {
      this.#completion.update(this.composer)
    }

    this.#layerOwners.clear()
    this.#surface.render({
      dock: dockNodes({
        branch: info?.branch ?? '',
        todos: this.todoHud.visible(Boolean(this.busy)),
        todoExpanded: this.todoHud.expanded,
        onTodoToggle: () => {
          this.todoHud.expanded = !this.todoHud.expanded
          this.changed()
        },
        dispatches,
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
        orb: this.#orb?.props(),
        onContext: () => void this.slash('/usage'),
        onEdit: ev => {
          this.composer.edit(ev)
          this.changed()
        },
        onEffort: () => this.cycleEffort(),
        onInterrupt: () => this.interrupt(),
        onSettings: () => openSettings(this),
        onModel: () => openModelPicker(this),
        onDismiss: key => {
          this.dispatches.clear(key)
          this.changed()
        },
        onQueueEdit: () => this.dequeue(),
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
