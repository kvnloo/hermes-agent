// Builds the sandboxed document that draws ephemeral-ui cards. Kept apart from the model because
// the generated kit is large (~1.6 MiB): the renderer imports this module only when a board has cards.
import { EPHEMERAL_UI_HEAD, EPHEMERAL_UI_TAIL } from './ephemeral-ui-kit.generated'

export interface EphemeralDocumentCard {
  kind: string
  app: string
  input?: unknown
  options?: Partial<Record<string, string>>
}

export interface EphemeralDocumentConfig {
  /** Echoed on every message so the host can tell its own frame's messages apart. */
  channel: string
  scheme: 'light' | 'dark'
  palette: Record<string, string>
  cards: EphemeralDocumentCard[]
}

export function ephemeralCardsDocument(config: EphemeralDocumentConfig): string {
  // The config sits inside a <script>; escaping "<" keeps any string from closing it.
  return EPHEMERAL_UI_HEAD + JSON.stringify(config).replaceAll('<', '\\u003c') + EPHEMERAL_UI_TAIL
}
