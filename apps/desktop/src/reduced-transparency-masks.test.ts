// @vitest-environment node
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const STYLES = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'styles.css'), 'utf8').replace(
  /\/\*[\s\S]*?\*\//g,
  ''
)

/** Read the contents of a CSS rule or media query using balanced braces. */
function blockAfter(css: string, prelude: string): string {
  const start = css.indexOf(prelude)
  expect(start, `Missing ${prelude}`).toBeGreaterThanOrEqual(0)

  const open = css.indexOf('{', start)
  let depth = 0

  for (let i = open; i < css.length; i += 1) {
    if (css[i] === '{') {
      depth += 1
    } else if (css[i] === '}' && --depth === 0) {
      return css.slice(open + 1, i)
    }
  }

  throw new Error(`Unclosed block: ${prelude}`)
}

describe('reduced transparency masks', () => {
  it('keeps structural arc cutouts while removing decorative element fades', () => {
    const media = blockAfter(STYLES, '@media (prefers-reduced-transparency: reduce)')
    const rules = [...media.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    const maskTargets = rules
      .filter(([, , body]) =>
        /(?:^|;)\s*mask-image:\s*none\s*!important;/.test(body) &&
        /(?:^|;)\s*-webkit-mask-image:\s*none\s*!important;/.test(body)
      )
      .map(([, selector]) => selector.trim().replace(/\s+/g, ' '))

    // The PR's original universal rule hid the hole in .arc-border and
    // in pseudo-element ring cutouts (Kanban and tour). These are not fades.
    expect(maskTargets).toEqual(['*:not(.arc-border)'])

    const arc = blockAfter(STYLES, '.arc-border {')
    expect(arc).toMatch(/\bmask:\s*linear-gradient\(/)
    expect(arc).toMatch(/\bmask-composite:\s*exclude;/)
  })
})
