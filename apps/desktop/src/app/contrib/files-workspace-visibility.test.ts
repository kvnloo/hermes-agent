import { afterEach, expect, it } from 'vitest'

import { group, split } from '@/components/pane-shell/tree/model'
import {
  $hiddenTreePanes,
  $layoutTree,
  isPaneVisible,
  noteActiveTreeGroup
} from '@/components/pane-shell/tree/store'
import { $fileBrowserOpen, setFileBrowserOpen } from '@/store/layout'
import {
  $selectedStoredSessionId,
  $workspaceCwdOwner,
  setCurrentCwdTransient,
  setSessions
} from '@/store/session'
import { $focusedWorkspaceCwd } from '@/store/session-states'

afterEach(() => {
  setSessions([])
  setCurrentCwdTransient('')
  $selectedStoredSessionId.set(null)
  $workspaceCwdOwner.set(null)
  setFileBrowserOpen(false)
  $layoutTree.set(null)
  $hiddenTreePanes.set(new Set())
  window.localStorage.clear()
})

it('shows the Files pane when the focused session has a cwd but the profile memory is empty', async () => {
  // The profile-scoped workspace value can be empty during startup or a
  // profile swap even though the selected session still has a real workspace.
  setCurrentCwdTransient('')
  $workspaceCwdOwner.set('another-session')
  $selectedStoredSessionId.set('session-in-project')
  setSessions([{ id: 'session-in-project', cwd: '/repo/project' } as never])

  // Import the real controller wiring, including its Files visibility gate.
  await import('./controller')

  $layoutTree.set(
    split('row', [
      group(['workspace'], { active: 'workspace', id: 'main' }),
      group(['files'], { active: 'files', id: 'files-group' })
    ])
  )
  noteActiveTreeGroup('main')
  setFileBrowserOpen(true)

  expect($focusedWorkspaceCwd.get()).toBe('/repo/project')
  expect($fileBrowserOpen.get()).toBe(true)
  expect($hiddenTreePanes.get().has('files')).toBe(false)
  expect(isPaneVisible('files')).toBe(true)

  // No focused project: preserve the existing chrome hide, not an empty tree.
  setSessions([])
  $selectedStoredSessionId.set(null)
  expect($focusedWorkspaceCwd.get()).toBe('')
  expect($hiddenTreePanes.get().has('files')).toBe(true)
})
