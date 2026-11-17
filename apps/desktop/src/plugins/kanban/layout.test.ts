import { describe, expect, it } from 'vitest'

import { KANBAN_LAYOUT, laneRailSnapClass } from './layout'

function classes(value: string): Set<string> {
  return new Set(value.split(/\s+/))
}

describe('Kanban responsive layout contract', () => {
  it('gives touch lanes one board width and disables snapping on desktop', () => {
    const rail = classes(KANBAN_LAYOUT.laneRail)
    const lane = classes(KANBAN_LAYOUT.lane)
    const collapsed = classes(KANBAN_LAYOUT.collapsedLane)

    expect(rail).toContain('md:snap-none')
    expect(rail).not.toContain('snap-x')
    expect(lane).toEqual(expect.objectContaining(new Set(['w-full', 'snap-start', 'md:w-64', 'md:snap-none'])))
    expect(collapsed).toEqual(expect.objectContaining(new Set(['w-full', 'snap-start', 'md:w-8', 'md:snap-none'])))
  })

  it('contains the toolbar and drawer on narrow viewports while retaining desktop sizing', () => {
    const page = classes(KANBAN_LAYOUT.page)
    const filters = classes(KANBAN_LAYOUT.toolbarFilters)
    const drawer = classes(KANBAN_LAYOUT.drawer)

    expect(page).toContain('min-w-0')
    expect(filters).toEqual(expect.objectContaining(new Set(['w-full', 'min-w-0', 'md:w-auto'])))
    expect(drawer).toEqual(
      expect.objectContaining(
        new Set([
          'w-full',
          'max-w-full',
          'md:w-[26rem]',
          'pl-[env(safe-area-inset-left)]',
          'pr-[env(safe-area-inset-right)]',
          'pb-[env(safe-area-inset-bottom)]'
        ])
      )
    )
  })
  it('disables mandatory lane snap during a card drag or grab-scroll, then restores it', () => {
    expect(laneRailSnapClass(false, false)).toBe('snap-x snap-mandatory')
    expect(laneRailSnapClass(false, true)).toBe('snap-none')
    expect(laneRailSnapClass(true, false)).toBe('snap-none')
    expect(laneRailSnapClass(true, true)).toBe('snap-none')
    expect(laneRailSnapClass(false, false)).toBe('snap-x snap-mandatory')
  })

})
