// One omp.session surface over a gateway session; keys stay with their input owner.

import type {
  ClarifyLockResult,
  ClarifyNote,
  ConfigGetResult,
  ConfigSetResult,
  PromptSubmitResult,
  RequestAnswerResult,
  SessionLiveInfo,
  SessionResumeResult,
  SkinPayload,
  TranscriptMessage,
  Usage
} from '@hermes/shared/gateway-events'
import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import type { Key, ScrollTo, Session, Surface, TspEvent, ViewInput } from '@stencil-hq/tern'
import type { GatewayClient } from '@tui/gatewayClient.js'
import type { AnyGatewayEvent } from '@tui/gatewayTypes.js'
import { writeActiveSessionFile } from '@tui/lib/activeSessionFile.js'

import logo from '../assets/logo.png'

import { type ActionContext, actionForKey, matchesAction } from './actions.js'
import { Attachments, eventImageSource, pastedImageSource, type SubmittedImage } from './attachments.js'
import { Dispatches } from './attention.js'
import { BindingPreferences } from './binding-preferences.js'
import { focusBrowserBlock } from './browser-blocks.js'
import { BtwReports } from './btw.js'
import { BusyInput } from './busy-input.js'
import { copyPrompt, copyToClipboard } from './clipboard.js'
import { canonicalCommand } from './classic-commands.js'
import { localCommand } from './commands.js'
import { Composer } from './composer.js'
import { Dictation } from './dictation.js'
import { editExternal } from './external-editor.js'
import { type Busy, busyFrom, ownsEvent, Switches } from './flow.js'
import { FramePump } from './frame.js'
import { HostLifecycle } from './host-lifecycle.js'
import { LiveVoice } from './live-voice.js'
import { MediaDelivery, type MediaPath, ternSharesFrontendHost } from './media-delivery.js'
import { ModelRecents } from './model-recents.js'
import type { UserEntry } from './model.js'
import { openOperationalSheet } from './operations.js'
import { OrbActivity, ThinkingOrb } from './orb.js'
import type { Overlay, OverlayHost } from './overlay.js'
import { openAgentInspector } from './overlays/agent-inspector.js'
import { type ApprovalPrompt, isApprovalPrompt } from './overlays/approval.js'
import { Completion } from './overlays/completion.js'
import { JobsSheet } from './overlays/jobs.js'
import { openModelPicker } from './overlays/models.js'
import { openPlanReview } from './overlays/plan-review.js'
import { isClarifyPrompt, promptOverlay } from './overlays/prompts.js'
import { openReportSheet } from './overlays/report-sheet.js'
import { openSettings } from './overlays/settings.js'
import type { SheetHost } from './overlays/sheet.js'
import { programPaletteOf } from './palette.js'
import { latestPlan, type PlanStatus, reviewPlanText } from './plan.js'
import { isOperationalCommand, isReportCommand, type Report, type ReportNotice } from './reports.js'
import { Retention } from './retention.js'
import { openRewind, rewindDisabledReason } from './rewind.js'
import { SPLASH_ROLE } from './splash/index.js'
import { LaunchSplash, pickSplashDesign, splashInsets, splashSetting, splashTickMs } from './splash/launch.js'
import { SurfaceProtocol, SurfaceView } from './surface-protocol.js'
import { appTableCharts } from './table-charts.js'
import { TodoHud } from './todo-hud.js'
import { ToolPresentation } from './tool-presentation.js'
import { Transcript } from './transcript.js'
import { dockNodes } from './view/dock.js'
import { projectedEntryNodes } from './view/transcript.js'
import { randomTip, type WelcomeContext } from './view/welcome.js'
import { VimPreference } from './vim-preference.js'

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
  readonly jobs = new JobsSheet(this)
  readonly btw = new BtwReports(this)
  readonly composer = new Composer()
  readonly modelRecents = new ModelRecents()
  readonly dictation = new Dictation(this)
  readonly liveVoice = new LiveVoice(this)
  readonly busyInput = new BusyInput(this)
  readonly bindings = new BindingPreferences(this)
  readonly vimPreference = new VimPreference(this)
  readonly tableCharts = appTableCharts(this)
  readonly attachments: Attachments
  readonly mediaDelivery: MediaDelivery
  readonly overlays: Overlay[] = []
  /** Presentation-only collapse overrides, scoped by transcript turn and tool identity. */
  readonly #tools = new ToolPresentation()
  /** Completed side-agent results projected only into dismissible dock notices. */
  readonly #reports = new Map<string, ReportNotice>()
  #retention: Retention | undefined
  sid: string | null = null
  /** The stored (database) id of the open session: what `session.list` rows are keyed by. */
  storedSid: string | null = null
  info: SessionLiveInfo | null = null
  usage: Usage | null = null
  busy: Busy | null = null
  rewinding: Busy | null = null
  queue: string[] = []
  readonly #tern: Session
  readonly #gw: GatewayClient
  readonly #completion: Completion
  readonly #welcome: WelcomeContext
  #surface!: Surface
  #protocol!: SurfaceProtocol
  #surfaceView = new SurfaceView()
  #skin: SkinPayload | null = null
  /** Owners of native handlers in the last rendered layer and dock prompts. */
  readonly #layerOwners = new Map<string, Overlay>()
  readonly #overlayIds = new WeakMap<Overlay, string>()
  #overlaySerial = 0
  readonly #activity = new OrbActivity()
  #orb: ThinkingOrb | undefined
  #frames!: FramePump
  #dispatchTimer: ReturnType<typeof setTimeout> | undefined
  #dispatchDeadline: number | null = null
  #visible = true
  #lastSubmitted: { sid: string; text: string; replayable: boolean } | null = null
  #retry: { sid: string; text: string; turnId: string } | null = null
  #startupAttachmentPending = false
  /** The field holding Tern's caret, as last sent. */
  #focus: string | null | undefined = INPUT_ID
  #exitArmed = 0
  #done = Promise.withResolvers<number>()
  readonly #switches = new Switches()
  readonly #hostLifecycle: HostLifecycle
  #quitting = false
  /** Server requests for another session, kept while a switch is in flight. */
  #heldRequests: ServerRequest[] = []
  /** Open approval prompts' overlay keys → their approval-queue `request_id` (what approval.cancelled names). */
  readonly #approvalIds = new Map<string, string>()
  /** The launcher's startup image until it is attached to the first session (the queue waits for it). */
  #startupImage = process.env.HERMES_TUI_IMAGE?.trim() ?? ''
  #effortWrites: Promise<unknown> = Promise.resolve()
  #reasoningToggles: Promise<unknown> = Promise.resolve()
  #submittingApproval = false
  #effortRequested: { sid: string; value: string } | null = null
  #editingExternal = false
  /** The launch splash while it covers the session chrome (it takes the keys until it leaves). */
  #splash: LaunchSplash | undefined

  constructor(tern: Session, gw: GatewayClient, version: string, writeHost: (text: string) => void = text => { process.stdout.write(text) }) {
    this.#hostLifecycle = new HostLifecycle(writeHost)
    this.#tern = tern
    this.#gw = gw
    this.mediaDelivery = new MediaDelivery(tern, gw, () => this.sid, () => this.changed())
    this.attachments = new Attachments(gw, () => {
      this.changed()

      if (this.#startupAttachmentPending && !this.#startupImage) {
        this.#drainQueue()
      }
    }, message => this.notice(message), false, () => ternSharesFrontendHost())
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
    this.#protocol = new SurfaceProtocol(this.#tern, {
      replace: surface => this.#bindSurface(surface),
      changed: () => this.changed(),
      credit: () => this.#frames?.credit(),
      report: message => {
        // Credit-starved or failed surfaces cannot display their own diagnostic yet.
        process.stderr.write(`${message}\n`)
        this.notice(message)
      }
    })
    this.#surface = this.#protocol.open()

    this.#bindSurface(this.#surface)

    this.#frames = new FramePump(
      () => this.#protocol.blocked,
      () => this.#paint(),
      fn => setImmediate(fn)
    )

    if (this.#tern.caps.features.includes('blobs')) {
      this.#welcome.logo = this.#tern.blob(logo, 'image/png')
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
      this.attachments.clear()
      this.dictation.reset()
      this.liveVoice.disconnect()
      this.sid = null
      this.tableCharts.session('')
      this.todoHud.adopt(null)
      this.jobs.adopt(null)
      this.btw.adopt(null)
      this.busy = null
      this.transcript.interrupt()
      this.dispatches.reset()
      this.#lastSubmitted = null
      this.#retry = null
      this.#dropPrompts(() => true)
      // Whatever went wrong is in the transcript: let it be seen.
      this.#splash?.ready()
      this.#activity.event({ type: 'error' } as AnyGatewayEvent)
      this.changed()
    })
    this.#gw.drain()
    this.#paint()
    this.#surface.focus(INPUT_ID)
    void this.#readInput()

    const code = await this.#done.promise
    this.#orb?.close()
    this.#frames.close()
    this.#protocol.dispose()
    await this.#tern.close()
    this.#gw.kill('exit')

    return code
  }

  #bindSurface(surface: Surface) {
    this.#orb?.close()
    this.#surface = surface
    this.#surfaceView = new SurfaceView()
    this.#retention = this.#tern.caps.features.includes('settle') ? new Retention() : undefined
    // Force prompt focus to be reasserted even when its id is unchanged.
    this.#focus = surface.id === 'hermes' ? INPUT_ID : undefined
    const view = this.#surfaceView
    const render = surface.render.bind(surface)
    const originalDispatch = surface.dispatch.bind(surface)

    surface.render = input => {
      if (view.recovering) {
        view.paint(surface, input)
      } else {
        render(input)
        view.remember(input)
      }

      this.#protocol.rendered()
    }

    const dispatch = (event: TspEvent) => (view.recovering ? view.dispatch(event) : originalDispatch(event))

    this.#surface.dispatch = event => {
      const handler = this.#retention?.dispatch(event, this.#surface.id, () => this.changed()) ?? dispatch(event)

      if (surface !== this.#surface || surface.closed) {
        return
      }

      if (
        !handler ||
        !('id' in event) ||
        typeof event.id !== 'string' ||
        (!event.id.startsWith('layer.') && !event.id.startsWith('dock.'))
      ) {
        return (
          handler &&
          (() => {
            if (surface === this.#surface && !surface.closed) {
              return handler()
            }
          })
        )
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
        return () => {
          if (surface === this.#surface && !surface.closed) {
            return handler()
          }
        }
      }

      // Session queues handler calls. Ownership and question must still match.
      const revision = owner.inputRevision

      return () => {
        if (
          surface === this.#surface &&
          !surface.closed &&
          this.owns(owner) && owner.inputRevision === revision &&
          this.#overlayIds.get(owner) === rootId
        ) {
          return handler()
        }
      }
    }

    if (this.#skin) {
      this.#applySkin(this.#skin)
    }

    if (this.#tern.caps.features.includes('blobs')) {
      this.#orb = new ThinkingOrb(this.#tern, surface)
      this.#orb.environment({ visible: this.#visible })
    }
  }

  // ── OverlayHost ────────────────────────────────────────────────────

  open(overlay: Overlay) {
    const same = this.overlays.find(o => o.key === overlay.key)

    if (same) {
      this.close(same)
    }

    // Inspection results must not cover an approval/clarification waiting for input.
    const prompt = ['report', 'agent-inspector', 'agent-hub', 'plan', 'lsp'].includes(overlay.key) ? this.overlays.findIndex(o => o.key.startsWith('prompt:')) : -1
    this.overlays.splice(prompt < 0 ? this.overlays.length : prompt, 0, overlay)
    this.#overlayIds.set(overlay, `${overlay.placement ?? 'layer'}.${overlay.key}:${++this.#overlaySerial}`)

    if (overlay.modal || overlay.placement === 'dock') {
      // A waiting request needs the pane immediately, not the splash's exit animation.
      this.#splash?.dismiss()
      // Clear a stale completion before handing approval keys to the dock.
      this.#completion.dismiss()
    }

    this.changed()
  }

  close(overlay: Overlay) {
    // By identity: a stale callback of a replaced overlay must not close its same-key successor.
    const at = this.overlays.indexOf(overlay)

    if (at >= 0) {
      this.overlays.splice(at, 1)
      overlay.onClose?.()
      this.#overlayIds.delete(overlay)
      this.#approvalIds.delete(overlay.key)

      if (overlay.key === 'settings') {
        void this.vimPreference.refresh()
        void this.busyInput.refresh()
      }

      this.changed()
    }
  }

  /** One input owner: the top floating overlay, otherwise the oldest dock approval. */
  #inputOwner(): Overlay | undefined {
    return this.overlays.findLast(o => o.placement !== 'dock') ?? this.overlays.find(isApprovalPrompt) ?? this.overlays.find(isClarifyPrompt)
  }

  owns(overlay: Overlay): boolean {
    return !this.#surface.closed && this.#inputOwner() === overlay && this.#overlayIds.has(overlay)
  }

  toggleClarify() {
    const owner = this.#inputOwner()

    if (owner && isClarifyPrompt(owner)) {
      owner.toggle()
    }
  }

  promptAttachments(): Attachments {
    return new Attachments(this.#gw, () => this.changed(), message => this.notice(message), true, () => ternSharesFrontendHost())
  }

  lockClarify(request_id: string, question_id: string, answer: string | null, note?: ClarifyNote) {
    return this.#gw.request<ClarifyLockResult>('clarify.lock', {
      request_id, question_id, answer, ...(note ? { note } : {})
    })
  }

  async confirmDenial(id: string): Promise<void> {
    const result = await this.#gw.request<RequestAnswerResult>('request.answer', { id, result: { choice: 'deny' } })

    if (result.status !== 'ok') {
      throw new Error('The approval is no longer pending. Your message was not sent.')
    }
  }

  notice(message: string) {
    this.transcript.notice(message, 'error')
    this.changed()
  }

  changed() {
    this.#hostLifecycle.project({
      sid: this.#quitting ? null : this.sid,
      working: Boolean(this.busy && this.busy.confirmed !== false),
      submitting: this.busy?.confirmed === false,
      waiting: this.busy?.waiting === true || this.overlays.some(o => o.key.startsWith('prompt:'))
    })
    this.#frames?.changed()
  }

  scrollOverlay(overlay: Overlay, child: string, to: ScrollTo) {
    const id = this.#overlayIds.get(overlay)

    if (id && this.overlays.at(-1) === overlay) {
      this.#surface.scroll(`${id}.${child}`, to)
    }
  }

  report(report: Report) {
    openReportSheet({ ...this.#sheetHost(), copy: copyToClipboard }, report)
  }

  #planRequest = 0

  async reviewPlan() {
    const sid = this.sid
    const request = ++this.#planRequest
    const candidate = latestPlan(this.transcript.entries)
    let status: PlanStatus | undefined

    try {
      status = await this.#gw.request<PlanStatus>('plan.status', { session_id: sid })
    } catch {
      // Older gateways keep the explicitly non-authoritative Markdown review MVP.
    }

    if (this.sid !== sid || request !== this.#planRequest || !sid) { return }
    openPlanReview({
      ...this.#sheetHost(),
      sessionId: sid,
      request: (method, params) => {
        if (this.sid !== sid) { return Promise.reject(new Error('Session changed')) }

        return this.#gw.request(method, { ...params })
      },
      owns: overlay => this.owns(overlay) && this.sid === sid &&
        (status?.plan !== undefined && status?.plan !== null || latestPlan(this.transcript.entries)?.text === candidate?.text),
      submit: text => {
        if (this.sid === sid) {
          this.#submit(text)
          this.changed()
        }
      }
    }, status?.plan ? reviewPlanText(status.plan.text) : status?.enabled || status?.generating ? undefined : candidate, status)
  }

  #sheetHost(): SheetHost {
    return {
      open: overlay => this.open(overlay),
      close: overlay => this.close(overlay),
      changed: () => this.changed(),
      scroll: (overlay, to: ScrollTo) => this.scrollOverlay(overlay, 'body.markdown', to)
    }
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
    if (this.#protocol.state !== 'visible') {
      return
    }

    // Any key skips the launch splash, and is spent doing so.
    if (this.#splash?.active) {
      return this.#splash.skip()
    }

    const stop = this.bindings.actions.find(action => action.id === 'app.interrupt.owned')!

    if (matchesAction(stop, key)) {
      return stop.run(this)
    }

    const top = this.#inputOwner()

    // Settings owns cancellation; reports must never clear the hidden draft.
    const clear = this.bindings.actions.find(action => action.id === 'app.clear')!

    if (matchesAction(clear, key) && (!top || (key.ctrl && key.name === 'c'))) {
      return top?.key === 'settings' || top?.key === 'agent-hub' || top?.key === 'agent-inspector' || top?.key === 'report' || top?.key === 'plan' || top?.key === 'history'
        ? top.onKey(key)
        : clear.run(this)
    }

    const clarifyToggle = this.bindings.actions.find(action => action.id === 'app.clarify.toggle')!

    if (top && isClarifyPrompt(top) && matchesAction(clarifyToggle, key)) {
      return clarifyToggle.run(this)
    }

    const approve = this.bindings.actions.find(action => action.id === 'app.approval.approve')!

    if (top && isApprovalPrompt(top) && !this.composer.text && matchesAction(approve, key)) {
      return approve.run(this)
    }

    if (top && (isClarifyPrompt(top) || top.placement !== 'dock' || !this.composer.text) && top.onKey(key)) {
      return
    }

    if (top?.modal) {
      return
    }

    if (key.name === 'paste' && key.text && this.#pasteImage(key.text)) {
      return
    }

    const escape = this.bindings.actions.find(action => action.id === 'app.interrupt')!

    if (this.liveVoice.captureBlocked && matchesAction(escape, key)) {
      return escape.run(this)
    }

    if (this.#completion.onKey(key)) {
      return
    }

    if (this.composer.vim.key(key)) { return }

    const ctx: ActionContext = {
      composerEmpty: !this.composer.text,
      busy: Boolean(this.busy),
      queued: this.queue.length > 0,
      overlayOpen: this.overlays.length > 0,
      completionOpen: this.#completion.open
    }

    const shortcut = actionForKey(key, ctx, this.bindings.actions)

    if (shortcut) {
      return shortcut.run(this)
    }

    // Unbound Alt letters are commands, never literal typing. Keep readline's
    // Alt+B/F/D editing behavior by forwarding the key without printable text.
    const action = this.composer.key(key.alt && /^[a-z]$/i.test(key.name) ? { ...key, text: undefined } : key)

    if (action === 'submit') {
      void this.#submitDraft()
    }
  }

  /** A terminal $EDITOR needs the grid; native Tern file blocks do not. */
  async editExternal() {
    if (this.#editingExternal) {
      return
    }

    this.#editingExternal = true
    const grid = !process.env.TERN_WINDOW_KEY

    if (grid) {
      this.#surface.suspend()
    }

    try {
      await editExternal(this)
    } finally {
      this.#editingExternal = false

      if (grid && !this.#surface.closed) {
        this.#surface.resume()
      }
    }
  }

  /** Explicit history-scroll intent: SDK 0.1 has no viewport/reload event. */
  olderHistory(): void {
    if (this.#retention) {
      this.#retention.request(true)
    } else {
      this.#surface.scroll('main', 'start')
    }

    this.changed()
  }

  /** Copy the draft literally, without submitting it or disturbing the caret. */
  copyPrompt(currentLine = false) { copyPrompt(this, currentLine) }

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

  toggleToolExpansion(): void {
    this.#tools.expand(this.transcript.entries, this.info?.cwd ?? '', this.#tern.caps.kinds.includes('media'),
      !this.#gw.attached && this.info?.terminal_backend === 'local')
    this.#invalidateTools()
  }

  toggleToolVisibility(): void {
    this.#tools.toggleVisibility()
    this.#invalidateTools()
  }

  #invalidateTools(): void {
    for (const entry of this.transcript.entries) {
      if (entry.kind === 'turn') {
        this.#retention?.invalidate(entry.id)
      }
    }

    this.changed()
  }

  #pasteImage(text: string): boolean {
    const source = pastedImageSource(text, ternSharesFrontendHost())

    if (source && 'path' in source) { source.host = 'tern' }

    if (!source || !this.sid || this.#switches.pending) {
      return false
    }

    void this.attachments.add(source, this.sid)

    return true
  }

  #onTernEvent(ev: TspEvent) {
    // Splash events must reach its owner before the inline surface address filter.
    if (ev.ev === 'gone' && ev.ids.includes('splash')) {
      this.#splash?.dismiss()
    }

    if (!('sf' in ev) || !ev.sf || ev.sf === this.#surface.id || ev.sf === 'splash') {
      if (ev.ev === 'motion') {
        this.#splash?.environment({ reduce: ev.reduce })
      }

      if ((ev.ev === 'visible' || ev.ev === 'resize') && ev.visible !== undefined) {
        this.#splash?.environment({ visible: ev.visible })
      }
      // Theme events need no new cells: splash CSS and spans resolve native tokens live.
    }

    this.#protocol.event(ev)

    if ('sf' in ev && ev.sf && ev.sf !== this.#surface.id) {
      return
    }

    if (ev.ev === 'unknown' && ev.sf === this.#surface.id && !this.#inputOwner() && !this.#splash?.active) {
      const source = eventImageSource(ev.raw)

      if (source && this.sid && !this.#switches.pending) {
        void this.attachments.add(source, this.sid)
      }
    }

    this.#retention?.gone(ev, this.#surface.id)

    if (ev.ev === 'gone') {
      this.#surfaceView.forget(ev.ids)
      this.#focus = undefined

      if (this.#surface.closed) {
        this.#orb?.close()
      }
    }

    if (ev.ev === 'toggle' && ev.sf === this.#surface.id && ev.key) {
      // Tern owns mouse folding. Mirror only the clicked tool's presentation
      // state, so the subsequent Ctrl+O reverses what the person actually saw.
      for (const entry of this.transcript.entries) {
        if (entry.kind !== 'turn' || (!ev.id.startsWith('main.' + entry.id + '.') && !ev.id.startsWith('main.' + entry.id + '~'))) {
          continue
        }

        const match = entry.blocks.find(b => b.kind === 'tool' && (b.call.id === ev.key || `${entry.id}~${b.id}` === ev.key))

        if (match?.kind === 'tool') {
          this.#tools.mirror(entry.id, match.call.id, ev.collapsed)
          this.#retention?.invalidate(entry.id)
          this.changed()

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

    if (ev.ev === 'focus' && ev.id === INPUT_ID && !this.#inputOwner()?.modal) {
      this.#focus = INPUT_ID
      this.#surface.focus(INPUT_ID)
    }
  }

  ctrlC() {
    if (this.liveVoice.blocked) { void this.liveVoice.control('stop');

 return }

    if (this.dictation.blocked) {
      void this.dictation.stop(true)

      return
    }

    if (this.composer.text || this.attachments.items.length) {
      this.composer.set('')
      this.attachments.clear()

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
    this.tableCharts.close()
    this.#quitting = true
    this.#splash?.dismiss()
    this.mediaDelivery.clear(true)
    this.attachments.clear()
    this.changed()
    void this.dictation.stop(true)
    void this.liveVoice.control('stop')

    for (const overlay of [...this.overlays]) {
      this.close(overlay)
    }

    if (this.#dispatchTimer) {
      clearTimeout(this.#dispatchTimer)
      this.#dispatchTimer = undefined
      this.#dispatchDeadline = null
    }

    this.jobs.adopt(null)
    this.#done.resolve(code)
  }

  // ── Prompts and commands ───────────────────────────────────────────

  /** The registered busy-only Alt+Enter action; approval denial retains priority. */
  submitAlternate() {
    void this.#submitDraft(this.composer.text, this.overlays.find(isApprovalPrompt) ?? null, true)
  }

  /** The painted sendable flag and every submit handler share this admission gate. */
  #draftAdmitted(): boolean {
    const owner = this.#inputOwner()

    const approval = this.overlays.find(isApprovalPrompt)

    return !this.#quitting && this.sid !== null && !this.#switches.pending &&
      !this.#submittingApproval &&
      !this.rewinding && !this.dictation.blocked && !this.liveVoice.blocked && !this.attachments.blocked &&
      (!owner?.modal || isApprovalPrompt(owner)) && (!approval || this.owns(approval)) &&
      (!owner || !isClarifyPrompt(owner) || owner.hidden)
  }

  /** Keyboard Enter and native send share the request-bound deny → submit transaction. */
  async #submitDraft(raw = this.composer.text, approval: ApprovalPrompt | null = this.overlays.find(isApprovalPrompt) ?? null, alternate = false) {
    if (!this.#draftAdmitted()) {
      return
    }

    // Native handlers retain the generation painted with their composer. Never
    // turn an old Send into a denial of a newly arrived or replaced request.
    if (approval !== (this.overlays.find(isApprovalPrompt) ?? null)) {
      return
    }

    if (this.attachments.blocked) {
      this.transcript.notice('Wait for pending attachments; retry or remove failed images before sending.', 'warning')
      this.changed()

      return
    }

    if (this.attachments.items.length && (!this.sid || this.#switches.pending || raw.trim().startsWith('/'))) {
      this.transcript.notice('Send images with a message in the current session, not a slash command.', 'warning')
      this.changed()

      return
    }

    if (!approval) {
      if (this.busy && this.sid && !this.#switches.pending && !this.attachments.items.length &&
          !raw.trim().startsWith('/') && this.busyInput.shouldSteer(alternate)) {
        await this.busyInput.steer(raw)

        return
      }

      const images = this.sid ? this.attachments.take(this.sid) : []
      this.#submit(this.composer.take(raw).trim() || (images.length ? 'What do you see in this image?' : ''), images)

      return
    }

    if (!raw.trim() || !this.owns(approval) || !this.sid || this.#switches.pending) {
      return
    }

    // Native send can carry text not yet delivered by onEdit. Retain it on failure.
    if (raw !== this.composer.text) {
      this.composer.set(raw)
    }

    const revision = this.composer.rev
    const sid = this.sid
    this.#submittingApproval = true
    this.changed()

    try {
      if (await approval.denyAndConfirm() && this.sid === sid && !this.#switches.pending) {
        // Don't erase edits made while a transport was awaiting completion.
        if (this.composer.rev === revision) {
          this.composer.take(raw)
        }

        // prompt.submit is the normal user-message path. Unlike our local queue,
        // an unqueued submission lets the gateway steer a running tool turn.
        this.#send(raw.trim(), { images: this.attachments.take(sid) })
      }
    } finally {
      this.#submittingApproval = false
      this.changed()
    }
  }

  #submit(raw: string, images: SubmittedImage[] = []) {
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

    if (images.length) {
      this.#send(text, { images, queued: Boolean(this.busy) })

      return
    }

    if (this.busy || !this.sid || this.#switches.pending) {
      this.queue.push(text)

      return
    }

    this.#send(text)
  }

  /** Sends `text` now; `queued` marks a drained queue entry (the gateway must queue it, never steer with it). */
  #send(text: string, { queued = false, images = [] }: { queued?: boolean; images?: SubmittedImage[] } = {}) {
    // A session switch in flight: the prompt belongs to the session it adopts.
    if (!this.sid || this.#switches.pending) {
      this.queue.unshift(text)

      return
    }

    this.#retry = null

    if (this.#startupAttachmentPending) {
      this.#startupAttachmentPending = false
      images = [...images, ...this.attachments.take(this.sid)]
    }

    const submitted = { sid: this.sid, text, replayable: !this.#startupAttachmentPending && !images.length }
    this.#lastSubmitted = submitted
    this.#startupAttachmentPending = false
    const entry = this.transcript.user(text, Date.now(), images)
    this.#startBusy('Working…')
    this.#gw
      .request<PromptSubmitResult>('prompt.submit', {
        session_id: this.sid,
        text,
        image_paths: images.map(image => image.path),
        ...(queued ? { queued } : {})
      })
      .then(result => {
        if (this.sid === submitted.sid && this.transcript.entries.includes(entry)) {
          entry.rowId = result.user_row_id ?? undefined

          if (this.#lastSubmitted === submitted && this.busy) {
            this.busy.confirmed = true
          }

          this.changed()
        }
      })
      .catch((error: Error) => {
        if (this.#lastSubmitted !== submitted || this.sid !== submitted.sid) {
          return
        }

        this.transcript.notice(error.message, 'error')

        if (images.length) {
          this.attachments.restore(images, submitted.sid)

          if (!this.composer.text) {
            this.composer.set(text)
          }
        }

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
        this.busy || this.rewinding || this.#switches.pending || this.queue.length) {
      return false
    }

    const latest = this.transcript.entries.findLast(e => e.kind === 'turn')

    return latest?.kind === 'turn' && latest.id === turnId && latest.retryable === true && latest.status === 'error'
  }

  retryLatest() {
    const latest = this.transcript.entries.findLast(entry => entry.kind === 'turn')

    if (latest) { this.retryFailed(latest.id) }
  }

  approvePending() {
    const owner = this.#inputOwner()

    if (owner && isApprovalPrompt(owner) && !this.composer.text && this.owns(owner)) { owner.approve() }
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
    if (this.rewinding) {
      return
    }

    const [token = '', ...rest] = text.slice(1).split(/\s+/)
    const name = canonicalCommand(token)
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

    const sid = this.sid

    if (name.toLowerCase() === 'btw') {
      await this.btw.show(arg)

      return
    }

    if (isOperationalCommand(name)) {
      await openOperationalSheet(this, name, arg, copyToClipboard)

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

      if (this.sid !== sid) {
        return
      }

      if (r?.type === 'send' && r.message) {
        this.#send(r.message, { queued: name === 'queue' })
      } else if (r?.output?.trim()) {
        const title = `/${name}${arg ? ` ${arg}` : ''}`

        if (isReportCommand(name, arg)) {
          this.report({ title, text: r.output, format: 'plain' })
        } else {
          this.transcript.panel(title, r.output, 'plain')
        }
      }

      if (r?.warning) {
        this.transcript.notice(r.warning, 'warning')
      }
    } catch (error) {
      this.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
    }

    void this.busyInput.refresh()
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
    this.busy = { label, since: {}, startedAt: Date.now(), confirmed: false }
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
      this.#startupAttachmentPending = true
      await this.attachments.add({ path, name: path.split('/').at(-1) || 'Startup image' }, sid)
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
    if (this.rewinding) {
      return
    }

    void this.liveVoice.control('stop')
    const token = this.#switches.begin()
    this.changed()

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
        const closing = this.sid
        await this.#gw.request('session.close', { session_id: closing }).then(() => {
          if (this.#switches.current(token) && this.sid === closing) {
            this.sid = null
            this.busy = null
            this.#dropPrompts(() => true)
            this.changed()
          }
        }).catch(() => undefined)
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
    if (this.busy || this.rewinding) {
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
    void this.liveVoice.control('stop')
    const token = this.#switches.begin()
    this.changed()

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
    this.mediaDelivery.clear()

    if (this.sid !== r.session_id) {
      void this.dictation.stop(true)
      this.dictation.reset()
      this.#dropPrompts(() => true)
      this.dispatches.reset()
      this.#reports.clear()
      this.btw.adopt(this.sid)

      for (const overlay of [...this.overlays]) {
        if (overlay.key === 'report' || overlay.key === 'plan' || overlay.key === 'sessions' || overlay.key === 'session-tree') {
          this.close(overlay)
        }
      }

      this.#tools.reset()
      this.#lastSubmitted = null
      this.#retry = null
      this.#startupAttachmentPending = false
      this.attachments.clear()
    }

    this.sid = r.session_id
    void this.bindings.refresh()
    void this.vimPreference.refresh()
    this.tableCharts.session(r.session_id)
    void this.busyInput.refresh()
    this.storedSid = r.info?.stored_session_id || r.stored_session_id || null
    this.todoHud.adopt(this.storedSid ?? r.session_id)
    this.jobs.adopt(r.session_id)
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
    this.liveVoice.event(ev)

    // Another session's traffic (one being closed, or left by a switch) never reaches this transcript.
    if (!ownsEvent(this.sid, ev)) {
      return
    }

    this.dictation.event(ev)
    const t = this.transcript
    this.jobs.event(ev.type)
    this.#activity.event(ev)

    switch (ev.type) {
      case 'gateway.ready':
        this.#applySkin(ev.payload?.skin)
        this.#splash?.ready()
        // A reconnect's ready reattaches the shown session; only a sessionless app bootstraps.
        void (this.storedSid ? this.#reattach(this.storedSid) : this.#bootstrap())

        break

      case 'table_chart.policy':
        this.tableCharts.configure(ev.payload?.mode ?? 'off')

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

        this.busy!.confirmed = true
        this.busy!.waiting = false
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
        t.reasoningBlock(ev.payload?.text ?? '', Date.now(), ev.payload?.presentation)

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

      case 'tool.output.delta':
        if (ev.payload) {
          t.toolOutput(ev.payload)
        }

        break

      case 'tool.complete':
        if (ev.payload) {
          t.toolComplete(ev.payload)
        }

        break

      case 'eval.update':
        if (ev.payload) { t.evalUpdate(ev.payload) }

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
        const completed = this.busy

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

        if (completed && completed.confirmed !== false && !this.queue.length) {
          this.#hostLifecycle.finish(ev.payload?.status)
        }

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

      case 'btw.update':
        if (ev.payload?.thread) {
          this.btw.adopt(this.sid)
          this.btw.update(ev.payload.thread, true)
        }

        break

      case 'background.complete':

      case 'btw.complete':
        if (ev.payload && 'text' in ev.payload && typeof ev.payload.text === 'string' && ev.payload.text.trim()) {
          const failed = /^error:/i.test(ev.payload.text.trimStart())
          const id = `${ev.type}:${ev.payload.task_id}`
          this.#reports.set(id, {
            id, failed,
            title: ev.type === 'btw.complete' ? '/btw' : 'Background task',
            text: ev.payload.text,
            label: ev.type === 'btw.complete' ? `Side question ${failed ? 'failed' : 'answered'}` :
              `background task ${failed ? 'failed' : 'done'}`
          })

          if (!this.#visible) {
            this.dispatches.show({
              key: `task:${ev.payload.task_id}`,
              text: failed ? 'A side task failed while this pane was hidden. View its report in the dock.' :
                ev.type === 'btw.complete' ? 'A side question was answered while this pane was hidden.' :
                'A background task finished while this pane was hidden.',
              level: failed ? 'error' : 'success',
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
        this.#heldRequests = this.#heldRequests.filter(r => !ev.payload?.request_ids.includes(String(r.params.request_id ?? '')))
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

    if (this.busy) {
      this.busy.waiting = false
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
      this.#skin = skin
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

        if (!this.#quitting) {
          // The caret was the composer's all along; say so again now that it shows.
          this.#surface.focus(this.#focus ?? null)
          this.changed()
        }
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
    if (this.busy || this.rewinding || !this.sid || this.#switches.pending || this.#startupImage || this.attachments.blocked) {
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

  #paint() {
    try {
      this.#render()
    } catch (error) {
      this.#protocol.failure(error)
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
      charts: this.tableCharts,
      copy: (text: string) => copyToClipboard(text),
      cwd: info?.cwd ?? '',
      media: this.#tern.caps.kinds.includes('media'),
      hour12: this.#tern.caps.hour12 ?? false,
      hostLocal: ternSharesFrontendHost() && !this.#gw.attached && info?.terminal_backend === 'local',
      attachmentHostLocal: ternSharesFrontendHost() && !this.#gw.attached,
      gatewayRemote: this.#gw.attached,
      mediaHost: info?.terminal_backend && info.terminal_backend !== 'local' ? 'compute' as const : this.#gw.attached ? 'gateway' as const : 'frontend' as const,
      mediaPreview: (source: MediaPath) => this.mediaDelivery.preview(source),
      mediaRevision: this.mediaDelivery.revision,
      focusBrowser: (id: string) => void focusBrowserBlock(this, id),
      onCopyError: () => {
        this.transcript.notice('Could not copy the answer to the clipboard.', 'warning')
        this.changed()
      },
      inspectAgent: (callId: string, agentId: string) => openAgentInspector(this, { callId, agentId }),
      toolsHidden: this.#tools.hidden && !this.overlays.some(isApprovalPrompt),
      foldRevision: (turnId: string) => this.#tools.foldRevision(turnId),
      toolCollapsed: (turnId: string, callId: string) => this.#tools.collapsed(turnId, callId),
      toggleTool: (turnId: string, callId: string) => {
        const turn = this.transcript.entries.find(e => e.id === turnId)
        const block = turn?.kind === 'turn' ? turn.blocks.find(b => b.kind === 'tool' && b.call.id === callId) : undefined

        if (block?.kind !== 'tool') { return }
        this.#tools.toggle(turnId, block.call, info?.cwd ?? '', this.#tern.caps.kinds.includes('media'),
          !this.#gw.attached && info?.terminal_backend === 'local')
        this.#retention?.invalidate(turnId)
        this.changed()
      },

      canRetry: (turnId: string) => this.canRetry(turnId),
      retry: (turnId: string) => this.retryFailed(turnId),
      now,
      rewind: (entry: UserEntry) => void openRewind(this, this.#gw, entry),
      rewindDisabledReason: (entry: UserEntry) => rewindDisabledReason(this, entry),
      welcome: { ...this.#welcome, version: this.#welcome.version || backend }
    }

    const used = usage?.context_used ?? 0
    const max = usage?.context_max ?? 0
    const modal = this.#inputOwner()?.modal === true
    this.#orb?.update(this.#activity.state(this.overlays.some(o => o.key.startsWith('prompt:'))), modal)

    // Every composer change (keys, native edits and undo, submits, queue edits) ends in a render: refresh here.
    if (!modal) {
      this.#completion.update(this.composer)
    }

    this.#layerOwners.clear()
    const approvals = this.overlays.filter(isApprovalPrompt)
    const approval = approvals[0]
    const asks = this.overlays.filter(isClarifyPrompt)
    const dockPrompt = approval ?? asks[0]
    const promptId = dockPrompt ? this.#overlayIds.get(dockPrompt)! : ''

    if (dockPrompt) {
      this.#layerOwners.set(promptId, dockPrompt)
    }

    const retained = this.#retention?.render(this.transcript, cx, approvals.length > 0)
    const retention = this.#retention

    const paint = retention
      ? (view: ViewInput) => retention.paint(this.#surface, view, retained ?? [])
      : this.#surface.render.bind(this.#surface)

    paint({
      dock: dockNodes({
        actions: this.bindings.actions,
        profile: this.bindings.profile,
        approval: dockPrompt?.node(promptId),
        approvalQueued: approvals.length + asks.length - 1,
        branch: info?.branch ?? '',
        jobs: this.jobs.count,
        onJobs: () => this.jobs.show(),
        todos: this.todoHud.visible(Boolean(this.busy)),
        todoExpanded: this.todoHud.expanded,
        onTodoToggle: () => {
          this.todoHud.expanded = !this.todoHud.expanded
          this.changed()
        },
        dispatches,
        reports: [...this.#reports.values(), ...this.btw.notices],
        onReportView: id => {
          if (id.startsWith('btw:')) {
            if (this.btw.notices.some(notice => notice.id === id)) {
              void this.btw.show('', id.slice('btw:'.length))
            }

            return
          }

          const report = this.#reports.get(id)

          if (report) {
            this.report(report)
          }
        },
        onReportDismiss: id => {
          this.btw.dismiss(id)
          this.#reports.delete(id)
          this.changed()
        },
        busy: this.busy ?? this.rewinding ?? undefined,
        busyMode: this.busyInput.mode,
        composer: this.composer,
        attachments: this.attachments.items,
        onAttachmentRemove: id => void this.attachments.remove(id),
        onAttachmentRetry: id => this.attachments.retry(id),
        dictation: this.dictation,
        liveVoice: this.liveVoice,
        onDictation: () => this.dictation.toggle(),
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
          if (['report', 'agent-inspector', 'agent-hub', 'plan'].includes(this.overlays.at(-1)?.key ?? '')) {
            return
          }

          if (this.composer.vim.enabled) { return }

          if (ev.len === this.composer.text.length && ev.text && this.#pasteImage(ev.text)) {
            this.composer.edit({ ...ev, text: '', cursor: ev.from })
          } else {
            this.composer.edit(ev)
          }

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
          if (['report', 'agent-inspector', 'agent-hub', 'plan'].includes(this.overlays.at(-1)?.key ?? '')) {
            return
          }

          if (this.composer.vim.enabled) { return }

          void this.#submitDraft(ev.text, approval ?? null)
          this.changed()
        },
        onSubmit: () => {
          if (['report', 'agent-inspector', 'agent-hub', 'plan'].includes(this.overlays.at(-1)?.key ?? '')) {
            return
          }

          void this.#submitDraft(this.composer.text, approval ?? null)
          this.changed()
        },
        onUndo: () => {
          if (['report', 'agent-inspector', 'agent-hub', 'plan'].includes(this.overlays.at(-1)?.key ?? '')) {
            return
          }

          if (this.composer.vim.enabled) { return }

          this.composer.undo()
          this.changed()
        },
        placeholder: 'Ask Hermes — / commands · @ files',
        queued: this.queue,
        ready: this.#draftAdmitted()
      }),
      layer: [
        ...this.overlays.filter(o => o.placement !== 'dock').map(o => {
          const id = this.#overlayIds.get(o)!
          this.#layerOwners.set(id, o)

          return o.node(id)
        }),
        ...(modal ? [] : this.#completion.nodes(INPUT_ID))
      ],
      main: retained ? [] : this.transcript.entries.flatMap(e => projectedEntryNodes(e, `main.${e.id}`, cx))
    })

    if (!this.#retention) {
      this.transcript.changedEntries.clear()
    }

    // The top overlay's field holds the caret; a modal sheet without one takes it from the composer.
    const top = this.#inputOwner()
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
