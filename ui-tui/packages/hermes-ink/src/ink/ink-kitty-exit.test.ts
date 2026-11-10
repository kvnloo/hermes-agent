import { EventEmitter } from 'events'

import React from 'react'
import { describe, expect, it, vi } from 'vitest'

import Text from './components/Text.js'
import Ink from './ink.js'
import { DISABLE_KITTY_KEYBOARD } from './termio/csi.js'
import { EXIT_ALT_SCREEN } from './termio/dec.js'

// Ink writes the final alt-screen cleanup synchronously, rather than through
// its mocked stdout stream. Observe those actual writes at the fs boundary.
const { syncWrites } = vi.hoisted(() => ({ syncWrites: [] as string[] }))

vi.mock('fs', async importOriginal => {
  const actual = await importOriginal<typeof import('fs')>()

  return {
    ...actual,
    writeSync: (fd: number, data: string | Uint8Array): number => {
      if (fd === 1) {
        syncWrites.push(typeof data === 'string' ? data : Buffer.from(data).toString('utf8'))

        return typeof data === 'string' ? Buffer.byteLength(data) : data.byteLength
      }

      return typeof data === 'string' ? actual.writeSync(fd, data) : actual.writeSync(fd, data)
    }
  }
})

class FakeTty extends EventEmitter {
  columns = 20
  rows = 5
  isTTY = true

  write(_chunk: string | Uint8Array, cb?: (err?: Error | null) => void): boolean {
    cb?.()

    return true
  }

  setRawMode(_enabled: boolean): void {}
}

describe('Ink alternate-screen shutdown (#56759)', () => {
  it('pops kitty keyboard mode before switching back to the main screen', () => {
    const stdout = new FakeTty()
    const stdin = new FakeTty()
    const stderr = new FakeTty()
    const ink = new Ink({
      exitOnCtrlC: false,
      patchConsole: false,
      stderr: stderr as unknown as NodeJS.WriteStream,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stdout: stdout as unknown as NodeJS.WriteStream
    })

    ink.setAltScreenActive(true)
    ink.render(React.createElement(Text, null, 'hello'))
    ink.onRender()

    syncWrites.length = 0
    ink.unmount()

    // These are the actual synchronous cleanup bytes. On the PR's merge
    // base, Ink exits the alternate screen without popping its kitty stack.
    const shutdown = syncWrites.join('')
    const pop = shutdown.indexOf(DISABLE_KITTY_KEYBOARD)
    const leaveAlt = shutdown.indexOf(EXIT_ALT_SCREEN)

    expect(pop).toBeGreaterThanOrEqual(0)
    expect(leaveAlt).toBeGreaterThanOrEqual(0)
    expect(pop).toBeLessThan(leaveAlt)
  })
})
