// Read-result media is path-backed. Tern loads the file; the frontend neither
// reads bytes nor invents blob ids (only Session.blob may address blobs).
import { extname } from 'node:path'
import { fileURLToPath } from 'node:url'

import { node, type Node } from '@stencil-hq/tern'

import { fileHref } from './links.js'
import { mediaNode } from './tern-media.js'

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
