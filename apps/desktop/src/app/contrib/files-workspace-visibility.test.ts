import { afterEach, expect, it } from 'vitest'

import { $fileBrowserOpen, setFileBrowserOpen } from '@/store/layout'
import {
  $currentCwd,
  $selectedStoredSessionId,
  $workspaceCwdOwner,
  setCurrentCwdTransient,
  setSessions
} from '@/store/session'
import { $focusedWorkspaceCwd } from '@/store/session-states'

import { $filesPaneVisible, shouldShowFilesPane } from './files-workspace-visibility'

afterEach(() => {
  setSessions([])
  setCurrentCwdTransient('')
  $selectedStoredSessionId.set(null)
  $workspaceCwdOwner.set(null)
  setFileBrowserOpen(false)
  window.localStorage.clear()
})

it('uses the focused session cwd instead of an empty profile cwd to show Files', () => {
  // Profile memory is empty, but the focused session still has a project.
  setCurrentCwdTransient('')
  $workspaceCwdOwner.set('another-session')
  $selectedStoredSessionId.set('session-in-project')
  setSessions([{ id: 'session-in-project', cwd: '/repo/project' } as never])
  setFileBrowserOpen(true)

  expect($currentCwd.get()).toBe('')
  expect($focusedWorkspaceCwd.get()).toBe('/repo/project')
  expect($fileBrowserOpen.get()).toBe(true)

  // Using the old profile-scoped cwd here yields false; the production
  // binding must instead use the focused session's resolved workspace.
  expect(shouldShowFilesPane($currentCwd.get(), $fileBrowserOpen.get())).toBe(false)
  expect(shouldShowFilesPane($focusedWorkspaceCwd.get(), $fileBrowserOpen.get())).toBe(true)
  expect($filesPaneVisible.get()).toBe(true)

  // Closing Files or leaving the project must still hide it.
  setFileBrowserOpen(false)
  expect($filesPaneVisible.get()).toBe(false)

  setFileBrowserOpen(true)
  setSessions([])
  $selectedStoredSessionId.set(null)
  expect($focusedWorkspaceCwd.get()).toBe('')
  expect($filesPaneVisible.get()).toBe(false)
})
