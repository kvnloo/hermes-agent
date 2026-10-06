// How the splash takes its colours. The designs speak in roles (paper, ink,
// shade, accent, dim, ray); nothing here or in the view holds a colour value.
// They arrive as a palette on the splash's own surface: the Hermes brand by
// default (the welcome screen is brand blue under any window theme), or a skin
// the user chose. With no palette at all, Tern's theme supplies every one.
//
//   * Inks are span tokens. Tern colours a span that names a token
//     (`{ s: 'accent' }`) from the surface's palette, else the active theme.
//   * Paper is the palette's own (`SPLASH_PAPER_TOKEN`), filled across the
//     pane; a palette without one leaves the pane itself as the paper.
//   * Shade and the inverted "ink" ground are stylesheet fills derived from
//     the paper and the foreground.
//   * Shadow ink (specks and shading darker than the paper) has no theme
//     token: no theme names a colour below its own page. It travels on the
//     `del` span class, which the splash stylesheet re-inks, inside the splash
//     only, from the paper.

/** Which Tern theme token inks each splash role. */
export interface SplashPalette {
  /** Highlight ink. */
  ink: string
  /** Sparing accent. */
  accent: string
  /** Secondary text. */
  dim: string
  /** Background engraving, fainter than `dim`. */
  ray: string
  /** Shadow ink, darker than the paper: a built-in span class the stylesheet re-inks. */
  shade: string
}

/** The splash on omp's theme tokens, which every Tern theme defines. */
export const TERN_SPLASH_PALETTE: SplashPalette = {
  accent: 'accent',
  dim: 'muted',
  ink: 'text',
  ray: 'dim',
  shade: 'del'
}

/**
 * The palette token a splash palette names its own paper with. It is one of
 * Tern's background tokens, which arrive as a translucent `--sf-status-bg`.
 */
export const SPLASH_PAPER_TOKEN = 'statusLineBg'

// The pane's background and foreground, as Tern's theme sets them.
const PANE = 'var(--tv-bg)'
const OWN_PAPER = 'rgb(from var(--sf-status-bg) r g b / 1)'
const INK_GROUND = 'var(--sf-p-text, var(--tv-fg))'

export const SPLASH_ROLE = 'hermes.splash'

/** The role of a segment: its ground, then the ground colour its base ink uses. */
export const segmentRole = (ground: string, base: string) => `${SPLASH_ROLE}.on-${ground}.in-${base}`

/** The stylesheet that turns segment roles into fills and inks. Rows are flush, cell-exact lines. */
export function splashStylesheet(palette: SplashPalette = TERN_SPLASH_PALETTE, ownPaper = false): string {
  // The paper: the splash palette's own (the Hermes brand blue), else the pane itself.
  const PAPER = ownPaper ? OWN_PAPER : PANE
  // Shadow: the paper pulled toward black (still "darker than the paper" on a light theme).
  const SHADE = `color-mix(in oklab, ${PAPER} 58%, black)`
  const fill: Record<string, string> = { ink: INK_GROUND, shade: SHADE }
  const segment = `[data-role^='${SPLASH_ROLE}.on-']`

  const rules = [
    // Surface text advances a hair less than a grid cell, so a full-width row
    // falls short of the pane: centre the block rather than leave a ragged edge.
    `[data-role='${SPLASH_ROLE}'] { align-items: center; }`,
    // Its own paper covers the whole pane, past the block's edges.
    ...(ownPaper ? [`[data-role='${SPLASH_ROLE}'] { background: ${PAPER}; box-shadow: 0 0 0 100vmax ${PAPER}; }`] : []),
    `[data-role='${SPLASH_ROLE}.row'] { align-items: stretch; flex-wrap: nowrap; }`,
    `[data-role='${SPLASH_ROLE}.row'] > * { flex: none; }`,
    // Ink is the pane's own text colour; a span that names a theme token overrides it.
    `${segment} { color: ${INK_GROUND}; }`,
    `${segment} .sf-t-${palette.shade} { color: ${SHADE}; text-decoration: none; }`
  ]

  for (const ground of ['none', 'paper', 'ink', 'shade']) {
    for (const base of ['none', 'paper']) {
      const decl = [fill[ground] ? `background: ${fill[ground]};` : '', base === 'paper' ? `color: ${PAPER};` : '']
        .filter(Boolean)
        .join(' ')

      if (decl) {
        rules.push(`[data-role='${segmentRole(ground, base)}'] { ${decl} }`)
      }
    }
  }

  return rules.join('\n')
}
