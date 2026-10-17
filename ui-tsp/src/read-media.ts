// Read-result media is path-backed. Tern loads the file; the frontend neither
// reads bytes nor invents blob ids (only Session.blob may address blobs).
import { createHash } from 'node:crypto'
import { extname } from 'node:path'
import { fileURLToPath } from 'node:url'

import { node, type Node } from '@stencil-hq/tern'

import { fileHref } from './links.js'
import type { ToolCall } from './model.js'
import { mediaNode } from './tern-media.js'
import { record } from './transcript.js'

interface ArtifactOwner {
  readonly callId: string
  /** Presentation identity only, never a Tern git revision or a blob id. */
  readonly revision: string
}

interface SourceArtifact extends ArtifactOwner {
  readonly kind: 'source'
  readonly language: 'svg' | 'mermaid'
  readonly source: string
}

interface ModelArtifact extends ArtifactOwner {
  readonly kind: 'model'
  /** Only constructed for a confirmed host-local path. */
  readonly path: string
}

export type ConfirmedWriteArtifact = SourceArtifact | ModelArtifact

const figureLanguages: Record<string, SourceArtifact['language']> = {
  svg: 'svg', mmd: 'mermaid', mermaid: 'mermaid'
}

const figureMimes: Record<SourceArtifact['language'], readonly string[]> = {
  svg: ['image/svg+xml'],
  mermaid: ['text/plain', 'text/vnd.mermaid', 'text/x-mermaid']
}

const modelMimes: Record<string, readonly string[]> = {
  glb: ['model/gltf-binary'], gltf: ['model/gltf+json'], obj: ['model/obj', 'text/plain'],
  usd: ['model/vnd.usd', 'application/x-usd'], usda: ['model/vnd.usda', 'text/plain'],
  usdc: ['model/vnd.usdc'], usdz: ['model/vnd.usdz+zip', 'application/x-usdz']
}

/** Project the owning completion, never the streaming arguments alone. No async cache to go stale. */
export function confirmedWriteArtifact(call: ToolCall, cwd: string, hostLocal: boolean): ConfirmedWriteArtifact | undefined {
  const result = record(call.result)
  const source = typeof call.args.content === 'string' ? call.args.content : call.args.contents

  // WriteResult.verified is the backend's on-disk hash check. bytes_written also
  // rejects partial results and differently sized/incomplete arguments.
  if (call.name !== 'write_file' || call.status !== 'done' || !result || result.error || result.success === false ||
      result.verified !== true || result.partial === true || result.truncated === true || typeof source !== 'string' ||
      !source || result.bytes_written !== Buffer.byteLength(source, 'utf8')) {
    return undefined
  }

  const rawPath = result.resolved_path ?? call.args.path ?? call.args.file_path

  if (typeof rawPath !== 'string') { return undefined }

  const href = fileHref(rawPath, cwd)
  const ext = extname(rawPath).slice(1).toLowerCase()
  const reportedMime = result.mime ?? result.mime_type ?? result.mimetype

  if (!href || (reportedMime !== undefined && typeof reportedMime !== 'string')) { return undefined }

  const mime = typeof reportedMime === 'string' ? reportedMime.split(';')[0]?.trim().toLowerCase() : undefined
  const revision = createHash('sha256').update(JSON.stringify([call.id, href, source, result])).digest('hex')
  const owner = { callId: call.id, revision }
  const language = Object.hasOwn(figureLanguages, ext) ? figureLanguages[ext] : undefined

  if (language) {
    return !mime || mime === 'application/octet-stream' || figureMimes[language].includes(mime)
      ? { ...owner, kind: 'source', language, source }
      : undefined
  }

  if (hostLocal && extensions.model.includes(ext) && (!mime || mime === 'application/octet-stream' || modelMimes[ext]?.includes(mime))) {
    return { ...owner, kind: 'model', path: fileURLToPath(href) }
  }

  return undefined
}

/** Native fences own SVG/Mermaid rendering and theme; no generated JS or Luau is evaluated. */
export function writtenArtifactNode(artifact: ConfirmedWriteArtifact, native: boolean): Node | undefined {
  const key = `figure-${artifact.callId}-${artifact.revision}`

  if (artifact.kind === 'model') {
    return native ? mediaNode({ path: artifact.path }, key) : undefined
  }

  // A generated source containing a fence must not escape into a second Markdown block.
  const ticks = '`'.repeat([...artifact.source.matchAll(/`+/g)].reduce((size, match) => Math.max(size, match[0].length + 1), 3))

  return node('md', { key, role: 'omp.tool.write.figure', text: `${ticks}${artifact.language}\n${artifact.source}\n${ticks}` })
}

type Family = 'image' | 'pdf' | 'video' | 'audio' | 'model'

const extensions: Record<Family, readonly string[]> = {
  image: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'avif', 'bmp', 'tif', 'tiff', 'ico', 'heic', 'heif'],
  pdf: ['pdf'],
  video: ['mp4', 'webm', 'mov', 'm4v', 'mkv', 'avi', 'ogv'],
  audio: ['mp3', 'wav', 'ogg', 'oga', 'flac', 'm4a', 'aac', 'opus', 'aiff'],
  model: ['glb', 'gltf', 'obj', 'usd', 'usda', 'usdc', 'usdz']
}

const families = new Map(Object.entries(extensions).flatMap(([family, exts]) =>
  exts.map(ext => [ext, family] as const)
))

const mimes: Record<string, RegExp> = {
  image: /^image\//,
  pdf: /^application\/pdf$/,
  video: /^video\//,
  audio: /^audio\//,
  model: /^(?:model\/|application\/(?:gltf(?:-buffer)?|(?:x-)?usd[acz]?)(?:\+zip)?$)/
}

/** Unknown extensions and contradictory reported MIME types stay ordinary file links. */
export function readMedia(path: string, cwd: string, reportedMime: string | undefined, native: boolean): Node | undefined {
  const family = families.get(extname(path).slice(1).toLowerCase())
  const mime = reportedMime?.split(';')[0]?.trim().toLowerCase()
  const href = fileHref(path, cwd)

  if (!family || !href || (mime && mime !== 'application/octet-stream' && !mimes[family]?.test(mime))) {
    return undefined
  }

  // The pane's cwd can differ from the gateway session's cwd after resume.
  const absolute = fileURLToPath(href)

  if (native) {
    return mediaNode({ path: absolute })
  }

  return family === 'image' ? node('image', { alt: path, key: 'media', path: absolute }) : undefined
}
