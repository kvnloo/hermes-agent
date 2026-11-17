/** The workspace pane is registered before the first disk plugin scan.
 * A deep-linked plugin page must not paint a "New session" tab while the
 * plugin has not registered its route. This tests the real module boot, not
 * only workspaceHeaderVetoed() in isolation.
 */
import { expect, it } from 'vitest'

import { $diskPluginsScanPending } from '@/contrib/disk-scan'
import { registry } from '@/contrib/registry'

import { $workspaceIsPage } from '../routes'

it('initial workspace registration vetoes its tab on an unresolved plugin deep link', async () => {
  const originalHash = window.location.hash

  try {
    window.location.hash = '#/html-gallery'
    $workspaceIsPage.set(false)
    $diskPluginsScanPending.set(true)

    // Controller registers the initial workspace pane when evaluated.
    await import('./controller')

    const workspaceHeaderVeto = () => {
      const workspace = registry.getArea('panes').find(pane => pane.id === 'workspace')
      return (workspace?.data as { headerVeto?: boolean } | undefined)?.headerVeto
    }

    // Before the fix, the initial pane has no headerVeto, and listen() does
    // not fire until a subsequent state change: a first-paint tab flash.
    expect(workspaceHeaderVeto()).toBe(true)

    $diskPluginsScanPending.set(false)
    expect(workspaceHeaderVeto()).toBe(false)
  } finally {
    window.location.hash = originalHash
    $diskPluginsScanPending.set(false)
    $workspaceIsPage.set(false)
  }
})
