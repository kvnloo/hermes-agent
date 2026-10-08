import { readFileSync, realpathSync, writeFileSync } from 'node:fs'
import { readdir, readFile } from 'node:fs/promises'
import { join, sep } from 'node:path'
import { defineTool } from 'e2e/agent'
import { z } from 'zod'
import type { NativeControl } from './adapter.ts'
import type { Manifest } from './types.ts'

const SENTINEL = 'isolated inert fixture; no turns or grants\n'
const INERT_CORRUPT = 'agent: [unterminated\n'
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
const ACTION_MS = 30_000

let capturedInert: string | undefined

function operation(options: object): {
  signal: AbortSignal
  timeoutMs: number
  runId: string
  attemptId: string
  origin: 'agent'
} {
  const timeoutMs = ACTION_MS
  const abortSignal = 'abortSignal' in options && options.abortSignal instanceof AbortSignal ? options.abortSignal : undefined
  const attemptId = 'toolCallId' in options && typeof options.toolCallId === 'string' ? options.toolCallId : 'mcp'
  return {
    signal: abortSignal ?? AbortSignal.timeout(timeoutMs),
    timeoutMs,
    runId: 'bugbash',
    attemptId,
    origin: 'agent',
  }
}

export function assertOwnedInert(manifest: Manifest): string {
  if (!manifest.runtime?.startsWith('/tmp/') || !manifest.display || manifest.display === 'wayland-0') {
    throw new Error('Owned isolated runtime/display is required; physical wayland-0 is refused.')
  }
  if (!manifest.proof.startsWith('/tmp/') || manifest.proof === '/tmp') {
    throw new Error('Proof directory must be a private /tmp path.')
  }
  const proof = realpathSync(manifest.proof)
  const home = realpathSync(manifest.home)
  if (home !== proof && !home.startsWith(`${proof}${sep}`)) {
    throw new Error('Hermes home is not inside the owned proof directory.')
  }
  const sentinel = readFileSync(join(home, '.native-settings-e2e'), 'utf8')
  if (sentinel !== SENTINEL) throw new Error('Owned inert sentinel is missing or not the native-settings fixture.')
  const yaml = realpathSync(join(home, 'config.yaml'))
  if (yaml !== home && !yaml.startsWith(`${home}${sep}`)) throw new Error('config.yaml is not inside the owned inert home.')
  return yaml
}

export function bugbashTools(native: NativeControl) {
  return {
    native_schema: defineTool(
      {
        description: 'Read the canonical native settings schema (field type and category) from the owned inert fixture. Read-only.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => JSON.stringify(await native.schema(operation(options))),
      },
      { mutates: false, platforms: ['desktop'] },
    ),
    native_settings: defineTool(
      {
        description: 'Read the last delivered settings.get result (fields, profile) from the owned gateway record. Read-only.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => JSON.stringify(await native.settings(operation(options))),
      },
      { mutates: false, platforms: ['desktop'] },
    ),
    native_prefs: defineTool(
      {
        description: 'Read the live Hermes settings prefs surface, or null when no Settings owner is open. Read-only.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => JSON.stringify((await native.prefs(operation(options))) ?? null),
      },
      { mutates: false, platforms: ['desktop'] },
    ),
    native_wire: defineTool(
      {
        description: 'Read the owned gateway JSONL (request/response/held/delivered/denied). Read-only. Never a grant.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => JSON.stringify(await native.wire(operation(options))),
      },
      { mutates: false, platforms: ['desktop'] },
    ),
    native_config_bytes: defineTool(
      {
        description: 'Read the owned inert profile config.yaml bytes after sentinel validation. Read-only.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => {
          assertOwnedInert(native.manifest)
          return JSON.stringify({ bytes: await native.configBytes(operation(options)) })
        },
      },
      { mutates: false, platforms: ['desktop'] },
    ),
    native_hold: defineTool(
      {
        description: 'Hold the next matching settings.get or settings.set gateway response until native_release. Mutates the owned response gate only.',
        inputSchema: z.object({
          method: z.enum(['settings.get', 'settings.set']),
          key: z.string().min(1).optional(),
        }).strict(),
        execute: async (input: { method: 'settings.get' | 'settings.set'; key?: string }, options: object) => {
          const token = await native.hold(input.method, input.key, operation(options))
          return JSON.stringify({ token, method: input.method, key: input.key ?? null })
        },
      },
      { mutates: true, platforms: ['desktop'] },
    ),
    native_release: defineTool(
      {
        description: 'Release a held gateway response by removing the owned response gate.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => {
          await native.release(operation(options))
          return JSON.stringify({ released: true })
        },
      },
      { mutates: true, platforms: ['desktop'] },
    ),
    native_evidence: defineTool(
      {
        description: 'Capture owned AX/tree JSON plus a HEADLESS-1 PNG via native.evidence, then accept only after gate+ownership postcheck. Returns private artifact paths. Not an MCP engine screenshot.',
        inputSchema: z.object({ label: z.string().min(1).max(80) }).strict(),
        execute: async (input: { label: string }, options: object) => {
          const ctx = operation(options)
          const dir = join(native.manifest.proof, 'observations')
          const before = new Set(await readdir(dir).catch(() => [] as string[]))
          await native.evidence(input.label, ctx)
          await native.snapshot(ctx)
          const created = (await readdir(dir)).filter((name) => !before.has(name))
          const jsonName = created.find((name) => name.endsWith('.json'))
          const pngName = created.find((name) => name.endsWith('.png'))
          if (!jsonName || !pngName) throw new Error('native.evidence pending files were not found after the owned postcheck.')
          const jsonPath = join(dir, jsonName)
          const pngPath = join(dir, pngName)
          JSON.parse(await readFile(jsonPath, 'utf8'))
          const png = await readFile(pngPath)
          if (png.length < PNG.length || !png.subarray(0, PNG.length).equals(PNG)) {
            throw new Error('native.evidence PNG failed the owned postcheck; not accepted.')
          }
          return JSON.stringify({ accepted: true, json: jsonPath, png: pngPath })
        },
      },
      { mutates: false, platforms: ['desktop'] },
    ),
    native_corrupt_inert: defineTool(
      {
        description: 'Capture the owned inert config.yaml bytes, then write the named unterminated-yaml fixture only. No caller path or content.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => {
          const yaml = assertOwnedInert(native.manifest)
          const ctx = operation(options)
          capturedInert = await native.configBytes(ctx)
          writeFileSync(yaml, INERT_CORRUPT, { mode: 0o600 })
          return JSON.stringify({ captured: true, bytes: capturedInert.length })
        },
      },
      { mutates: true, platforms: ['desktop'] },
    ),
    native_restore_inert: defineTool(
      {
        description: 'Restore the exact config.yaml bytes captured by native_corrupt_inert on this MCP process.',
        inputSchema: z.object({}).strict(),
        execute: async (_input: Record<string, never>, options: object) => {
          const yaml = assertOwnedInert(native.manifest)
          if (capturedInert === undefined) throw new Error('No captured inert bytes; call native_corrupt_inert first.')
          writeFileSync(yaml, capturedInert, { mode: 0o600 })
          const now = await native.configBytes(operation(options))
          if (now !== capturedInert) throw new Error('Restore did not match the captured inert bytes.')
          return JSON.stringify({ restored: true })
        },
      },
      { mutates: true, platforms: ['desktop'] },
    ),
  }
}
