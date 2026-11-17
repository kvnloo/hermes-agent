import { expect, it, vi } from 'vitest'

const ipc = vi.hoisted(() => ({
  handlers: new Map<string, (...args: unknown[]) => unknown>(),
  repoStatus: vi.fn<(_repoPath: string, _gitBinary: string) => Promise<unknown>>()
}))

vi.mock('electron', () => ({
  ipcMain: {
    handle: (channel: string, handler: (...args: unknown[]) => unknown) => ipc.handlers.set(channel, handler)
  }
}))

vi.mock('./git-review-ops', async importOriginal => ({
  ...(await importOriginal<typeof import('./git-review-ops')>()),
  repoStatus: ipc.repoStatus
}))

import { registerGitIpc } from './git-ipc'

it('shares concurrent repoStatus IPC probes per repo and refreshes after completion', async () => {
  const status = { branch: 'main', changed: 1 }
  let finish!: (value: typeof status) => void
  const inFlight = new Promise<typeof status>(resolve => {
    finish = resolve
  })

  ipc.repoStatus.mockResolvedValue(status).mockImplementationOnce(() => inFlight)
  registerGitIpc({ resolveGitBinary: () => 'git', resolveGhBinary: () => 'gh' })

  const handler = ipc.handlers.get('hermes:git:repoStatus')

  if (!handler) {
    throw new Error('repoStatus IPC handler was not registered')
  }

  const first = handler({}, '/workspace/large')
  const second = handler({}, '/workspace/large')

  finish(status)
  await expect(Promise.all([first, second])).resolves.toEqual([status, status])
  expect(ipc.repoStatus).toHaveBeenCalledTimes(1)
  expect(ipc.repoStatus).toHaveBeenCalledWith('/workspace/large', 'git')

  await expect(handler({}, '/workspace/large')).resolves.toEqual(status)
  expect(ipc.repoStatus).toHaveBeenCalledTimes(2)
})
