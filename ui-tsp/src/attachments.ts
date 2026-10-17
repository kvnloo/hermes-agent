// Composer-only upload projection. Hermes owns staging; confirmed paths are its attachment identities.
import { existsSync } from 'node:fs'
import { open } from 'node:fs/promises'
import { basename, extname, isAbsolute } from 'node:path'
import { fileURLToPath } from 'node:url'

import type { AttachedImageResult, ImageDetachResult } from '@hermes/shared/gateway-events'
import type { JsonObject } from '@stencil-hq/tern'
import type { GatewayClient } from '@tui/gatewayClient.js'

const MAX_BYTES = 20 * 1024 * 1024

interface ImageFileSource {
  path: string
  name: string
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

/** Newer peers' events remain `unknown` in SDK 0.1.0: validate the raw boundary. */
export function eventImageSource(raw: JsonObject): ImageSource | undefined {
  if (raw.ev !== 'paste' && raw.ev !== 'drop') {
    return undefined
  }

  if (typeof raw.path === 'string') {
    return pastedImageSource(raw.path, false)
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

  constructor(readonly gw: GatewayClient, readonly changed: () => void, readonly notice: (message: string) => void) {}

  get blocked(): boolean {
    return this.#removing.size > 0 || this.items.some(item => item.status !== 'attached')
  }

  add(source: ImageSource, session: string): Promise<void> {
    const duplicate = this.items.some(item => item.session === session && (
      ('path' in source && 'path' in item.source && source.path === item.source.path) ||
      ('data' in source && 'data' in item.source && source.data === item.source.data)
    ))

    if (duplicate) {
      this.notice(`${source.name} is already in the composer. Retry its chip if it failed.`)

      return Promise.resolve()
    }

    const item: Attachment = { id: `a${++this.#serial}`, name: source.name, mime: '', bytes: 0, source, session, generation: this.#generation, status: 'pending' }
    this.items.push(item)
    this.changed()

    return this.#attach(item)
  }

  async #attach(item: Attachment): Promise<void> {
    try {
      const source = item.source
      let data: Buffer
      let localPath = 'path' in source ? source.path : undefined

      if ('path' in source) {
        const file = await open(source.path, 'r')

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
          if (!['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff'].includes(extname(source.path).toLowerCase())) {
            data = await file.readFile()
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

      item.mime = mime

      // Removal during local sniffing must never start a gateway upload.
      if (!this.items.includes(item)) {
        return
      }

      const result = localPath
        ? await this.gw.request<AttachedImageResult>('image.attach', { path: localPath, session_id: item.session })
        : await this.gw.request<AttachedImageResult>('image.attach_bytes', {
          content_base64: data.toString('base64'), filename: `pasted.${mime.split('/')[1] === 'jpeg' ? 'jpg' : mime.split('/')[1]}`, session_id: item.session
        })

      if (!result.attached || !result.path) {
        throw new Error(result.message || 'Gateway did not confirm an attachment path.')
      }

      const attached: Attachment = { ...item, status: 'attached', path: result.path }
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
        this.items.push({ ...image, id: `a${++this.#serial}`, source: { path: image.path, name: image.name }, session, generation: this.#generation, status: 'attached' })
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
