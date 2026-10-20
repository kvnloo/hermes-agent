import { constants } from 'node:fs'

import { describe, expect, it, vi } from 'vitest'

import { readImageBytes } from '../media-delivery.js'

const probe = vi.hoisted(() => ({
  opened: [] as { path: string; flags: number }[],
  closed: [] as string[]
}))

/** The real FileHandle contract, with deterministic concurrent file-size changes. */
vi.mock('node:fs/promises', async importOriginal => {
  const real = await importOriginal<typeof import('node:fs/promises')>()

  return {
    ...real,
    open: async (...args: Parameters<typeof real.open>) => {
      const path = String(args[0])

      if (!path.startsWith('/synthetic-media/')) {
        return real.open(...args)
      }

      probe.opened.push({ path, flags: args[1] as number })
      const payload = Buffer.from('89504e470d0a1a0a00010203', 'hex')
      const mode = path.slice('/synthetic-media/'.length)
      const declared = mode === 'truncated' ? payload.length + 5 :
        mode === 'grown' ? payload.length - 5 :
          mode === 'oversize' ? payload.length + 1 : payload.length
      let cursor = 0

      const handle = {
        async stat() {
          return { isFile: () => mode !== 'directory', size: declared }
        },
        async read(buffer: Buffer, offset: number, length: number) {
          // Short OS reads are normal; EOF with fewer bytes than fstat is not.
          const count = Math.max(0, Math.min(4, length, payload.length - cursor))
          payload.copy(buffer, offset, cursor, cursor + count)
          cursor += count

          return { buffer, bytesRead: count }
        },
        async close() { probe.closed.push(path) }
      }

      return handle as unknown as Awaited<ReturnType<typeof real.open>>
    }
  }
})

describe('frontend-local media read ownership', () => {
  it('accepts repeated short reads when the exact stat size is eventually reached', async () => {
    const bytes = await readImageBytes('/synthetic-media/exact', 20)
    expect(bytes).toEqual(Buffer.from('89504e470d0a1a0a00010203', 'hex'))
    expect(probe.closed).toContain('/synthetic-media/exact')
  })

  it('rejects an in-place truncation even when the PNG magic header remains valid', async () => {
    await expect(readImageBytes('/synthetic-media/truncated', 20)).rejects.toThrow('changed while reading')
    expect(probe.closed).toContain('/synthetic-media/truncated')
  })

  it('rejects a growing file when a sentinel read passes the initial stat size', async () => {
    await expect(readImageBytes('/synthetic-media/grown', 20)).rejects.toThrow('changed while reading')
    expect(probe.closed).toContain('/synthetic-media/grown')
  })

  it('rejects directories and oversized files and closes both handles', async () => {
    await expect(readImageBytes('/synthetic-media/directory', 20)).rejects.toThrow('regular file')
    await expect(readImageBytes('/synthetic-media/oversize', 12)).rejects.toThrow('regular file')
    expect(probe.closed).toContain('/synthetic-media/directory')
    expect(probe.closed).toContain('/synthetic-media/oversize')
  })

  it('uses the read-only nonblocking descriptor and nofollow when available', async () => {
    await readImageBytes('/synthetic-media/flags', 20)
    const flags = probe.opened.find(item => item.path === '/synthetic-media/flags')!.flags
    expect(flags & constants.O_RDONLY).toBe(constants.O_RDONLY)
    expect(flags & constants.O_NONBLOCK).toBe(constants.O_NONBLOCK)

    if (constants.O_NOFOLLOW) {
      expect(flags & constants.O_NOFOLLOW).toBe(constants.O_NOFOLLOW)
    }
  })
})
