import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import type { ModelOptionsResult } from '@hermes/shared/gateway-events'
import React from 'react'
import { expect, it, vi } from 'vitest'

const input = vi.hoisted(() => ({
  handler: undefined as undefined | ((ch: string, key: Record<string, boolean>) => void)
}))

vi.mock('@hermes/ink', async importOriginal => ({
  ...await importOriginal(),
  useInput: (handler: (ch: string, key: Record<string, boolean>) => void) => { input.handler = handler }
}))

import { ModelPicker } from '../components/modelPicker.js'
import type { GatewayClient } from '../gatewayClient.js'
import { DEFAULT_THEME } from '../theme.js'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

const catalog = (model: string): ModelOptionsResult => ({
  model,
  providers: [{ slug: 'fixture', name: 'Fixture', models: [model], is_current: true,
    capabilities: { [model]: { reasoning: false } } }]
}) as ModelOptionsResult

async function flush() {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

function mount(request: (method: string, params: Record<string, unknown>) => Promise<unknown>) {
  const stdout = Object.assign(new PassThrough(), { columns: 100, rows: 40, isTTY: false })
  const stdin = Object.assign(new PassThrough(), { isTTY: false })
  const stderr = Object.assign(new PassThrough(), { isTTY: false })
  let output = ''
  stdout.on('data', chunk => { output += chunk.toString() })
  const onSelect = vi.fn()
  const gw = { request } as unknown as GatewayClient
  const element = (sessionId: string) => React.createElement(ModelPicker, {
    allowPersistGlobal: false, gw, onCancel: vi.fn(), onSelect,
    sessionId, t: DEFAULT_THEME
  })
  const instance = renderSync(element('session-a'), {
    patchConsole: false, stdout: stdout as NodeJS.WriteStream,
    stdin: stdin as NodeJS.ReadStream, stderr: stderr as NodeJS.WriteStream
  })
  return {
    onSelect,
    output: () => stripAnsi(output),
    clearOutput: () => { output = '' },
    rerender: (sessionId: string) => instance.rerender(element(sessionId)),
    enter: () => input.handler?.('', { return: true }),
    cleanup: () => { instance.unmount(); instance.cleanup(); input.handler = undefined }
  }
}

it.each(['resolve', 'reject'] as const)('ignores an obsolete session catalog that later %ss', async completion => {
  const first = deferred<ModelOptionsResult>()
  const second = deferred<ModelOptionsResult>()
  const request = vi.fn(async (method: string, params: Record<string, unknown>) => {
    if (method === 'model.options') return params.session_id === 'session-a' ? first.promise : second.promise
    return { value: 'medium' }
  })
  const mounted = mount(request)
  try {
    await vi.waitFor(() => expect(request).toHaveBeenCalledWith('model.options', expect.objectContaining({ session_id: 'session-a' })))
    mounted.rerender('session-b')
    await vi.waitFor(() => expect(request).toHaveBeenCalledWith('model.options', expect.objectContaining({ session_id: 'session-b' })))
    second.resolve(catalog('new-model'))
    await vi.waitFor(() => expect(mounted.output()).toContain('new-model'))
    if (completion === 'resolve') first.resolve(catalog('old-model'))
    else first.reject(new Error('obsolete catalog failure'))
    await flush()
    mounted.enter()
    await flush()
    expect(mounted.onSelect).toHaveBeenCalledExactlyOnceWith('new-model --provider fixture --tui-session')
    expect(request.mock.calls.filter(([method]) => method === 'config.get')).toEqual([
      ['config.get', { key: 'reasoning', session_id: 'session-b' }]
    ])
  } finally { mounted.cleanup() }
})

it('does not start a reasoning read after the picker unmounts with a pending catalog', async () => {
  const pending = deferred<ModelOptionsResult>()
  const request = vi.fn(async (method: string) => method === 'model.options' ? pending.promise : { value: 'medium' })
  const mounted = mount(request)
  await vi.waitFor(() => expect(request).toHaveBeenCalledTimes(1))
  mounted.cleanup()
  pending.resolve(catalog('old-model'))
  await flush()
  expect(request.mock.calls.map(([method]) => method)).toEqual(['model.options'])
  expect(mounted.onSelect).not.toHaveBeenCalled()
})

it.each(['resolve', 'reject'] as const)('ignores an obsolete reasoning read that later %ss', async completion => {
  const oldReasoning = deferred<{ value: string }>()
  const request = vi.fn(async (method: string, params: Record<string, unknown>) => {
    if (method === 'model.options') {
      const result = catalog(params.session_id === 'session-a' ? 'old-model' : 'new-model')
      result.providers![0]!.capabilities = {}
      return result
    }
    return params.session_id === 'session-a' ? oldReasoning.promise : { value: 'high' }
  })
  const mounted = mount(request)
  try {
    await vi.waitFor(() => expect(request).toHaveBeenCalledWith('config.get', { key: 'reasoning', session_id: 'session-a' }))
    mounted.rerender('session-b')
    await vi.waitFor(() => expect(request).toHaveBeenCalledWith('config.get', { key: 'reasoning', session_id: 'session-b' }))
    await flush()
    if (completion === 'resolve') oldReasoning.resolve({ value: 'low' })
    else oldReasoning.reject(new Error('obsolete reasoning failure'))
    await flush()
    mounted.clearOutput()
    mounted.enter()
    await flush()
    expect(mounted.output()).toContain('Keep current effort (high)')
  } finally { mounted.cleanup() }
})
