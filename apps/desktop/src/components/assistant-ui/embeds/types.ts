import type { ReactNode } from 'react'

// Shared prop contract for fenced-block renderers (mermaid, svg). Kept in its
// own module so renderers and the registry can both import it without a cycle.
export interface RichFenceProps {
  code: string
  /** True while the surrounding message is still streaming. Renderers that can
   *  throw on partial input (e.g. mermaid) defer until this is false. */
  streaming?: boolean
  /** The original syntax-highlighted fence. OpenUI preserves it on disclosure
   *  and validation failure; other rich renderers can ignore it. */
  source?: ReactNode
}
