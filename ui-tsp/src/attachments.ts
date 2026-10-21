// Composer-only upload projection. Hermes owns staging; confirmed paths are its attachment identities.
import { createHash } from 'node:crypto'
import { constants, existsSync } from 'node:fs'
import { open } from 'node:fs/promises'
import { basename, extname, isAbsolute } from 'node:path'
import { fileURLToPath } from 'node:url'

import type { AttachedImageResult, FileAttachResult, ImageDetachResult } from '@hermes/shared/gateway-events'
import type { JsonObject } from '@stencil-hq/tern'
import type { GatewayClient } from '@tui/gatewayClient.js'

import { readImageBytes } from './media-delivery.js'

const MAX_BYTES = 20 * 1024 * 1024

interface ImageFileSource {
  path: string
  name: string
  host?: 'frontend' | 'gateway' | 'tern'
}

interface ImageDataSource {
  data: string
  name: string
}

type ImageSource = ImageDataSource | ImageFileSource

interface AttachmentBase {
  id: string
  name: string
  mime: string
  bytes: number
  source: ImageSource
  session: string
  generation: number
  fingerprint?: string
}

export type Attachment = AttachmentBase & (
  | { status: 'pending' }
  | { status: 'attached'; path: string }
  | { status: 'failed'; error: string; path?: string }
)

export interface SubmittedImage {
  id: string
  name: string
  path: string
  mime: string
  bytes: number
}

/** Gateway's persisted @image directives keep their original durable path identity on resume. */
export function resumedImages(text: string): { text: string; images: SubmittedImage[] } {
  const lines = text.split('\n')
  const images: SubmittedImage[] = []

  while (lines.length) {
    const match = /^@image:(?:`([^`]+)`|"([^"]+)"|'([^']+)'|(\S+))$/.exec(lines.at(-1) ?? '')
    const path = match?.slice(1).find(Boolean)

    if (!path || !isAbsolute(path)) { break }
    images.unshift({ id: path, path, name: basename(path), mime: '', bytes: 0 })
    lines.pop()
  }

  return { text: lines.join('\n').trimEnd(), images }
}

/** Extensions never establish image-ness, including a misleading .png filename. */
export function imageMime(bytes: Uint8Array): string | undefined {
  const b = Buffer.from(bytes)

  const signatures: [string, Buffer][] = [
    ['image/png', Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])],
    ['image/jpeg', Buffer.from([255, 216, 255])],
    ['image/gif', Buffer.from('GIF87a')],
    ['image/gif', Buffer.from('GIF89a')],
    ['image/bmp', Buffer.from('BM')],
    ['image/tiff', Buffer.from([73, 73, 42, 0])],
    ['image/tiff', Buffer.from([77, 77, 0, 42])]
  ]

  if (b.subarray(0, 4).toString() === 'RIFF' && b.subarray(8, 12).toString() === 'WEBP') {
    return 'image/webp'
  }

  return signatures.find(([, signature]) => b.subarray(0, signature.length).equals(signature))?.[0]
}

/** Tern's current drop transport is a bracketed paste of a quoted path / file URI. */
export function pastedImageSource(text: string, mustExist = true): ImageSource | undefined {
  const data = /^data:image\/[a-z0-9.+-]+;base64,[a-z0-9+/=\s]+$/i.test(text) ? text : undefined

  if (data) {
    return { data, name: 'Pasted image' }
  }

  let path = text.trim()

  if (/^(["']).*\1$/s.test(path)) {
    path = path.slice(1, -1)
  }

  if (path.startsWith('file://')) {
    try {
      path = fileURLToPath(path)
    } catch {
      return undefined
    }
  }

  path = path.replace(/\\ /g, ' ')

  return isAbsolute(path) && (!mustExist || existsSync(path)) && !/[\r\n\0]/.test(path) ? { path, name: basename(path) } : undefined
}

/** Parse a terminal multi-file drop without evaluating shell syntax. All-or-none preserves ordinary prose. */
export function pastedImageSources(text: string, mustExist = true): ImageSource[] {
  const single = pastedImageSource(text, mustExist)

  if (single && (mustExist || 'data' in single || !/[\s"']/.test(text.trim()))) { return [single] }
  const paths: string[] = []
  let token = ''
  let quote = ''
  let escaped = false

  for (const char of text.trim()) {
    if (escaped) { token += char; escaped = false }
    else if (char === '\\' && quote !== "'") { escaped = true }
    else if (quote) { if (char === quote) { quote = '' } else { token += char } }
    else if (char === '"' || char === "'") { quote = char }
    else if (/\s/.test(char)) { if (token) { paths.push(token); token = '' } }
    else { token += char }
  }

  if (escaped || quote) { return [] }

  if (token) { paths.push(token) }
  const sources = paths.map(path => pastedImageSource(path, mustExist))

  return sources.length && sources.every(source => source !== undefined) ? sources : []
}

/** Newer peers' events remain `unknown` in SDK 0.1.0: validate the raw boundary. */
export function eventImageSource(raw: JsonObject): ImageSource | undefined {
  if (raw.ev !== 'paste' && raw.ev !== 'drop') {
    return undefined
  }

  if (typeof raw.path === 'string') {
    const source = pastedImageSource(raw.path, false)

    return source && 'path' in source ? { ...source, host: 'tern' } : source
  }

  const data = typeof raw.data === 'string' ? raw.data : undefined
  const mime = typeof raw.mime === 'string' ? raw.mime : ''

  if (data && (data.startsWith('data:image/') || mime.startsWith('image/'))) {
    return { data: data.startsWith('data:') ? data : `data:${mime};base64,${data}`, name: typeof raw.name === 'string' ? raw.name : 'Pasted image' }
  }

  return undefined
}

export class Attachments {
  readonly items: Attachment[] = []
  #serial = 0
  #generation = 0
  #removing = new Set<string>()
  #inflight = new Set<Attachment>()

  constructor(readonly gw: GatewayClient, readonly changed: () => void, readonly notice: (message: string) => void, readonly referenceOnly = false, readonly ternLocal: () => boolean = () => true) {}

  get blocked(): boolean {
    return this.#removing.size > 0 || this.items.some(item => item.status !== 'attached')
  }

  add(source: ImageSource, session: string): Promise<void> {
    const retained = [...new Set([...this.items, ...this.#inflight])].reduce((size, item) => size + ('data' in item.source ? item.source.data.length : 0), 0)

    if (this.items.length >= 8 || this.#inflight.size >= 8 || ('data' in source && retained + source.data.length > Math.ceil(MAX_BYTES * 2 / 3) * 4)) {
      this.notice('Composer attachment budget reached (8 images / 40 MiB). Remove an image first.')

      return Promise.resolve()
    }

    const fingerprint = createHash('sha256').update('data' in source ? source.data : `${source.host}:${source.path}`).digest('hex')
    const duplicate = this.items.some(item => item.session === session && item.fingerprint === fingerprint)

    if (duplicate) {
      this.notice(`${source.name} is already in the composer. Retry its chip if it failed.`)

      return Promise.resolve()
    }

    const item: Attachment = { id: `a${++this.#serial}`, name: source.name, mime: '', bytes: 0, source, session, generation: this.#generation, fingerprint, status: 'pending' }
    this.items.push(item)
    this.changed()

    return this.#attach(item)
  }

  async #attach(item: Attachment): Promise<void> {
    if (this.#inflight.size >= 8) {
      const index = this.items.indexOf(item)

      if (index >= 0) { this.items[index] = { ...item, status: 'failed', error: 'Attachment uploads are busy; retry after they finish.' } }
      this.changed()

      return
    }

    this.#inflight.add(item)

    try {
      const source = item.source
      let data: Buffer
      let localPath = 'path' in source ? source.path : undefined

      if ('path' in source) {
        if (source.host === 'gateway') { throw new Error('Gateway attachment is stale; remove it and attach the original again.') }

        if (source.host === 'tern' && !this.ternLocal()) { throw new Error('Dropped path belongs to the Tern host. Paste image bytes across SSH instead.') }
        const file = await open(source.path, constants.O_RDONLY | constants.O_NONBLOCK | (constants.O_NOFOLLOW ?? 0))

        try {
          const stat = await file.stat()

          if (!stat.isFile() || stat.size > MAX_BYTES) {
            throw new Error('Image must be a file no larger than 20 MiB.')
          }

          // Read only a header for local files; the existing gateway RPC owns the full image.
          data = Buffer.alloc(Math.min(32, stat.size))
          await file.read(data, 0, data.length, 0)
          item.bytes = stat.size

          // The path RPC rejects unknown suffixes. Upload verified bytes under their real format instead.
          if (this.gw.attached || !['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff'].includes(extname(source.path).toLowerCase())) {
            data = await readImageBytes(source.path, MAX_BYTES)
            localPath = undefined
          }
        } finally {
          await file.close()
        }
      } else {
        const payload = source.data.split(',')[1]?.replace(/\s/g, '') ?? ''

        if (!payload || payload.length > Math.ceil(MAX_BYTES / 3) * 4 || !/^[a-z0-9+/]*={0,2}$/i.test(payload)) {
          throw new Error('Invalid image data or image exceeds 20 MiB.')
        }

        data = Buffer.from(payload, 'base64')
        item.bytes = data.length
      }

      const mime = imageMime(data)

      if (!mime) {
        throw new Error('Not a supported image (magic bytes did not match).')
      }

      if ('data' in source) {
        const declared = /^data:([^;]+);/.exec(source.data)?.[1]

        if (declared && declared !== mime) { throw new Error('Image MIME does not match magic bytes.') }
      }

      const suffixMimes: Record<string, string> = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp', '.tif': 'image/tiff', '.tiff': 'image/tiff' }

      if (localPath && suffixMimes[extname(localPath).toLowerCase()] !== mime) {
        data = await readImageBytes(localPath, MAX_BYTES)
        localPath = undefined
      }

      item.mime = mime

      // Removal during local sniffing must never start a gateway upload.
      if (!this.items.includes(item)) {
        return
      }

      // Ask notes use workspace references, never the next user turn's image queue.
      const result = this.referenceOnly
        ? await this.gw.request<FileAttachResult>('file.attach', {
          ...(localPath ? { path: localPath } : { data_url: `data:${mime};base64,${data.toString('base64')}`, name: `note.${mime.split('/')[1]}` }),
          session_id: item.session
        })
        : localPath
        ? await this.gw.request<AttachedImageResult>('image.attach', { path: localPath, session_id: item.session })
        : await this.gw.request<AttachedImageResult>('image.attach_bytes', {
          content_base64: data.toString('base64'), filename: `pasted.${mime.split('/')[1] === 'jpeg' ? 'jpg' : mime.split('/')[1]}`, session_id: item.session
        })

      if (!result.attached || !result.path) {
        throw new Error(('message' in result && result.message) || 'Gateway did not confirm an attachment path.')
      }

      const attached: Attachment = { ...item, source: { path: result.path, name: item.name, host: 'gateway' }, status: 'attached', path: result.path }
      const index = this.items.indexOf(item)

      if (index < 0) {
        await this.#detach(attached)
      } else {
        this.items[index] = attached
      }
    } catch (error) {
      const index = this.items.indexOf(item)

      if (index >= 0) {
        this.items[index] = { ...item, status: 'failed', error: error instanceof Error ? error.message : String(error) }
      }
    } finally {
      this.#inflight.delete(item)
    }

    this.changed()
  }

  retry(id: string): void {
    const index = this.items.findIndex(item => item.id === id)
    const item = this.items[index]

    if (item?.status !== 'failed') {
      return
    }

    if (item.path) {
      void this.remove(id)

      return
    }

    const pending: Attachment = { ...item, status: 'pending' }
    this.items[index] = pending
    this.changed()
    void this.#attach(pending)
  }

  async #detach(item: Attachment & { path: string }): Promise<void> {
    // file.attach stores durable workspace refs, not disposable queued images.
    if (this.referenceOnly) {
      return
    }

    this.#removing.add(item.id)

    try {
      await this.gw.request<ImageDetachResult>('image.detach', { path: item.path, session_id: item.session })
    } catch (error) {
      // Keep the gateway identity visible and block submission until removal succeeds.
      const message = `Could not remove image: ${error instanceof Error ? error.message : String(error)}`

      if (item.generation === this.#generation) {
        this.items.push({ ...item, status: 'failed', error: message })
      } else {
        this.notice(`${item.name}: ${message}`)
      }
    } finally {
      this.#removing.delete(item.id)
      this.changed()
    }
  }

  async remove(id: string): Promise<void> {
    const index = this.items.findIndex(item => item.id === id)
    const item = this.items[index]

    if (!item) {
      return
    }

    this.items.splice(index, 1)

    if ('path' in item && item.path) {
      await this.#detach({ ...item, path: item.path })
    }

    this.changed()
  }

  snapshot(session: string): SubmittedImage[] {
    return this.items.flatMap(item => item.status === 'attached' && item.session === session
      ? [{ id: item.path, name: item.name, path: item.path, mime: item.mime, bytes: item.bytes }]
      : [])
  }

  take(session: string): SubmittedImage[] {
    const images = this.snapshot(session)
    const paths = new Set(images.map(image => image.path))

    for (let i = this.items.length - 1; i >= 0; i--) {
      const item = this.items[i]

      if (item?.status === 'attached' && item.session === session && paths.has(item.path)) {
        this.items.splice(i, 1)
      }
    }

    this.changed()

    return images
  }

  restore(images: readonly SubmittedImage[], session: string): void {
    for (const image of images) {
      if (!this.items.some(item => item.status === 'attached' && item.path === image.path && item.session === session)) {
        this.items.push({ ...image, id: `a${++this.#serial}`, source: { path: image.path, name: image.name, host: 'gateway' }, session, generation: this.#generation, status: 'attached' })
      }
    }

    this.changed()
  }

  clear(): void {
    this.#generation++
    this.#removing.clear()

    for (const item of [...this.items]) {
      void this.remove(item.id)
    }
  }
}
