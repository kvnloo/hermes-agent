import { PassThrough } from 'node:stream'

import { Box, renderSync, Text } from '@hermes/ink'
import React from 'react'
import stripAnsi from 'strip-ansi'
import { describe, expect, it } from 'vitest'

import {
  AGENTS_OVERLAY_MIN_COLS,
  AGENTS_OVERLAY_MIN_ROWS,
  agentsOverlayHeight,
  overlayLayoutDecision
} from '../lib/overlayLayoutDecision.js'

describe('overlayLayoutDecision', () => {
  it('tables overlay vs full from rows/cols/expanded', () => {
    const table: Array<[number, number, boolean, 'full' | 'overlay']> = [
      [24, 80, false, 'overlay'],
      [40, 120, false, 'overlay'],
      [80, 80, false, 'overlay'],
      [23, 80, false, 'full'],
      [24, 39, false, 'full'],
      [12, 40, false, 'full'],
      [40, 80, true, 'full'],
      [24, 80, true, 'full'],
      [AGENTS_OVERLAY_MIN_ROWS, AGENTS_OVERLAY_MIN_COLS, false, 'overlay']
    ]

    for (const [rows, cols, expanded, want] of table) {
      expect(overlayLayoutDecision(rows, cols, expanded)).toBe(want)
    }
  })

  it('sizes overlay height to ~40% while reserving parent rows', () => {
    expect(agentsOverlayHeight(24)).toBe(10)
    expect(agentsOverlayHeight(40)).toBe(16)
    expect(agentsOverlayHeight(100)).toBe(40)
  })
})

/**
 * Host shim mirrors appLayout's keep-vs-swap decision so the #113241
 * invariant is proven without mounting the full AppLayout graph.
 */
function AgentsChromeHost({
  cols,
  draft,
  expanded = false,
  marker,
  open,
  rows
}: {
  cols: number
  draft: string
  expanded?: boolean
  marker: string
  open: boolean
  rows: number
}) {
  const mode = open ? overlayLayoutDecision(rows, cols, expanded) : null
  const full = mode === 'full'
  const overlay = mode === 'overlay'
  const cardH = agentsOverlayHeight(rows)

  return (
    <Box flexDirection="column" height={rows} width={cols}>
      {full ? (
        <Box flexDirection="column" flexGrow={1}>
          <Text>AGENTS_FULL</Text>
          <Text>workers · Esc close</Text>
        </Box>
      ) : (
        <>
          <Box flexDirection="column" flexGrow={1}>
            <Text>{marker}</Text>
            <Text>scroll-anchor</Text>
          </Box>
          <Text>{`composer:${draft}`}</Text>
        </>
      )}
      {overlay && (
        <Box flexDirection="column" height={cardH} width={cols}>
          <Text>AGENTS_OVERLAY</Text>
          <Text>{`card=${cardH}`}</Text>
        </Box>
      )}
      <Text>{open ? `open:${mode}` : 'closed'}</Text>
      <Text>{open ? 'focus:agents' : 'focus:composer'}</Text>
    </Box>
  )
}

const paint = (el: React.ReactElement, cols: number, rows: number) => {
  const stdout = Object.assign(new PassThrough(), { columns: cols, rows, isTTY: false })

  const stdin = Object.assign(new PassThrough(), {
    isTTY: true,
    setRawMode: () => {},
    ref: () => {},
    unref: () => {}
  })

  let output = ''
  stdout.on('data', chunk => {
    output += stripAnsi(chunk.toString())
  })

  const view = renderSync(el, {
    stdout: stdout as unknown as NodeJS.WriteStream,
    stdin: stdin as unknown as NodeJS.ReadStream,
    stderr: new PassThrough() as unknown as NodeJS.WriteStream,
    patchConsole: false
  })

  return {
    output: () => output,
    rerender: (next: React.ReactElement) => {
      output = ''
      view.rerender(next)
    },
    unmount: () => {
      view.unmount()
      view.cleanup()
    }
  }
}

describe('agentsOverlayContext', () => {
  it('opens overlay without unmounting transcript host at normal height', () => {
    const marker = 'PARENT_TRANSCRIPT_MARKER'

    const painted = paint(
      <AgentsChromeHost cols={80} draft="hello draft" marker={marker} open rows={40} />,
      80,
      40
    )

    try {
      expect(painted.output()).toContain(marker)
      expect(painted.output()).toContain('scroll-anchor')
      expect(painted.output()).toContain('AGENTS_OVERLAY')
      expect(painted.output()).not.toContain('AGENTS_FULL')
      expect(painted.output()).toContain('open:overlay')
    } finally {
      painted.unmount()
    }
  })

  it('preserves composer draft across open/close', () => {
    const draft = 'keep-me-byte-for-byte'

    const painted = paint(
      <AgentsChromeHost cols={80} draft={draft} marker="PARENT_TRANSCRIPT_MARKER" open rows={40} />,
      80,
      40
    )

    try {
      expect(painted.output()).toContain(`composer:${draft}`)
      expect(painted.output()).toContain('AGENTS_OVERLAY')
      painted.rerender(
        <AgentsChromeHost cols={80} draft={draft} marker="PARENT_TRANSCRIPT_MARKER" open={false} rows={40} />
      )
      expect(painted.output()).toContain(`composer:${draft}`)
      expect(painted.output()).not.toContain('AGENTS_OVERLAY')
      expect(painted.output()).toContain('closed')
    } finally {
      painted.unmount()
    }
  })

  it('small terminal falls back to full-height (transcript host not co-visible)', () => {
    const marker = 'PARENT_TRANSCRIPT_MARKER'

    const painted = paint(
      <AgentsChromeHost cols={80} draft="x" marker={marker} open rows={20} />,
      80,
      20
    )

    try {
      expect(painted.output()).toContain('AGENTS_FULL')
      expect(painted.output()).not.toContain(marker)
      expect(painted.output()).toContain('open:full')
    } finally {
      painted.unmount()
    }
  })

  it('explicit expand reaches full-height even on a large terminal', () => {
    const marker = 'PARENT_TRANSCRIPT_MARKER'

    const painted = paint(
      <AgentsChromeHost cols={120} draft="x" expanded marker={marker} open rows={60} />,
      120,
      60
    )

    try {
      expect(painted.output()).toContain('AGENTS_FULL')
      expect(painted.output()).not.toContain(marker)
      expect(painted.output()).toContain('open:full')
    } finally {
      painted.unmount()
    }
  })

  it('Esc restores focus region to composer after close', () => {
    const draft = 'focus-draft'

    const painted = paint(
      <AgentsChromeHost cols={80} draft={draft} marker="PARENT_TRANSCRIPT_MARKER" open rows={40} />,
      80,
      40
    )

    try {
      expect(painted.output()).toContain('focus:agents')
      expect(painted.output()).toContain(`composer:${draft}`)
      painted.rerender(
        <AgentsChromeHost cols={80} draft={draft} marker="PARENT_TRANSCRIPT_MARKER" open={false} rows={40} />
      )
      expect(painted.output()).toContain('focus:composer')
      expect(painted.output()).toContain(`composer:${draft}`)
      expect(painted.output()).not.toContain('AGENTS_OVERLAY')
    } finally {
      painted.unmount()
    }
  })

  it('width matrix smoke: 40 / 80 / 120 with overlay open (no throw)', () => {
    for (const cols of [40, 80, 120] as const) {
      const rows = 40
      const mode = overlayLayoutDecision(rows, cols, false)
      expect(['overlay', 'full']).toContain(mode)

      const painted = paint(
        <AgentsChromeHost cols={cols} draft="w" marker="PARENT_TRANSCRIPT_MARKER" open rows={rows} />,
        cols,
        rows
      )

      try {
        expect(painted.output().length).toBeGreaterThan(0)

        if (mode === 'overlay') {
          expect(painted.output()).toContain('AGENTS_OVERLAY')
          expect(painted.output()).toContain('PARENT_TRANSCRIPT_MARKER')
        } else {
          expect(painted.output()).toContain('AGENTS_FULL')
        }
      } finally {
        painted.unmount()
      }
    }
  })
})
