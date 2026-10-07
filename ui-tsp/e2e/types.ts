export type Json = null | boolean | number | string | Json[] | { [key: string]: Json }
export interface Manifest {
  root: string; entry: string; python: string; control: string; pane: string; proof: string
  home: string; record: string; tsp: string; gate: string; launch: string; project: string
  runtime: string; display: string
}
export interface Field {
  type: string; category: string; description: string; value: Json; default: Json
  options?: string[]; nullable?: boolean; sensitive?: boolean
}
export interface SettingsResult { fields: Record<string, Field>; profile: string }
export interface Rpc {
  id?: string | number; method?: string; params?: Record<string, Json>
  result?: Json; error?: { code: number; message: string }
}
export interface Wire { time: number; dir: 'request' | 'response' | 'delivered' | 'held' | 'denied'; body: Rpc }
export interface TspNode { id: string; k: string; p?: Record<string, Json>; c?: TspNode[] }
export interface TspFrame {
  dir: string; verb: string
  body: { sf?: string; s?: number; id?: string; ev?: string; item?: string; value?: Json; ops?: Json[][] }
}
export interface Prefs {
  id: string
  p: { title?: string; page?: string; query?: string; cursor?: number; lead?: string; focus?: string
    editing?: { row: string; draft?: string; cursor?: number; option?: string }
    pages?: { id: string; label: string }[]
    sections?: { id: string; title: string; rows: { id: string; label: string; control: Record<string, Json>; hint?: string; warning?: string; changed?: boolean }[] }[] }
}
export function record(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) throw new Error('Expected a JSON object.')
  return value as Record<string, unknown>
}
export function flatten<T extends { children?: readonly T[] }>(nodes: readonly T[]): T[] {
  return nodes.flatMap(node => [node, ...flatten(node.children ?? [])])
}
