// Launch splash (HERMES_TUI_SPLASH=0 to disable, =<design> to pick one). A thin
// Ink shell around the pure frame renderers in ../splash: it owns the clock, the
// skip key and the hand-off, and nothing about the picture.

import { RawAnsi, useInput, useStdout } from '@hermes/ink'
import { useEffect, useRef, useState } from 'react'

import {
  DEFAULT_SPLASH_DESIGN,
  renderSplashFrame,
  SPLASH_EXIT_MS,
  SPLASH_DESIGN_NAMES,
  SPLASH_INTRO_MS,
  SPLASH_TICK_MS,
  type SplashColor
} from '../splash/index.js'

// Never hold the app hostage: if the gateway hasn't reported in by now, hand
// over anyway and let the normal chrome show whatever went wrong.
const SPLASH_MAX_MS = 15_000

export const splashColorDepth = (env: NodeJS.ProcessEnv = process.env): SplashColor => {
  if (env.NO_COLOR) {
    return 'none'
  }

  return /truecolor|24bit/i.test(env.COLORTERM ?? '') ? 'truecolor' : '256'
}

/** Resolve a HERMES_TUI_SPLASH value to a design name. */
export const pickSplashDesign = (setting: string, random: () => number = Math.random): string => {
  if (setting === 'random') {
    return SPLASH_DESIGN_NAMES[Math.floor(random() * SPLASH_DESIGN_NAMES.length)]!
  }

  return SPLASH_DESIGN_NAMES.includes(setting) ? setting : DEFAULT_SPLASH_DESIGN
}

export interface LaunchSplashProps {
  /** True once startup work is finished; the splash plays out its intro, then leaves. */
  ready: boolean
  /** Live loader line. */
  status?: string
  onDone: () => void
  /** Which design to draw; unknown names fall back to the default. */
  design?: string
  /** Claim a keypress (return true) instead of letting it skip the splash. */
  onInput?: (input: string) => boolean
  now?: () => number
}

export function LaunchSplash({
  design,
  now = () => performance.now(),
  onDone,
  onInput,
  ready,
  status
}: LaunchSplashProps) {
  const { stdout } = useStdout()
  const startedAt = useRef(now())
  const exitAt = useRef<number | null>(null)
  const skipped = useRef(false)
  const done = useRef(false)
  const [, setTick] = useState(0)

  useInput(input => {
    if (!onInput?.(input)) {
      skipped.current = true
    }
  })

  useEffect(() => {
    const id = setInterval(() => {
      const t = now()
      const elapsed = t - startedAt.current

      if (
        exitAt.current === null &&
        (skipped.current || elapsed >= SPLASH_MAX_MS || (ready && elapsed >= SPLASH_INTRO_MS))
      ) {
        exitAt.current = t
      }

      if (exitAt.current !== null && t - exitAt.current >= SPLASH_EXIT_MS && !done.current) {
        done.current = true
        clearInterval(id)
        onDone()

        return
      }

      setTick(n => n + 1)
    }, SPLASH_TICK_MS)

    return () => clearInterval(id)
  }, [now, onDone, ready])

  const width = stdout?.columns ?? 80
  const t = now()

  const lines = renderSplashFrame({
    color: splashColorDepth(),
    design,
    elapsedMs: t - startedAt.current,
    exitMs: exitAt.current === null ? undefined : t - exitAt.current,
    height: stdout?.rows ?? 24,
    status,
    width
  })

  return <RawAnsi lines={lines} width={width} />
}
