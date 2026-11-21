import { expect, it, vi } from 'vitest'

import { createSlashHandler } from './createSlashHandler.js'
import type { SlashHandlerContext } from './interfaces.js'

// Regression for NousResearch/hermes-agent#149176, reported by ayylmaonade.
it('shows /insights labels without Markdown delimiters in the TUI pager', async () => {
  const output = [
    '**Models:**',
    '  Qwen-3.6 — 312 sessions, 267,841,033 tokens',
    '**Platforms:**',
    '  cron — 138 sessions, 1,472 msgs',
    '**Top Tools:**',
    '  terminal — 4,011 calls (46.8%)'
  ].join('\n')
  const page = vi.fn()
  const sys = vi.fn()
  const request = vi.fn(async (method: string) => (method === 'slash.exec' ? { output } : {}))
  const ctx = {
    gateway: { gw: { request } },
    local: { catalog: null },
    slashFlightRef: { current: 0 },
    transcript: { page, send: vi.fn(), sys }
  } as unknown as SlashHandlerContext

  expect(createSlashHandler(ctx)('/insights')).toBe(true)

  await vi.waitFor(() =>
    expect(page).toHaveBeenCalledWith(
      [
        'Models:',
        '  Qwen-3.6 — 312 sessions, 267,841,033 tokens',
        'Platforms:',
        '  cron — 138 sessions, 1,472 msgs',
        'Top Tools:',
        '  terminal — 4,011 calls (46.8%)'
      ].join('\n'),
      'Insights'
    )
  )
  expect(sys).not.toHaveBeenCalled()
})
