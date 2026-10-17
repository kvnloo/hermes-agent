// The launch splash as Tern nodes: one flush `row` per terminal line, one
// `text` per ground segment. Box drawing and braille stay cell text; inks are
// span tokens that name palette tokens; grounds and base inks are roles the
// splash stylesheet (`../splash/theme.ts`) paints from the palette. Nothing
// here knows a colour.

import type { Node } from '@stencil-hq/tern'

import { segmentRole, SPLASH_ROLE, type SplashCells, type SplashSegment } from '../splash/index.js'

const segmentNode = (seg: SplashSegment, key: number) => (
  <text
    key={key}
    role={segmentRole(seg.ground, seg.base)}
    spans={seg.spans.map(sp => (sp.s ? { s: sp.s, t: sp.t } : sp.t))}
    wrap="none"
  />
)

/** One frame of the splash. */
export function splashNode(cells: SplashCells): Node {
  return (
    <col gap="none" key="splash" role={SPLASH_ROLE}>
      {cells.map((row, y) => (
        <row gap="none" key={y} role={`${SPLASH_ROLE}.row`}>
          {row.map(segmentNode)}
        </row>
      ))}
    </col>
  ) as Node
}
