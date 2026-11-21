import { computed } from 'nanostores'

import { $fileBrowserOpen } from '@/store/layout'
import { $focusedWorkspaceCwd } from '@/store/session-states'

/** Files are shown only when the focused session has a workspace and the toggle is on. */
export const shouldShowFilesPane = (focusedWorkspaceCwd: string, fileBrowserOpen: boolean): boolean =>
  Boolean(focusedWorkspaceCwd.trim()) && fileBrowserOpen

// Export the production binding so the regression tests the real store
// selection without importing the controller's renderer/registration graph.
export const $filesPaneVisible = computed([$focusedWorkspaceCwd, $fileBrowserOpen], shouldShowFilesPane)
