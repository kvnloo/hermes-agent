import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import type { ModelOptionProvider } from '@hermes/shared/gateway-events'
import React from 'react'
import { expect, it, vi } from 'vitest'

const input = vi.hoisted(() => ({
  handler: undefined as undefined | ((ch: string, key: Record<string, boolean>) => void)
}))

// Keep real Ink rendering and React effects; only replace terminal key delivery.
vi.mock('@hermes/ink', async importOriginal => ({
  ...await importOriginal(),
  useInput: (handler: (ch: string, key: Record<string, boolean>) => void) => { input.handler = handler }
}))

import { ModelPicker } from '../components/modelPicker.js'
import type { GatewayClient } from '../gatewayClient.js'
import { DEFAULT_THEME } from '../theme.js'

const provider = (slug: string, models: string[], current = false): ModelOptionProvider => ({
  slug, name: slug, models, is_current: current,
  capabilities: Object.fromEntries(models.map(model => [model, { reasoning: false }]))
}) as ModelOptionProvider

async function mount(providers: ModelOptionProvider[], current: string) {
  const stdout = Object.assign(new PassThrough(), { columns: 100, rows: 40, isTTY: false })
  const stdin = Object.assign(new PassThrough(), { isTTY: false })
  const stderr = Object.assign(new PassThrough(), { isTTY: false })
  let output = ''
  stdout.on('data', chunk => { output += chunk.toString() })
  const onSelect = vi.fn()
  const request = vi.fn(async (method: string) => method === 'model.options'
    ? { providers, model: current } : { value: 'medium' })
  const instance = renderSync(React.createElement(ModelPicker, {
    allowPersistGlobal: false, gw: { request } as unknown as GatewayClient,
    onCancel: vi.fn(), onSelect, sessionId: 'fixture-session', t: DEFAULT_THEME
  }), {
    patchConsole: false, stdout: stdout as NodeJS.WriteStream,
    stdin: stdin as NodeJS.ReadStream, stderr: stderr as NodeJS.WriteStream
  })
  const flush = async () => {
    await new Promise<void>(resolve => setImmediate(resolve))
    await new Promise<void>(resolve => setImmediate(resolve))
  }
  await vi.waitFor(() => expect(stripAnsi(output)).toContain('Enter use'))
  await flush()
  return {
    onSelect,
    press: async (key: Record<string, boolean>) => {
      input.handler?.('', key)
      await flush()
    },
    cleanup: () => { instance.unmount(); instance.cleanup() }
  }
}

it('Enter initially selects the current model after the hop catalog is reordered', async () => {
  const mounted = await mount([provider('fixture', ['other', 'current'], true)], 'current')
  try {
    await mounted.press({ return: true })
    expect(mounted.onSelect).toHaveBeenCalledExactlyOnceWith('current --provider fixture --tui-session')
  } finally { mounted.cleanup() }
})

it('hop navigation can move beyond the current provider model count', async () => {
  const mounted = await mount([
    provider('first', ['current'], true), provider('second', ['target'])
  ], 'current')
  try {
    await mounted.press({ downArrow: true })
    await mounted.press({ return: true })
    expect(mounted.onSelect).toHaveBeenCalledExactlyOnceWith('target --provider second --tui-session')
  } finally { mounted.cleanup() }
})
