
import { describe, expect, it } from 'vitest'

import { operationalText } from '../operations.js'

describe('literal operational report display', () => {
  it('neutralizes terminal control sequences, bidi overrides and Markdown injection', () => {
    const text = operationalText({
      view: 'ssh-list', scope: 'profile', state: 'ready', read_only: true,
      message: 'Connected \x1b]2;spoofed title\x07 \u202e',
      rows: [{ name: '**admin**\r# counterfeit heading',
        details: ['[click here](https://example.invalid/?secret=bad)', 'visible\bcontrol'] }]
    })

    expect(text).not.toMatch(/[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/)
    expect(text).not.toContain('spoofed title')
    expect(text).toContain('u202e')
    expect(text).toContain('\\*\\*admin\\*\\*')
    expect(text).toContain('\\# counterfeit heading')
    expect(text).toContain('\\[click here\\]\\(https://example\\.invalid/')
    expect(text).toContain('u0008control')
  })

  it('preserves literal multi-item inventory, not fake headings or links', () => {
    const text = operationalText({
      view: 'mcp-tools', scope: 'profile', state: 'ready', read_only: true,
      message: 'Tools', rows: [
        { name: 'safe-a', details: ['method-a', 'method-b'] },
        { name: 'safe-b', details: ['method-c'] }
      ]
    })
    expect(text).toContain('## safe\\-a\n\n- method\\-a\n- method\\-b')
    expect(text).toContain('## safe\\-b\n\n- method\\-c')
    expect(text).not.toContain('No MCP servers')
  })
})
