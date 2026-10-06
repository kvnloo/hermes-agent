import { describe, expect, it } from 'vitest'

import { FramePump } from '../frame.js'

function pump(blocked: () => boolean) {
  const renders: number[] = []
  let n = 0
  const queued: Array<() => void> = []
  const frames = new FramePump(
    blocked,
    () => {
      renders.push(++n)
    },
    fn => queued.push(fn)
  )

  return {
    frames,
    renders,
    run: () => {
      const batch = queued.splice(0)
      for (const fn of batch) fn()
    }
  }
}

describe('FramePump', () => {
  it('sends one frame for a burst when credit is free', () => {
    const p = pump(() => false)

    p.frames.changed()
    p.frames.changed()
    expect(p.renders).toEqual([])

    p.run()
    expect(p.renders).toEqual([1])
  })

  it('keeps the newest view while blocked and flushes it on the next credit', () => {
    let blocked = true
    const p = pump(() => blocked)

    p.frames.changed()
    p.frames.changed()
    p.run()
    expect(p.renders).toEqual([])

    p.frames.credit()
    p.run()
    expect(p.renders).toEqual([])

    blocked = false
    p.frames.credit()
    p.run()
    expect(p.renders).toEqual([1])
  })

  it('does not send when nothing changed', () => {
    const p = pump(() => false)

    p.frames.credit()
    p.run()
    expect(p.renders).toEqual([])
  })
})
