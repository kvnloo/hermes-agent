import { afterEach, expect, it, vi } from 'vitest'

import { group, split } from '@/components/pane-shell/tree/model'
import { $hiddenTreePanes, $layoutTree, isPaneVisible, noteActiveTreeGroup } from '@/components/pane-shell/tree/store'
import { setFileBrowserOpen } from '@/store/layout'
import {
  $currentCwd,
  $selectedStoredSessionId,
  $workspaceCwdOwner,
  setCurrentCwdTransient,
  setSessions
} from '@/store/session'
import { $focusedWorkspaceCwd } from '@/store/session-states'
import { makeSessionInfo } from '@/test/session-info'

// Keep the real controller registration, session stores and tree visibility.
// Renderer surfaces and plugin discovery are outside this workspace gate.
vi.mock('@/contrib/plugins', () => ({ discoverBundledPlugins: vi.fn() }))
vi.mock('@/components/pane-shell/tree/renderer', () => ({ LayoutTreeRoot: () => null }))
vi.mock('@/components/assistant-ui/inline-preview-directive', () => ({ InlinePreviewDirective: () => null }))
vi.mock('../chat/browser-popout-shell', () => ({ BrowserPopoutShell: () => null }))
vi.mock('../context-menu/app-context-menu', () => ({ AppContextMenu: () => null }))
vi.mock('../hud/hud-shell', () => ({ HudShell: () => null }))
vi.mock('./panes', () => ({ FilesPane: () => null, LogsPane: () => null, ReviewPaneContent: () => null }))
vi.mock('./wiring', () => ({ ContribWiring: () => null, WiredPane: () => null }))

import './controller'

it.each(['', '/repo/stale'])(
  'shows Files for the focused session and hides detached chats with profile cwd "%s"',
  profileCwd => {
    setCurrentCwdTransient(profileCwd)
    $workspaceCwdOwner.set('another-session')
    $selectedStoredSessionId.set('session-in-project')
    setSessions([makeSessionInfo({ id: 'session-in-project', cwd: '/repo/project' })])
    $layoutTree.set(
      split('row', [
        group(['workspace'], { active: 'workspace', id: 'main' }),
        group(['files'], { active: 'files', id: 'files-group' })
      ])
    )
    noteActiveTreeGroup('main')
    setFileBrowserOpen(true)

    expect($currentCwd.get()).toBe(profileCwd)
    expect($focusedWorkspaceCwd.get()).toBe('/repo/project')
    expect($hiddenTreePanes.get().has('files')).toBe(false)
    expect(isPaneVisible('files')).toBe(true)

    setFileBrowserOpen(false)
    expect(isPaneVisible('files')).toBe(false)

    setFileBrowserOpen(true)
    setSessions([])
    $selectedStoredSessionId.set(null)
    expect($focusedWorkspaceCwd.get()).toBe('')
    expect($hiddenTreePanes.get().has('files')).toBe(true)
    expect(isPaneVisible('files')).toBe(false)
  }
)

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
