// Launch-splash registry. Every design is a pure function from a frame
// description to ANSI lines; pick one with `frame.design`.

import { type SplashFrame } from './canvas.js'
import { atlas } from './designs/atlas.js'
import { kerykeion } from './designs/kerykeion.js'
import { sigil } from './designs/sigil.js'
import { soul } from './designs/soul.js'
import { unleash } from './designs/unleash.js'
import { velocity } from './designs/velocity.js'
import { windows } from './designs/windows.js'

export * from './canvas.js'

export type SplashDesign = (frame: SplashFrame) => string[]

export const SPLASH_DESIGNS: Record<string, SplashDesign> = {
  kerykeion,
  sigil,
  velocity,
  atlas,
  windows,
  unleash,
  soul
}

export const SPLASH_DESIGN_NAMES = Object.keys(SPLASH_DESIGNS)
export const DEFAULT_SPLASH_DESIGN = 'kerykeion'

/** Render one frame as `height` ANSI lines, each exactly `width` cells wide. */
export function renderSplashFrame(frame: SplashFrame): string[] {
  const safe = { ...frame, height: Math.max(1, Math.floor(frame.height)), width: Math.max(1, Math.floor(frame.width)) }

  return (SPLASH_DESIGNS[frame.design ?? ''] ?? kerykeion)(safe)
}
