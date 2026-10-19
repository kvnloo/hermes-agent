import { describe, expect, it } from 'vitest'

import { fileHref, rewriteLocalMarkdownLinks } from '../links.js'

// Deterministic inputs: no ambient cwd, filesystem access or property-test seed drift.
const cwd = '/workspace/native-tern'

function filenames(): string[] {
  const alphabet = ['a', 'z', '4', '-', '_', ' ', '#', '?', '%', '(', ')', 'é', '🧭']
  let state = 0x51ace
  const values: string[] = []

  for (let i = 0; i < 64; i++) {
    let name = ''

    for (let j = 0; j < 7; j++) {
      state = (Math.imul(state, 1664525) + 1013904223) >>> 0
      name += alphabet[state % alphabet.length]
    }

    values.push(name + '.tsx')
  }

  return values
}

describe('session-owned native file-link invariants (#535)', () => {
  it('round-trips safely encoded local filenames without relying on process.cwd', () => {
    for (const name of filenames()) {
      const href = fileHref('src/' + name, cwd)
      expect(href, name).toBeDefined()
      const parsed = new URL(href!)
      expect(parsed.protocol).toBe('file:')
      expect(parsed.host).toBe('')
      expect(decodeURIComponent(parsed.pathname)).toBe(cwd + '/src/' + name)
      expect(parsed.hash).toBe('')
      expect(fileHref('src/' + name, cwd)).toBe(href)
      expect(fileHref('src/' + name, '')).toBeUndefined()
    }
  })

  it('never turns control characters or remote schemes into local open targets', () => {
    const unsafe = [
      'https://example.com/a.ts', 'http://example.com/a.ts', 'mailto:a@b.test',
      'javascript:alert(1)', 'data:text/plain,x', 'file:///etc/passwd',
      'ssh://host/a.ts', '//host/a.ts', 'src/a\x00b.ts', 'src/a\n.ts',
      'src/a\r.ts', 'src/a\t.ts', 'src/a\x1fb.ts', 'src/a\x7fb.ts'
    ]

    for (const target of unsafe) {
      expect(fileHref(target, cwd), JSON.stringify(target)).toBeUndefined()
    }
  })

  it('adds line fragments only for safe positive integers', () => {
    const invalid = [0, -1, 1.5, NaN, Infinity, -Infinity, Number.MAX_SAFE_INTEGER + 1]

    for (const line of invalid) {
      expect(fileHref('src/example.ts', cwd, { line })).toBe('file:///workspace/native-tern/src/example.ts')
      expect(fileHref('src/example.ts', cwd, { line: 7, endLine: line })).toBe('file:///workspace/native-tern/src/example.ts#L7')
      expect(fileHref('src/example.ts', cwd, { line: 7, col: line })).toBe('file:///workspace/native-tern/src/example.ts#L7')
    }

    expect(fileHref('src/example.ts', cwd, { line: 7, endLine: 11 })).toBe('file:///workspace/native-tern/src/example.ts#L7-L11')
    expect(fileHref('src/example.ts', cwd, { line: 7, col: 3 })).toBe('file:///workspace/native-tern/src/example.ts#L7C3')
  })

  it('rewrites prose once and leaves existing file URLs, web links and code inert', () => {
    const fence = String.fromCharCode(96).repeat(3)
    const source = [
      '[source](src/a%20b.ts) [line](src/b.ts#L3-L5) [web](https://example.com)',
      String.fromCharCode(96) + '[inline](src/no.ts)' + String.fromCharCode(96),
      fence + 'md',
      '[fenced](src/no.ts)',
      fence,
      '[other](src/c(d).ts)'
    ].join('\n')
    const once = rewriteLocalMarkdownLinks(source, cwd)
    const twice = rewriteLocalMarkdownLinks(once, cwd)

    expect(once).toBe(twice)
    expect(once).toContain('[source](file:///workspace/native-tern/src/a%20b.ts)')
    expect(once).toContain('[line](file:///workspace/native-tern/src/b.ts#L3-L5)')
    expect(once).toContain('[web](https://example.com)')
    expect(once).toContain('[fenced](src/no.ts)')
    expect(once).toContain('[other](<file:///workspace/native-tern/src/c(d).ts>)')
  })
})
