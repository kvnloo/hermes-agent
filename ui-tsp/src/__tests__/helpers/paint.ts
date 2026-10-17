import type { Session } from '@stencil-hq/tern'

/** Feature tests use a terminal that paints promptly. Credit-stall tests opt out. */
export function acknowledgeFrames(tern: Session) {
  const open = tern.open.bind(tern)

  tern.open = options => {
    const surface = open(options)

    const painted = () => {
      if (!surface.closed) {
        surface.acknowledge(surface.seq)
      }
    }

    const render = surface.render.bind(surface)
    const send = surface.send.bind(surface)

    surface.render = view => {
      render(view)
      painted()
    }

    surface.send = ops => {
      send(ops)
      painted()
    }

    return surface
  }
}
