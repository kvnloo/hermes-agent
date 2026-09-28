import { PassThrough } from 'stream'

import { renderSync } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import React from 'react'
import { describe, expect, it } from 'vitest'

import { MessageLine } from '../components/messageLine.js'
import {
  AllocatedToolTrail,
  allocateSettledReadGroup,
  allocateSettledToolTrailLine,
  flattenToolHeader,
  isSettledReadGroupCandidate,
  isSettledToolTrailCandidate
} from '../components/toolAllocation.js'
import { DEFAULT_THEME } from '../theme.js'

const settledRead =
  'read_file(src/components/example.ts) (0.2s) :: lines 1-120\nsecond detail that should fold ✓'

const groupedReads = [
  'Read File("src/a.ts") (0.1s) :: lines 1-20 ✓',
  'Read File("src/b.ts") (0.2s) :: lines 1-40 ✓',
  'Read File("src/c.ts") (0.3s) :: lines 1-60 ✓'
]

describe('settled tool row allocation', () => {
  it('flattens embedded newlines in tool headers', () => {
    expect(flattenToolHeader('read_file(foo)\nbar')).toBe('read_file(foo) bar')
  })

  it('recognizes only finalized result lines', () => {
    expect(isSettledToolTrailCandidate([settledRead])).toBe(true)
    expect(isSettledToolTrailCandidate(['drafting read_file(foo)…'])).toBe(false)
  })

  it('lets a successful settled tool disappear at zero rows', () => {
    expect(allocateSettledToolTrailLine(settledRead, 0)?.rows).toEqual([])
  })

  it('keeps an error visible even when the requested budget is zero', () => {
    const block = allocateSettledToolTrailLine('terminal(make test) :: exit 1 ✗', 0)

    expect(block?.rows).toHaveLength(1)
    expect(block?.rows[0]).toContain('✗ terminal(make test)')
  })

  it('renders a settled read in exactly one semantic row', () => {
    const block = allocateSettledToolTrailLine(settledRead, 1)

    expect(block?.rows).toHaveLength(1)
    expect(block?.rows[0]).toContain('✓ read_file(src/components/example.ts)')
    expect(block?.rows[0]).not.toContain('\n')
  })

  it('renders the two-row folded-card shape', () => {
    const block = allocateSettledToolTrailLine(settledRead, 2)

    expect(block?.rows).toHaveLength(2)
    expect(block?.rows[0]).toMatch(/^╭─ ✓ /)
    expect(block?.rows[1]).toMatch(/^╰─ /)
    expect(block?.rows[1]).toContain('+1 line')
  })

  it('bounds 3+ rows and reports omitted detail exactly', () => {
    const line = 'terminal(test) :: one\ntwo\nthree\nfour ✓'
    const block = allocateSettledToolTrailLine(line, 3)

    expect(block?.rows).toHaveLength(3)
    expect(block?.rows.at(-1)).toContain('… 3 more lines')
  })
})

describe('settled read grouping', () => {
  it('accepts only 2+ successful canonical Read File rows', () => {
    expect(isSettledReadGroupCandidate(groupedReads)).toBe(true)
    expect(isSettledReadGroupCandidate([groupedReads[0]!])).toBe(false)
    expect(isSettledReadGroupCandidate([groupedReads[0]!, 'Terminal("pwd") ✓'])).toBe(false)
    expect(isSettledReadGroupCandidate([groupedReads[0]!, 'Read File("src/b.ts") ✗'])).toBe(false)
  })

  it('compresses a read run into one bounded summary row', () => {
    expect(allocateSettledReadGroup(groupedReads, 1)?.rows).toEqual([
      '✓ Read 3 files · src/a.ts · src/b.ts · +1 more'
    ])
  })

  it('renders a two-row folded read group', () => {
    expect(allocateSettledReadGroup(groupedReads, 2)?.rows).toEqual([
      '╭─ ✓ Read 3 files',
      '╰─ src/a.ts · +2 files'
    ])
  })

  it('uses spare rows for file identities before an omission row', () => {
    expect(allocateSettledReadGroup(groupedReads, 3)?.rows).toEqual([
      '╭─ ✓ Read 3 files',
      '│  src/a.ts',
      '╰─ … +2 files'
    ])
  })
})

describe.each([40, 80, 120])('AllocatedToolTrail at %i columns', columns => {
  it('keeps a one-row settled read on one physical line', () => {
    const stdout = new PassThrough()
    const stdin = new PassThrough()
    const stderr = new PassThrough()
    let output = ''

    Object.assign(stdout, { columns, isTTY: false, rows: 20 })
    Object.assign(stdin, { isTTY: false })
    Object.assign(stderr, { isTTY: false })
    stdout.on('data', chunk => {
      output += chunk.toString()
    })

    const instance = renderSync(
      <AllocatedToolTrail lines={[settledRead]} rowsPerTool={1} t={DEFAULT_THEME} />,
      {
        patchConsole: false,
        stderr: stderr as NodeJS.WriteStream,
        stdin: stdin as NodeJS.ReadStream,
        stdout: stdout as NodeJS.WriteStream
      }
    )

    const printable = stripAnsi(output).replace(/\r/g, '')
    const visibleLines = printable.split('\n').filter(Boolean)

    expect(visibleLines).toHaveLength(1)
    expect(visibleLines[0]).toContain('✓ read_file')

    instance.unmount()
    instance.cleanup()
  })
})

describe('MessageLine settled-tool integration', () => {
  it('routes one finalized collapsed tool result through the one-row renderer', () => {
    const stdout = new PassThrough()
    const stdin = new PassThrough()
    const stderr = new PassThrough()
    let output = ''

    Object.assign(stdout, { columns: 80, isTTY: false, rows: 20 })
    Object.assign(stdin, { isTTY: false })
    Object.assign(stderr, { isTTY: false })
    stdout.on('data', chunk => {
      output += chunk.toString()
    })

    const instance = renderSync(
      <MessageLine
        cols={80}
        detailsModeCommandOverride={true}
        msg={{ kind: 'trail', role: 'system', text: '', tools: [settledRead] }}
        t={DEFAULT_THEME}
      />,
      {
        patchConsole: false,
        stderr: stderr as NodeJS.WriteStream,
        stdin: stdin as NodeJS.ReadStream,
        stdout: stdout as NodeJS.WriteStream
      }
    )

    const printable = stripAnsi(output).replace(/\r/g, '')
    const visibleLines = printable.split('\n').filter(Boolean)

    expect(visibleLines).toHaveLength(1)
    expect(visibleLines[0]).toContain('✓ read_file')
    expect(printable).not.toContain('Tool calls')

    instance.unmount()
    instance.cleanup()
  })


  it('renders a completed read run as one compact group', () => {
    const stdout = new PassThrough()
    const stdin = new PassThrough()
    const stderr = new PassThrough()
    let output = ''

    Object.assign(stdout, { columns: 80, isTTY: false, rows: 20 })
    Object.assign(stdin, { isTTY: false })
    Object.assign(stderr, { isTTY: false })
    stdout.on('data', chunk => {
      output += chunk.toString()
    })

    const instance = renderSync(
      <MessageLine
        cols={80}
        msg={{ kind: 'trail', role: 'system', text: '', tools: groupedReads }}
        t={DEFAULT_THEME}
      />,
      {
        patchConsole: false,
        stderr: stderr as NodeJS.WriteStream,
        stdin: stdin as NodeJS.ReadStream,
        stdout: stdout as NodeJS.WriteStream
      }
    )

    const printable = stripAnsi(output).replace(/\r/g, '')
    const visibleLines = printable.split('\n').filter(Boolean)

    expect(visibleLines).toHaveLength(1)
    expect(visibleLines[0]).toContain('✓ Read 3 files')
    expect(printable).not.toContain('Tool calls')

    instance.unmount()
    instance.cleanup()
  })

  it('honors a two-row viewport budget without leaving the settled renderer', () => {
    const stdout = new PassThrough()
    const stdin = new PassThrough()
    const stderr = new PassThrough()
    let output = ''

    Object.assign(stdout, { columns: 80, isTTY: false, rows: 20 })
    Object.assign(stdin, { isTTY: false })
    Object.assign(stderr, { isTTY: false })
    stdout.on('data', chunk => {
      output += chunk.toString()
    })

    const instance = renderSync(
      <MessageLine
        cols={80}
        detailsModeCommandOverride={true}
        msg={{ kind: 'trail', role: 'system', text: '', tools: [settledRead] }}
        t={DEFAULT_THEME}
        toolRowBudget={2}
      />,
      {
        patchConsole: false,
        stderr: stderr as NodeJS.WriteStream,
        stdin: stdin as NodeJS.ReadStream,
        stdout: stdout as NodeJS.WriteStream
      }
    )

    const printable = stripAnsi(output).replace(/\r/g, '')
    const visibleLines = printable.split('\n').filter(Boolean)

    expect(visibleLines).toHaveLength(2)
    expect(visibleLines[0]).toMatch(/^╭─ ✓ read_file/)
    expect(visibleLines[1]).toMatch(/^╰─ /)
    expect(printable).not.toContain('Tool calls')

    instance.unmount()
    instance.cleanup()
  })
})
