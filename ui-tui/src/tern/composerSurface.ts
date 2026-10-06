import { pauseRendering, resumeRendering, useStdout } from '@hermes/ink'
import { useStore } from '@nanostores/react'
import { useEffect, useMemo, useRef } from 'react'

import type { AppLayoutComposerProps, AppLayoutTranscriptProps } from '../app/interfaces.js'
import { $isBlocked } from '../app/overlayStore.js'
import { useTurnSelector } from '../app/turnStore.js'
import { $uiState } from '../app/uiStore.js'
import { NATIVE_MODE } from '../config/env.js'
import { encodeTspJson, HERMES_TSP_PROGRAM_FEATURES, type TspEvent, type TspHello } from './protocol.js'
import { projectTernTranscript, reconcileTernLiveNodes, type TernLiveNode } from './liveProjection.js'
import { projectTernSubagents } from './subagentProjection.js'
import { $ternSurface, subscribeTernSurfaceEvents } from './surface.js'

export const TERN_SURFACE_ID = 'hermes:session'
export const TERN_COMPOSER_ID = 'hermes:composer'

export type TernComposerSnapshot = {
  cursor: number
  text: string
}

type WriteTsp = (data: string) => void

const clampOffset = (value: number, max: number): number =>
  Number.isFinite(value) ? Math.min(Math.max(Math.trunc(value), 0), max) : 0

export function applyTernComposerEdit(
  current: string,
  event: Extract<TspEvent, { ev: 'edit' }>
): TernComposerSnapshot | null {
  if (event.len !== current.length) {
    return null
  }

  const from = clampOffset(event.from, current.length)
  const to = Math.max(from, clampOffset(event.to, current.length))
  const text = current.slice(0, from) + event.text + current.slice(to)

  return {
    cursor: clampOffset(event.cursor, text.length),
    text
  }
}

export function supportsTernComposer(hello: TspHello): boolean {
  const kinds = hello.kinds

  return (
    kinds.includes('col') &&
    kinds.includes('editor') &&
    HERMES_TSP_PROGRAM_FEATURES.includes('edit')
  )
}

export function resolveTernComposerSendable(_hello: TspHello, hermesReady: boolean): boolean {
  return hermesReady && HERMES_TSP_PROGRAM_FEATURES.includes('send')
}


export function supportsTernLiveSurface(hello: TspHello): boolean {
  return supportsTernComposer(hello) && hello.kinds.includes('md') && hello.kinds.includes('card') && hello.kinds.includes('agent')
}

export function ternSurfaceStaysOpen(state: { blocked: boolean }): boolean {
  return !state.blocked
}


export interface TernComposerInputState {
  snapshot: TernComposerSnapshot
  busy: boolean
  blocked: boolean
  completionCount: number
}

export interface TernComposerInputDeps {
  read: () => TernComposerInputState
  edit: (snapshot: TernComposerSnapshot) => void
  /** Clear the native snapshot synchronously before calling Hermes submission. */
  submit: (text: string) => void
}

/** The listener outlives React renders. Read current Hermes authority for each
 * event, including a modal opening before effect cleanup removes the listener. */
export function createTernComposerInputHandler(
  hello: TspHello,
  deps: TernComposerInputDeps
): (event: TspEvent) => void {
  return event => {
    if (!('sf' in event) || event.sf !== TERN_SURFACE_ID || !('id' in event) || event.id !== TERN_COMPOSER_ID) {
      return
    }

    if (event.ev !== 'edit' && event.ev !== 'send') {
      return
    }

    const state = deps.read()

    if (state.blocked) {
      return
    }

    if (event.ev === 'edit') {
      const next = applyTernComposerEdit(state.snapshot.text, event)

      if (next) {
        deps.edit(next)
      }

      return
    }

    const sendable = resolveTernComposerSendable(hello, !state.busy && state.completionCount === 0)

    if (sendable && event.text.trim() && event.text === state.snapshot.text) {
      deps.submit(event.text)
    }
  }
}

/**
 * First concrete TSP consumer. Hermes still owns the authoritative transcript
 * and composer state; this transport only projects the first prose-only slice
 * into one persistent Tern inline surface. Unsupported modal families still
 * close the surface and return to the proven Ink path.
 */
export class TernComposerTransport {
  private acked = 0
  private credits: number
  private cursor = 0
  private lastMain: readonly TernLiveNode[] = []
  private lastSendable = false
  private lastText = ''
  private limit: number
  private pending: { sendable: boolean; snapshot: TernComposerSnapshot; main: readonly TernLiveNode[] } | null = null
  private seq = 0
  private started = false

  constructor(
    private write: WriteTsp,
    hello: TspHello
  ) {
    this.credits = Math.max(1, Math.trunc(hello.credits ?? 2))
    this.limit = Math.max(4, Math.trunc(hello.apc ?? 65_536))
  }

  start(snapshot: TernComposerSnapshot, sendable: boolean, main?: readonly TernLiveNode[]): void {
    if (this.started) {
      return
    }

    const initialMain =
      main ?? [{ id: 'hermes:title', k: 'text', p: { text: 'Hermes' } }]

    this.started = true
    this.cursor = clampOffset(snapshot.cursor, snapshot.text.length)
    this.lastMain = initialMain
    this.lastSendable = sendable
    this.lastText = snapshot.text

    this.write(
      encodeTspJson(
        'o',
        {
          id: TERN_SURFACE_ID,
          mode: 'inline',
          role: 'hermes.session',
          title: 'Hermes'
        },
        this.limit
      )
    )

    this.sendOps([
      ['add', 'main', TERN_SURFACE_ID, null, { id: 'main', k: 'col', c: initialMain }],
      [
        'add',
        'dock',
        TERN_SURFACE_ID,
        null,
        {
          id: 'dock',
          k: 'col',
          c: [
            {
              id: TERN_COMPOSER_ID,
              k: 'editor',
              p: {
                cursor: this.cursor,
                maxLines: 12,
                role: 'hermes.composer',
                sendable,
                text: snapshot.text
              }
            }
          ]
        }
      ],
      ['add', 'layer', TERN_SURFACE_ID, null, { id: 'layer', k: 'col', c: [] }],
      ['focus', TERN_COMPOSER_ID]
    ])
  }

  update(snapshot: TernComposerSnapshot, sendable: boolean, main?: readonly TernLiveNode[]): void {
    if (!this.started) {
      return
    }

    const next = {
      cursor: clampOffset(snapshot.cursor, snapshot.text.length),
      text: snapshot.text
    }
    const nextMain = main ?? this.lastMain
    const mainOps = reconcileTernLiveNodes('main', this.lastMain, nextMain)
    const composerUnchanged =
      next.text === this.lastText && next.cursor === this.cursor && sendable === this.lastSendable

    if (composerUnchanged && mainOps.length === 0) {
      // The desired state has converged back to the most recently sent frame.
      // Drop any blocked intermediate update so a later ACK cannot resurrect it.
      this.pending = null
      return
    }

    if (this.seq - this.acked >= this.credits) {
      this.pending = { sendable, snapshot: next, main: nextMain }

      return
    }

    this.sendSurface(next, sendable, nextMain, mainOps)
  }

  handleEvent(event: TspEvent): void {
    if (event.ev !== 'ack' || event.sf !== TERN_SURFACE_ID) {
      return
    }

    // ACK sequence numbers are cumulative frame ids. Ignore malformed,
    // duplicate/stale, and future ACKs rather than clamping them into credit:
    // clamping a future ACK would release a frame the terminal never accepted,
    // and a fractional ACK must never create half a credit.
    if (!Number.isInteger(event.s) || event.s <= this.acked || event.s > this.seq) {
      return
    }

    this.acked = event.s

    if (this.pending && this.seq - this.acked < this.credits) {
      const pending = this.pending
      this.pending = null
      this.sendSurface(pending.snapshot, pending.sendable, pending.main)
    }
  }

  stop(): void {
    if (!this.started) {
      return
    }

    this.started = false
    this.pending = null
    this.write(encodeTspJson('x', { id: TERN_SURFACE_ID, keep: false }, this.limit))
  }

  private sendSurface(
    snapshot: TernComposerSnapshot,
    sendable: boolean,
    main: readonly TernLiveNode[],
    mainOps = reconcileTernLiveNodes('main', this.lastMain, main)
  ): void {
    const ops: unknown[] = [...mainOps]
    const composerChanged =
      snapshot.text !== this.lastText || snapshot.cursor !== this.cursor || sendable !== this.lastSendable

    if (composerChanged) {
      ops.push([
        'set',
        TERN_COMPOSER_ID,
        {
          cursor: snapshot.cursor,
          sendable,
          text: snapshot.text
        }
      ])
    }

    this.cursor = snapshot.cursor
    this.lastMain = main
    this.lastSendable = sendable
    this.lastText = snapshot.text

    if (ops.length) {
      this.sendOps(ops)
    }
  }

  private sendOps(ops: unknown[]): void {
    this.seq += 1
    this.write(
      encodeTspJson(
        'f',
        {
          ops,
          s: this.seq,
          sf: TERN_SURFACE_ID
        },
        this.limit
      )
    )
  }
}

export class TernInlineSession {
  private transport: TernComposerTransport | null = null

  constructor(
    private write: WriteTsp,
    private hello: TspHello
  ) {}

  sync(state: {
    blocked: boolean
    busy: boolean
    completionCount?: number
    snapshot: TernComposerSnapshot
    main?: readonly TernLiveNode[]
  }): void {
    if (state.blocked) {
      this.close()
      return
    }

    const sendable = resolveTernComposerSendable(this.hello, !state.busy && (state.completionCount ?? 0) === 0)

    if (!this.transport) {
      this.transport = new TernComposerTransport(this.write, this.hello)
      this.transport.start(state.snapshot, sendable, state.main)
      return
    }

    this.transport.update(state.snapshot, sendable, state.main)
  }

  handleEvent(event: TspEvent): void {
    this.transport?.handleEvent(event)
  }

  close(): void {
    this.transport?.stop()
    this.transport = null
  }
}

export function useTernComposerSurface(composer: AppLayoutComposerProps, transcript: AppLayoutTranscriptProps): void {
  const surface = useStore($ternSurface)
  const blocked = useStore($isBlocked)
  const { busy } = useStore($uiState)
  const streaming = useTurnSelector(state => state.streaming)
  const subagents = useTurnSelector(state => state.subagents)
  const main = useMemo(
    () => [...projectTernTranscript(transcript.virtualRows, streaming), ...projectTernSubagents(subagents)],
    [streaming, subagents, transcript.virtualRows]
  )
  const { stdout } = useStdout()
  const composerRef = useRef(composer)
  const cursorRef = useRef(composer.input.length)
  const mainRef = useRef(main)
  const nativeTextRef = useRef(composer.input)
  const sessionRef = useRef<TernInlineSession | null>(null)

  composerRef.current = composer
  mainRef.current = main

  useEffect(() => {
    if (
      !NATIVE_MODE ||
      blocked ||
      !stdout ||
      surface.status !== 'active' ||
      !supportsTernLiveSurface(surface.hello)
    ) {
      return
    }

    const hello = surface.hello

    if (!pauseRendering(stdout)) {
      return
    }

    stdout.write('\x1b[2J\x1b[H')

    nativeTextRef.current = composerRef.current.input
    cursorRef.current = composerRef.current.input.length

    const session = new TernInlineSession(data => {
      stdout.write(data)
    }, hello)

    sessionRef.current = session
    const readInputState = (): TernComposerInputState => ({
      blocked: $isBlocked.get(),
      busy: $uiState.get().busy,
      completionCount: composerRef.current.completions.length,
      snapshot: {
        cursor: cursorRef.current,
        text: nativeTextRef.current
      }
    })
    const syncCurrent = () => session.sync({ ...readInputState(), main: mainRef.current })

    syncCurrent()

    const handleInput = createTernComposerInputHandler(hello, {
      read: readInputState,
      edit: next => {
        nativeTextRef.current = next.text
        cursorRef.current = next.cursor
        composerRef.current.updateInput(next.text)
        syncCurrent()
      },
      submit: text => {
        // Invalidate the submitted snapshot before a second native send can land.
        nativeTextRef.current = ''
        cursorRef.current = 0
        syncCurrent()
        composerRef.current.submit(text)
      }
    })

    const unsubscribe = subscribeTernSurfaceEvents(event => {
      session.handleEvent(event)
      handleInput(event)
    })

    return () => {
      unsubscribe()
      session.close()
      sessionRef.current = null
      resumeRendering(stdout)
    }
  }, [blocked, stdout, surface])

  useEffect(() => {
    const session = sessionRef.current

    if (!session) {
      return
    }

    if (composer.input !== nativeTextRef.current) {
      nativeTextRef.current = composer.input
      cursorRef.current = composer.input.length
    }

    session.sync({
      blocked,
      busy,
      completionCount: composer.completions.length,
      snapshot: {
        cursor: cursorRef.current,
        text: nativeTextRef.current
      },
      main
    })
  }, [blocked, busy, composer.completions.length, composer.input, main, surface])
}
