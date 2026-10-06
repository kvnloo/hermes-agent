// How the splash's six colours reach Tern. The designs speak in roles
// (paper, ink, shade, accent, dim, ray); this module names the program-palette
// token that carries each one and writes the stylesheet that paints grounds
// from them. No colour value appears here or in the view: a skin change sends
// a new palette (`surface.palette`) and the splash recolours on its own.
//
// Tern treats palette tokens two ways (surface `palette.rs`):
//   * foreground tokens colour a span that names them (`{ s: 'accent' }`);
//     Tern may lift them for contrast against the pane;
//   * a fixed set of `…Bg` tokens are fills, exposed to stylesheets as
//     `--sf-tint-*` / `--sf-mark-bg` at reduced alpha and never lifted.
// So inks travel as span tokens and grounds as fill tokens, and a ground
// colour used as ink (navy specks on blue, blue type on a white card) is the
// segment's base ink, set from the same fill variable.

/** Which Tern palette token carries each splash colour. */
export interface SplashPalette {
  /** Highlight ink: a foreground token. Also the ground of inverted panels. */
  ink: string
  /** Sparing accent: a foreground token. */
  accent: string
  /** Secondary text: a foreground token. */
  dim: string
  /** Background engraving, between paper and ink: a foreground token. */
  ray: string
  /** The field the scene is printed on: a fill token. */
  paper: string
  /** Shadow, darker than the paper: a fill token. */
  shade: string
}

/**
 * The splash on the tokens `paletteOf` already sends for the chrome
 * (`../palette.ts`), so the two share one set of colours.
 */
export const TERN_SPLASH_PALETTE: SplashPalette = {
  accent: 'accent',
  dim: 'dim',
  ink: 'text',
  paper: 'userMessageBg',
  ray: 'border',
  shade: 'selectedBg'
}

// Tern's fill tokens and the CSS variable each one lands in.
const FILL_VARS: Record<string, string> = {
  cardBg: '--sf-tint-neutral',
  customMessageBg: '--sf-tint-custom',
  infoBg: '--sf-tint-info',
  selectedBg: '--sf-mark-bg',
  statusLineBg: '--sf-status-bg',
  toolErrorBg: '--sf-tint-error',
  toolPendingBg: '--sf-tint-pending',
  toolSuccessBg: '--sf-tint-success',
  userMessageBg: '--sf-tint-user'
}

/** The opaque CSS colour of palette token `token`. */
const colorOf = (token: string) => `rgb(from var(${FILL_VARS[token] ?? `--sf-p-${token}`}) r g b / 1)`

export const SPLASH_ROLE = 'hermes.splash'

/** The role of a segment: its ground, then the ground colour its base ink uses. */
export const segmentRole = (ground: string, base: string) => `${SPLASH_ROLE}.on-${ground}.in-${base}`

/**
 * The stylesheet that turns segment roles into fills and base inks, for the
 * tokens `palette` names. Geometry: rows are flush, cell-exact lines.
 */
export function splashStylesheet(palette: SplashPalette = TERN_SPLASH_PALETTE): string {
  const fill = { ink: colorOf(palette.ink), paper: colorOf(palette.paper), shade: colorOf(palette.shade) }

  const rules = [
    // Surface text advances a hair less than a grid cell, so a full-width row
    // falls short of the pane: centre the block rather than leave a ragged edge.
    `[data-role='${SPLASH_ROLE}'] { align-items: center; }`,
    `[data-role='${SPLASH_ROLE}.row'] { align-items: stretch; flex-wrap: nowrap; }`,
    `[data-role='${SPLASH_ROLE}.row'] > * { flex: none; }`
  ]

  for (const ground of ['none', 'paper', 'ink', 'shade'] as const) {
    for (const base of ['none', 'paper', 'shade'] as const) {
      const decl = [
        ground === 'none' ? '' : `background: ${fill[ground]};`,
        base === 'none' ? '' : `color: ${fill[base]};`
      ]
        .filter(Boolean)
        .join(' ')

      if (decl) {
        rules.push(`[data-role='${segmentRole(ground, base)}'] { ${decl} }`)
      }
    }
  }

  return rules.join('\n')
}
