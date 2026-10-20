// SDK-owned blob encoding/deduplication; this cache owns metadata, never image bytes.
import { constants } from 'node:fs'
import { open } from 'node:fs/promises'

import { node, type Node, type Session } from '@stencil-hq/tern'
import type { GatewayClient } from '@tui/gatewayClient.js'

import { imageMime } from './attachments.js'
import { ActionButton } from './view/action-button.js'

export const MEDIA_MAX_BYTES = 16 * 1024 * 1024
export const MEDIA_CACHE_ENTRIES = 32
export const MEDIA_CONNECTION_BYTES = 64 * 1024 * 1024
export const MEDIA_CONNECTION_BLOBS = 64

export interface MediaPath {
  kind: 'path'
  /** A path is meaningful only on its named host. */
  host: 'tern' | 'frontend' | 'gateway' | 'compute'
  path: string
  id: string
  mime?: string
  toolCallId?: string
}

export interface MediaBlob {
  kind: 'blob'
  id: string
  mime: string
}

export type MediaSource = MediaPath | MediaBlob
export type MediaPreview = (source: MediaPath, native: boolean) => Node | undefined

interface CachedImage {
  source: MediaPath
  status: 'loading' | 'ready' | 'failed'
  blob?: MediaBlob
  error?: string
}

/** Only the frontend's regular files are read here, bounded even if they grow after stat. */
export async function readImageBytes(path: string, maxBytes = MEDIA_MAX_BYTES): Promise<Buffer> {
  const file = await open(path, constants.O_RDONLY | constants.O_NONBLOCK | (constants.O_NOFOLLOW ?? 0))

  try {
    const stat = await file.stat()

    if (!stat.isFile() || stat.size > maxBytes) {
      throw new Error(`Image must be a regular file no larger than ${maxBytes / (1024 * 1024)} MiB.`)
    }

    const data = Buffer.alloc(Math.min(stat.size + 1, maxBytes + 1))
    let size = 0

    while (size < data.length) {
      const { bytesRead } = await file.read(data, size, data.length - size, null)

      if (!bytesRead) { break }
      size += bytesRead
    }

    // A concurrent in-place truncation must not upload a valid header with a missing tail.
    // Growth was already rejected above by the sentinel byte / size cap.
    if (size !== stat.size || size > maxBytes) { throw new Error('Image changed while reading; retry.') }

    return data.subarray(0, size)
  } finally {
    await file.close()
  }
}

export function imageBytesMime(data: Uint8Array, reported?: string): string {
  const mime = imageMime(data)
  const declared = reported?.split(';')[0]?.trim().toLowerCase()

  if (!mime || (declared && declared !== 'application/octet-stream' && declared !== mime)) {
    throw new Error('Unsupported image or MIME/magic-byte mismatch.')
  }

  return mime
}

/** No idle timers, no auto-retry, and at most one image transfer in flight. */
export class MediaDelivery {
  readonly #cache = new Map<string, CachedImage>()
  #busy = false
  #epoch = 0
  #closed = false
  #bytes = 0
  #uploads = 0
  revision = 0

  constructor(readonly tern: Session, readonly gw: GatewayClient, readonly session: () => string | null, readonly changed: () => void) {}

  preview(source: MediaPath): Node {
    const key = this.#key(source)
    const cached = this.#cache.get(key)

    if (cached?.blob) {
      return node('image', { key: 'media', blob: cached.blob.id, alt: source.path })
    }

    const supported = this.tern.caps.features.includes('blobs') && source.host !== 'compute' && source.host !== 'tern'
    const exhausted = this.#uploads >= MEDIA_CONNECTION_BLOBS || this.#bytes >= MEDIA_CONNECTION_BYTES

    const text = !supported ? 'Remote preview unavailable: image blobs or readable source host not supported.'
      : exhausted ? 'Preview connection budget reached; reconnect to load more images.'
        : cached?.status === 'loading' ? 'Loading image preview…'
          : cached?.error ? `${cached.error} Retry preview` : 'Load image preview'

    const session = this.session()
    const epoch = this.#epoch

    return ActionButton({ key: 'media', role: 'omp.media.notice', text, wrap: 'word',
      ...(!this.#closed && supported && !exhausted && cached?.status !== 'loading' ? { onClick: () => { if (session === this.session() && epoch === this.#epoch) { return this.load(source) } } } : {}) })
  }

  async load(source: MediaPath): Promise<void> {
    if (this.#closed || this.#busy || !this.tern.caps.features.includes('blobs') || source.host === 'compute' || source.host === 'tern') { return }
    const session = this.session()

    if (!session) { return }
    const key = this.#key(source)

    if (this.#cache.get(key)?.status === 'ready') { return }
    const epoch = this.#epoch
    const entry: CachedImage = { source, status: 'loading' }
    this.#cache.delete(key)

    while (this.#cache.size >= MEDIA_CACHE_ENTRIES) { this.#cache.delete(this.#cache.keys().next().value!) }
    this.#cache.set(key, entry)
    this.#busy = true
    this.#touch()

    try {
      let data: Buffer
      let reported = source.mime

      if (source.host === 'gateway') {
        const result = await this.gw.request<{ content_base64: string; mime: string; bytes: number }>('media.image', {
          session_id: session, path: source.path, ...(source.toolCallId ? { tool_call_id: source.toolCallId } : {})
        })

        if (typeof result.content_base64 !== 'string' || result.content_base64.length > Math.ceil(MEDIA_MAX_BYTES / 3) * 4 || !/^[a-z0-9+/]*={0,2}$/i.test(result.content_base64)) {
          throw new Error('Invalid or oversized gateway image.')
        }

        data = Buffer.from(result.content_base64, 'base64')

        if (result.bytes !== data.length) { throw new Error('Incomplete gateway image.') }
        reported = result.mime
        imageBytesMime(data, source.mime)
      } else {
        data = await readImageBytes(source.path)
      }

      const mime = imageBytesMime(data, reported)

      if (data.length > MEDIA_MAX_BYTES || this.#bytes + data.length > MEDIA_CONNECTION_BYTES || this.#uploads >= MEDIA_CONNECTION_BLOBS) {
        throw new Error('Preview connection budget reached; reconnect to load more images.')
      }

      // Removal, session adoption, and quit invalidate late reads before they can upload.
      if (this.#closed || epoch !== this.#epoch || session !== this.session() || this.#cache.get(key) !== entry) { return }
      const id = this.tern.blob(data, mime)
      this.#bytes += data.length
      this.#uploads++
      entry.status = 'ready'
      entry.blob = { kind: 'blob', id, mime }
    } catch (error) {
      if (this.#cache.get(key) === entry) {
        entry.status = 'failed'
        entry.error = error instanceof Error ? error.message : String(error)
      }
    } finally {
      this.#busy = false
      this.#touch()
    }
  }

  forget(source: MediaPath): void {
    this.#cache.delete(this.#key(source))
    this.#touch()
  }

  clear(close = false): void {
    this.#epoch++
    this.#closed ||= close
    this.#cache.clear()
    // SDK 0.1 has no blob release API. Its connection-scoped ID set is bounded
    // by these cumulative budgets, NOT reset when a session/view is cleared.
    this.#touch()
  }

  #key(source: MediaPath): string {
    return JSON.stringify([this.session(), source.host, source.id, source.path, source.mime, source.toolCallId])
  }

  #touch(): void {
    if (this.#closed) { return }
    this.revision++
    this.changed()
  }
}

/** SSH places the frontend on a different machine from Tern, even with stdio gateway. */
export function ternSharesFrontendHost(env: NodeJS.ProcessEnv = process.env): boolean {
  return !env.SSH_CONNECTION && !env.SSH_CLIENT && !env.SSH_TTY
}
