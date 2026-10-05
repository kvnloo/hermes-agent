import { pauseRendering, resumeRendering, useStdout } from '@hermes/ink'
import { useStore } from '@nanostores/react'
import { useEffect, useRef } from 'react'

import type { AppLayoutComposerProps } from '../app/interfaces.js'
import { $isBlocked } from '../app/overlayStore.js'
import { $uiState } from '../app/uiStore.js'
import { NATIVE_MODE } from '../config/env.js'
import { encodeTspJson, HERMES_TSP_PROGRAM_FEATURES, type TspEvent, type TspHello } from './protocol.js'
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

export function ternSurfaceStaysOpen(state: { blocked: boolean }): boolean {
  return !state.blocked
}

/**
 * First concrete TSP consumer. The transcript intentionally remains Ink-owned:
 * while Hermes is idle this surface owns only the native composer; busy turns
 * and modal prompts close it and resume Ink immediately.
 */
export class TernComposerTransport {
  private acked = 0
  private credits: number
  private cursor = 0
  private lastSendable = false
  private lastText = ''
  private limit: number
  private pending: { sendable: boolean; snapshot: TernComposerSnapshot } | null = null
  private seq = 0
  private started = false

  constructor(
    private write: WriteTsp,
    hello: TspHello
  ) {
    this.credits = Math.max(1, Math.trunc(hello.credits ?? 2))
    this.limit = Math.max(4, Math.trunc(hello.apc ?? 65_536))
  }

  start(snapshot: TernComposerSnapshot, sendable: boolean): void {
    if (this.started) {
      return
    }

    this.started = true
    this.cursor = clampOffset(snapshot.cursor, snapshot.text.length)
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
      ['add', 'main', TERN_SURFACE_ID, null, { id: 'main', k: 'col', c: [{ id: 'hermes:title', k: 'text', p: { text: 'Hermes' } }] }],
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

  update(snapshot: TernComposerSnapshot, sendable: boolean): void {
    if (!this.started) {
      return
    }

    const next = {
      cursor: clampOffset(snapshot.cursor, snapshot.text.length),
      text: snapshot.text
    }

    if (next.text === this.lastText && next.cursor === this.cursor && sendable === this.lastSendable) {
      return
    }

    if (this.seq - this.acked >= this.credits) {
      this.pending = { sendable, snapshot: next }

      return
    }

    this.sendComposer(next, sendable)
  }

  handleEvent(event: TspEvent): void {
    if (event.ev !== 'ack' || event.sf !== TERN_SURFACE_ID) {
      return
    }

    this.acked = Math.max(this.acked, Math.min(event.s, this.seq))

    if (this.pending && this.seq - this.acked < this.credits) {
      const pending = this.pending
      this.pending = null
      this.sendComposer(pending.snapshot, pending.sendable)
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

  private sendComposer(snapshot: TernComposerSnapshot, sendable: boolean): void {
    this.cursor = snapshot.cursor
    this.lastSendable = sendable
    this.lastText = snapshot.text
    this.sendOps([
      [
        'set',
        TERN_COMPOSER_ID,
        {
          cursor: snapshot.cursor,
          sendable,
          text: snapshot.text
        }
      ]
    ])
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

export function useTernComposerSurface(composer: AppLayoutComposerProps): void {
  const surface = useStore($ternSurface)
  const blocked = useStore($isBlocked)
  const { busy } = useStore($uiState)
  const { stdout } = useStdout()
  const composerRef = useRef(composer)
  const cursorRef = useRef(composer.input.length)
  const nativeTextRef = useRef(composer.input)
  const transportRef = useRef<TernComposerTransport | null>(null)

  composerRef.current = composer

  useEffect(() => {
    if (
      !NATIVE_MODE ||
      blocked ||
      !stdout ||
      surface.status !== 'active' ||
      !supportsTernComposer(surface.hello)
    ) {
      return
    }

    const hello = surface.hello
    const sendable = resolveTernComposerSendable(hello, !busy)

    if (!pauseRendering(stdout)) {
      return
    }

    stdout.write('\x1b[2J\x1b[H')

    nativeTextRef.current = composerRef.current.input
    cursorRef.current = composerRef.current.input.length

    const transport = new TernComposerTransport(data => {
      stdout.write(data)
    }, hello)

    transportRef.current = transport
    transport.start(
      {
        cursor: cursorRef.current,
        text: nativeTextRef.current
      },
      sendable
    )

    const unsubscribe = subscribeTernSurfaceEvents(event => {
      transport.handleEvent(event)

      if (!('sf' in event) || event.sf !== TERN_SURFACE_ID || !('id' in event) || event.id !== TERN_COMPOSER_ID) {
        return
      }

      if (event.ev === 'edit') {
        const next = applyTernComposerEdit(nativeTextRef.current, event)

        if (!next) {
          return
        }

        nativeTextRef.current = next.text
        cursorRef.current = next.cursor
        composerRef.current.updateInput(next.text)
        transport.update(next, sendable)

        return
      }

      if (
        event.ev === 'send' &&
        sendable &&
        composerRef.current.completions.length === 0 &&
        event.text.trim() &&
        event.text === nativeTextRef.current
      ) {
        nativeTextRef.current = ''
        cursorRef.current = 0
        transport.update({ cursor: 0, text: '' }, sendable)
        composerRef.current.submit(event.text)
      }
    })

    return () => {
      unsubscribe()
      transport.stop()
      transportRef.current = null
      resumeRendering(stdout)
    }
  }, [blocked, stdout, surface])

  useEffect(() => {
    const transport = transportRef.current

    if (!transport) {
      return
    }

    if (composer.input !== nativeTextRef.current) {
      nativeTextRef.current = composer.input
      cursorRef.current = composer.input.length
    }

    const hello = surface.status === 'active' ? surface.hello : null
    transport.update(
      {
        cursor: cursorRef.current,
        text: nativeTextRef.current
      },
      resolveTernComposerSendable(hello ?? { r: 'hello', v: 1, term: 'tern', kinds: [] }, !busy)
    )
  }, [busy, composer.input, surface])
}
