import { describe, expect, it } from 'vitest'

import { cardCount, classifyDoc, filterDesk, layoutDesk, planWalk, seedDesk, shouldSkipDir } from './model'

describe('spatial curator', () => {
  it('ranks product scope above generic docs', () => {
    expect(classifyDoc('docs/PRD.md').priority).toBeGreaterThan(classifyDoc('docs/notes/misc.md').priority)
    expect(classifyDoc('docs/decisions/ADR-001.md').stack).toBe('Decisions')
    expect(classifyDoc('AGENTS.md').stack).toBe('Context')
    expect(classifyDoc('roadmap.md').type).toBe('roadmap')
  })

  it('layouts highest-priority stacks first and collapses the long tail', () => {
    const desk = layoutDesk([
      { path: '/r/docs/notes/z.md', name: 'z.md', rel: 'docs/notes/z.md' },
      { path: '/r/docs/PRD.md', name: 'PRD.md', rel: 'docs/PRD.md' },
      { path: '/r/docs/ROADMAP.md', name: 'ROADMAP.md', rel: 'docs/ROADMAP.md' },
      { path: '/r/README.md', name: 'README.md', rel: 'README.md' },
      { path: '/r/docs/specs/a.md', name: 'a.md', rel: 'docs/specs/a.md' }
    ])
    expect(desk.stacks[0].name).toBe('Scope')
    expect(desk.stacks[0].collapsed).toBe(false)
    expect(desk.stacks[0].cards[0].type).toBe('prd')
    expect(desk.stacks[0].priority).toBeGreaterThanOrEqual(desk.stacks.at(-1)!.priority)
    expect(cardCount(desk)).toBeGreaterThan(0)
  })

  it('filters without dropping stack metadata shape', () => {
    const desk = seedDesk()
    const hit = filterDesk(desk, 'prd')
    expect(cardCount(hit)).toBe(1)
    expect(filterDesk(desk, 'zzz').stacks).toEqual([])
  })

  it('plans walks that skip junk dirs', () => {
    expect(shouldSkipDir('node_modules')).toBe(true)
    const plan = planWalk(
      [
        { name: 'node_modules', isDirectory: true, path: '/r/node_modules' },
        { name: 'docs', isDirectory: true, path: '/r/docs' },
        { name: 'PRD.md', isDirectory: false, path: '/r/PRD.md' },
        { name: 'app.ts', isDirectory: false, path: '/r/app.ts' }
      ],
      0,
      3
    )
    expect(plan.docs).toEqual(['/r/PRD.md'])
    expect(plan.dirs).toEqual(['/r/docs'])
  })
})
