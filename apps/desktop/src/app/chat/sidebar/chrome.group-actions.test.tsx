import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { $sidebarRowMeta } from '@/store/layout'

import { SidebarGroupRow } from './chrome'

const styles = readFileSync(fileURLToPath(new URL('../../../styles.css', import.meta.url)), 'utf8')
const priorRowMeta = $sidebarRowMeta.get()

afterEach(() => {
  cleanup()
  $sidebarRowMeta.set(priorRowMeta)
})

describe('SidebarGroupRow action totals (#154748)', () => {
  it('scopes focus/open fades to the owning group instead of a broad Tailwind group-has selector', () => {
    $sidebarRowMeta.set(['tokens'])

    const { container } = render(
      <SidebarGroupRow
        actions={<button data-state="open">Actions</button>}
        label={<span>Project</span>}
        lead={<span />}
        totals={{ costUsd: 0, tokens: 12345 }}
      />
    )

    const totals = container.querySelector('.sidebar-group-totals')
    expect(totals).not.toBeNull()
    expect(totals?.textContent).toBeTruthy()
    expect(totals?.className).toContain('group-hover/workspace:opacity-0')
    expect(totals?.className).not.toContain('group-has-')
    expect(totals?.closest('.sidebar-group-actions')?.querySelector('[data-state="open"]')).not.toBeNull()

    // Pin the shipped selector: Tailwind's group-has-* expands to a
    // document-scale :is(:where(group):has(...) *) invalidation rule.
    expect(styles).toMatch(
      /:where\(\.sidebar-group-actions\):has\(:focus-visible,\s*\[data-state='open'\]\)\s+\.sidebar-group-totals\s*\{\s*opacity:\s*0;/
    )
  })
})
