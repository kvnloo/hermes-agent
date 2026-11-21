import { EPHEMERAL_UI_HEAD, EPHEMERAL_UI_TAIL } from './kit.generated'

export interface EphemeralCardConfig {
  channel: string
  scheme: 'light' | 'dark'
  palette: Record<string, string>
  card: { kind: string; app: string } & Record<string, string | null | undefined>
  pinned: boolean
}

/** One card's offline document. `<` is escaped so no config text can close the script element. */
export function ephemeralCardDocument(config: EphemeralCardConfig): string {
  return EPHEMERAL_UI_HEAD + JSON.stringify(config).replaceAll('<', '\\u003c') + EPHEMERAL_UI_TAIL
}
