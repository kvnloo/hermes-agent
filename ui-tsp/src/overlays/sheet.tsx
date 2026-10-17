import type { Children, JSX, ScrollTo } from '@stencil-hq/tern'

import type { Overlay, OverlayHost } from '../overlay.js'

export interface SheetHost extends OverlayHost {
  scroll(overlay: Overlay, to: ScrollTo): void
}

interface SheetProps {
  id: string
  title: string
  role: string
  children?: Children
}

/** All native inspection sheets share the body/Markdown scroll target. */
export function Sheet({ id, title, role, children }: SheetProps): JSX.Element {
  return (
    <overlay anchor="center" head={title} key={id.slice('layer.'.length)} modal role={role} size="lg">
      <col gap="md" key="body">
        {children}
      </col>
    </overlay>
  )
}
