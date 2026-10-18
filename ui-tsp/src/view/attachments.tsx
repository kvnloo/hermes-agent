import { type JSX, node } from '@stencil-hq/tern'

import type { Attachment, SubmittedImage } from '../attachments.js'
import { mediaNode } from '../tern-media.js'

import { ActionButton } from './action-button.js'

/** Shared vocabulary for composer attachments and immutable submitted user chips. */
export function attachmentNodes(images: readonly SubmittedImage[], native: boolean): JSX.Element {
  return (
    <row gap="sm" key="attachments" role="omp.user.attachments" wrap>
      {images.map(image => (
        <col gap="xs" key={image.id} role="omp.attachment">
          <badge key="name" text={image.name} title={image.path} />
          {thumbnail(image.path, image.name, native)}
        </col>
      ))}
    </row>
  )
}

function thumbnail(path: string, name: string, native: boolean): JSX.Element {
  return native
    ? node('col', { key: 'thumbnail', max: { h: '6lines', w: '18ch' } }, [mediaNode({ path })])
    : node('image', { alt: name, key: 'thumbnail', max: { h: '6lines', w: '18ch' }, path })
}

export function composerAttachments(images: readonly Attachment[], remove: (id: string) => void, retry: (id: string) => void): JSX.Element {
  return (
    <row gap="sm" hidden={!images.length} key="chips" role="omp.composer.chips" wrap>
      {images.map(image => (
        <row align="center" gap="xs" key={image.id} role="omp.composer.attachment" title={image.status === 'failed' ? image.error : image.mime}>
          <badge key="name" text={`${image.name} · ${image.bytes} B · ${image.status}`} tone={image.status === 'failed' ? 'error' : image.status === 'pending' ? 'pending' : 'success'} />
          {image.status === 'failed' ? <text key="error" text={image.error} tone="error" /> : null}
          {image.status === 'failed' ? <ActionButton key="retry" onClick={() => retry(image.id)} text="Retry" title="Retry attachment" /> : null}
          <ActionButton key="remove" onClick={() => remove(image.id)} text="×" title={`Remove ${image.name}`} />
        </row>
      ))}
    </row>
  )
}
