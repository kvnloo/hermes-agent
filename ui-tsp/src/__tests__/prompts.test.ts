import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import { describe, expect, it } from 'vitest'

import type { OverlayHost } from '../overlay.js'
import { promptOverlay } from '../overlays/prompts.js'

const host: OverlayHost = {
  changed() {},
  close() {},
  open() {}
}

function request(method: string, params: Record<string, unknown>): { calls: string[]; req: ServerRequest } {
  const calls: string[] = []

  return {
    calls,
    req: {
      fail: () => calls.push('fail'),
      id: 'req-1',
      method,
      params,
      respond: () => calls.push('respond')
    }
  }
}

describe('prompt overlay', () => {
  it('opens approval, clarify, and secret and does not answer them', () => {
    const approval = request('approval', { command: 'rm -rf /tmp/nope' })
    const clarify = request('clarify', {
      questions: [{ choices: ['a', 'b'], qid: 'q1', question: 'Which file?' }]
    })
    const secret = request('secret', { env_var: 'TOKEN', prompt: 'Token' })

    expect(promptOverlay(host, approval.req)?.key).toBe('prompt:req-1')
    expect(promptOverlay(host, clarify.req)?.key).toBe('prompt:req-1')
    expect(promptOverlay(host, secret.req)?.key).toBe('prompt:req-1')
    expect(approval.calls).toEqual([])
    expect(clarify.calls).toEqual([])
    expect(secret.calls).toEqual([])
  })

  it('does not invent an answer for an unknown request', () => {
    const unknown = request('not-a-prompt', {})

    expect(promptOverlay(host, unknown.req)).toBeNull()
    expect(unknown.calls).toEqual([])
  })
})
