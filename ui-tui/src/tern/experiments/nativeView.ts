import { TERN_UX_FIXTURE } from './fixture.js'

/** Fixture-only projection. No gateway, shell, provider or user state is read. */
export interface FixtureNode {
  id: string
  k: string
  p?: Record<string, unknown>
  c?: FixtureNode[]
}

export interface FixtureView {
  main: FixtureNode
  dock: FixtureNode
  layer: FixtureNode
}

export type FixturePanel = 'approval' | 'models' | 'inspector' | 'preview'

export interface NativeFixtureState {
  step: number
  decision: 'allow' | 'deny' | null
  model: string
  panel: FixturePanel | 'auto' | null
}

export const NATIVE_FIXTURE_SURFACE = 'hermes:ux:preview'
export const NATIVE_FIXTURE_REVISION = 'native-a-v1'
export const FIXTURE_MODELS = ['fixture/primary', 'fixture/alternate'] as const
export const INITIAL_NATIVE_FIXTURE: NativeFixtureState = { step: 0, decision: null, model: FIXTURE_MODELS[0], panel: 'auto' }

const node = (id: string, k: string, p: Record<string, unknown> = {}, c?: FixtureNode[]): FixtureNode =>
  ({ id, k, p, ...(c ? { c } : {}) })
const text = (id: string, value: string, p: Record<string, unknown> = {}): FixtureNode =>
  node(id, 'text', { text: value, ...p })
const button = (id: string, label: string, action: string): FixtureNode =>
  text(id, label, { actions: { click: action }, tone: 'accent' })

export function fixturePanel(state: NativeFixtureState): FixturePanel | null {
  if (state.panel !== 'auto') return state.panel
  return ({ 7: 'approval', 10: 'models', 11: 'inspector', 12: 'preview' } as Record<number, FixturePanel>)[state.step] ?? null
}

const overlay = (id: string, title: string, children: FixtureNode[]): FixtureNode =>
  node(id, 'overlay', { title, role: 'hermes.ux.inspector' }, [
    text(`${id}:title`, title, { tone: 'accent' }),
    ...children,
    button(`${id}:close`, 'Return to chat', 'return-chat')
  ])

/** The OMP user/composer roles deliberately opt A into Tern's built-in OMP skin.
 * Shape reference: Can Bölük / Stencil Labs, OMP d9ee5e6a31 user-message.ts
 * and custom-editor.ts. These are fixture proposals, never reference captures. */
export function renderNativeFixture(state: NativeFixtureState): FixtureView {
  const step = TERN_UX_FIXTURE[state.step]
  if (!step) throw new RangeError(`Unknown fixture step ${state.step}`)
  const main: FixtureNode[] = []
  const dock: FixtureNode[] = []
  const layer: FixtureNode[] = []
  const panel = fixturePanel(state)
  const active = state.step > 0 && state.step < 9

  if (state.step > 0) {
    main.push(node('request', 'card', { role: 'omp.user', tone: 'user' }, [
      node('request:text', 'md', { text: 'Keep the existing API. Reject an empty task title and add a regression test.' })
    ]))
    main.push(node('answer', 'md', {
      role: 'hermes.ux.answer',
      text: state.step < 3
        ? 'I will inspect the task parser.'
        : 'I will inspect the task parser. Then add the smallest validation and regression test.'
    }))
  }
  if (state.step >= 3) {
    main.push(node('read', 'tool', {
      name: 'read', title: 'Read', target: 'src/tasks.ts', targetKind: 'path',
      status: state.step === 3 ? 'running' : 'done', collapsible: true, collapsed: state.step > 3
    }, [node('read:body', 'code', { lang: 'typescript', text: 'export const taskTitle = (value: string) => value.trim()' })]))
  }
  if (state.step >= 4) {
    main.push(node('edit', 'tool', {
      name: 'edit', title: 'Edit', target: 'src/tasks.ts', targetKind: 'path',
      status: state.step === 4 ? 'running' : 'done', collapsible: true, collapsed: state.step > 4
    }, [node('edit:body', 'diff', { text: '@@ -1 +1,4 @@\n-export const taskTitle = (value: string) => value.trim()\n+export function taskTitle(value: string) {\n+  if (!value.trim()) throw new Error("Title required")\n+  return value.trim()\n+}' })]))
  }
  if (state.step >= 5) {
    main.push(node('reviewer', 'agent', {
      name: 'Review', task: 'Check the empty-title edge case',
      status: state.step < 9 ? 'running' : 'done', collapsible: true, collapsed: state.step >= 9
    }, [text('reviewer:body', 'Fixture worker: verify whitespace-only and non-empty titles.')]))
  }
  if (state.step >= 8) {
    // Failed history remains failed after recovery; the retry is a different call.
    main.push(node('test:first', 'tool', {
      name: 'bash', title: 'Test', target: 'npm test -- tasks', targetKind: 'command',
      status: 'error', exit: 1, note: 'Fixture failure', collapsible: true, collapsed: state.step >= 9
    }, [text('test:first:body', 'Expected the whitespace-only case to reject; the fixture test still uses the old expectation.')]))
    main.push(node('test:retry', 'tool', {
      name: 'bash', title: 'Retry', target: 'npm test -- tasks', targetKind: 'command',
      status: state.step === 8 ? 'running' : 'done', collapsible: true, collapsed: state.step >= 9
    }, [text('test:retry:body', state.step === 8 ? 'Fixture recovery in progress.' : 'Fixture result: 2 tests passed. No tests were executed by this preview.')]))
  }
  if (state.step >= 9) {
    main.push(node('result', 'md', {
      text: '**Fixture complete.** Empty titles are rejected; non-empty titles retain the same API.\n\nThis is simulated review content, not an executed code change.'
    }))
  }
  if (state.step === 0) {
    main.push(node('welcome', 'md', { text: '# Hermes\nNative Tern UX fixture. Use **Next** to inspect the same task across its states.' }))
  }

  // The lab controls are conspicuously separate from the proposed app chrome.
  dock.push(text('lab:notice', 'UX FIXTURE — no model calls, commands, approvals or files are executed', { tone: 'muted' }))
  dock.push(node('lab:nav', 'row', { wrap: true, gap: 'sm' }, [
    button('lab:prev', 'Previous [p]', 'previous'),
    text('lab:step', `${state.step + 1}/${TERN_UX_FIXTURE.length} · ${step.title}`),
    button('lab:next', 'Next [n]', 'next'),
    button('lab:reset', 'Reset [r]', 'reset'),
    button('lab:quit', 'Quit [q]', 'quit')
  ]))
  if (active) {
    dock.push(text('work', step.expectedDoing, { tone: state.step === 7 ? 'warning' : 'muted' }))
  }
  if (state.step >= 6 && state.step < 9) {
    dock.push(text('queue', '1 queued · Keep the API unchanged.', { tone: 'muted' }))
  }
  dock.push(node('composer', 'col', { role: 'omp.composer' }, [
    node('composer:line', 'row', { role: 'omp.composer.line', align: 'start' }, [
      node('composer:editor', 'editor', {
        role: 'omp.editor', text: 'Keep the API unchanged.', readonly: true,
        sendable: false, maxLines: 6, placeholder: 'Fixture composer (read-only)'
      })
    ]),
    node('composer:facts', 'row', { wrap: true, gap: 'sm' }, [
      button('composer:model', state.model, 'models'),
      text('composer:cwd', 'fixture/tasks · no real checkout', { tone: 'muted' }),
      button('composer:inspect', 'Inspect', 'inspect')
    ])
  ]))
  if (panel === 'approval') {
    layer.push(overlay('approval', 'Fixture approval', [
      node('approval:command', 'code', { lang: 'sh', text: 'npm test -- tasks' }),
      text('approval:explanation', 'Simulate a decision. These controls cannot authorize or run a real command.'),
      node('approval:actions', 'row', {}, [
        button('approval:allow', 'Simulate allow', 'allow'),
        button('approval:deny', 'Simulate deny', 'deny')
      ]),
      text('approval:decision', state.decision ? `Recorded locally: ${state.decision}` : 'No fixture decision yet.')
    ]))
  }
  if (panel === 'models') {
    layer.push(overlay('models', 'Fixture model picker', FIXTURE_MODELS.map((model, index) =>
      button(`models:${index}`, `${state.model === model ? 'Selected: ' : ''}${model}`, `model-${index}`)
    )))
  }
  if (panel === 'inspector') {
    layer.push(overlay('inspector', 'Fixture background inspector', [
      text('inspector:worker', state.step < 5 ? 'No fixture worker has started.' : state.step < 9 ? 'Review · running · checking whitespace-only titles' : 'Review · completed · whitespace-only case checked'),
      text('inspector:history', state.step < 8 ? 'No test attempts yet. No live process is attached.' : 'A failed test attempt is separate from its retry. No live process is attached.')
    ]))
  }
  if (panel === 'preview') {
    layer.push(overlay('preview', 'Fixture file preview — not a host split', [
      node('preview:body', 'code', { lang: 'typescript', text: 'expect(() => taskTitle("   ")).toThrow("Title required")' }),
      text('preview:limit', 'This preview does not open a browser or create a Tern pane. Host split behavior still needs live capture.')
    ]))
  }
  return {
    main: node('main', 'col', {}, main),
    dock: node('dock', 'col', {}, dock),
    layer: node('layer', 'col', {}, layer)
  }
}

export function fixtureNodes(view: FixtureView): FixtureNode[] {
  const out: FixtureNode[] = []
  const visit = (item: FixtureNode) => { out.push(item); item.c?.forEach(visit) }
  Object.values(view).forEach(visit)
  return out
}

export function fixtureRequiredKinds(): string[] {
  return [...new Set(TERN_UX_FIXTURE.flatMap((_, step) =>
    fixtureNodes(renderNativeFixture({ ...INITIAL_NATIVE_FIXTURE, step })).map(item => item.k)
  ))].sort()
}

export function reduceNativeFixture(state: NativeFixtureState, action: string): NativeFixtureState {
  switch (action) {
    case 'next': return { ...state, step: Math.min(TERN_UX_FIXTURE.length - 1, state.step + 1), panel: 'auto' }
    case 'previous': return { ...state, step: Math.max(0, state.step - 1), panel: 'auto' }
    case 'reset': return { ...INITIAL_NATIVE_FIXTURE }
    case 'models': return { ...state, panel: 'models' }
    case 'inspect': return { ...state, panel: 'inspector' }
    case 'return-chat': return { ...state, panel: null }
    case 'allow': case 'deny': return fixturePanel(state) === 'approval' ? { ...state, decision: action } : state
    case 'model-0': case 'model-1':
      return fixturePanel(state) === 'models' ? { ...state, model: FIXTURE_MODELS[action === 'model-0' ? 0 : 1] } : state
    default: return state
  }
}
