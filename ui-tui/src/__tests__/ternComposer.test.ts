import { type OutMessage, Surface, type WireNode } from '@stencil-hq/tern'
import { describe, expect, it, vi } from 'vitest'

import { type ComposerSnapshot, MAX_NATIVE_DRAFT, TernComposer } from '../tern/composer.js'

function fixture() {
  const messages: OutMessage[] = []
  const surface = new Surface({ credits: () => 8, dropped() {}, send: message => messages.push(message) }, 'test', {})
  let live: ComposerSnapshot = { owner: 'session:a:epoch:1', revision: 0, text: 'buffered\nlast line', ready: true, busy: false, modal: false }
  const submit = vi.fn(() => { live = { ...live, text: '', revision: live.revision + 1, busy: true } })
  const edit = vi.fn((text: string) => { live = { ...live, text, revision: live.revision + 1 } })
  const composer = new TernComposer(surface)
  composer.bind({ read: () => live, submit, edit })

  const findEditor = (value: WireNode): string | undefined =>
    value.k === 'editor' ? value.id : value.c?.map(findEditor).find(Boolean)

  const id = () => {
    for (const message of messages.toReversed()) {
      if (message.verb === 'f') {
        for (const op of message.body.ops.toReversed()) {
          const found = op[0] === 'add' ? findEditor(op[4]) : undefined

          if (found) { return found }
        }
      }
    }

    throw new Error('editor not rendered')
  }

  return { composer, edit, id, submit, surface, set: (patch: Partial<ComposerSnapshot>) => { live = { ...live, ...patch } } }
}

// Behavioral donors: review/134833-tsp-optin-gates and downstream app-send/flow tests.
describe('bounded native composer seam', () => {
  it('submits the full atomic multiline buffer once through the existing dispatcher', () => {
    const f = fixture()
    const pending = f.surface.dispatch({ ev: 'send', id: f.id(), text: 'first line\nlast 😀', sf: 'test', raw: {} })!
    pending()
    pending()
    expect(f.submit).toHaveBeenCalledExactlyOnceWith('first line\nlast 😀')
    expect(f.edit).not.toHaveBeenCalled()
  })

  it.each([{ busy: true }, { modal: true }, { ready: false }, { owner: 'session:b:epoch:2' }, { revision: 1 }])(
    'reads live state at dispatch, even before React commits: %j', patch => {
      const f = fixture()
      const pending = f.surface.dispatch({ ev: 'send', id: f.id(), text: 'never submit', sf: 'test', raw: {} })!
      f.set(patch)
      pending()
      expect(f.submit).not.toHaveBeenCalled()
    }
  )

  it('rejects a stale event even when the replacement draft has the same length', () => {
    const f = fixture()
    const old = f.id()
    const pending = f.surface.dispatch({ ev: 'send', id: old, text: 'stale', sf: 'test', raw: {} })!
    f.set({ text: 'replaced\nlast line', revision: 1 })
    f.composer.refresh()
    pending()
    expect(f.submit).not.toHaveBeenCalled()
    expect(f.surface.dispatch({ ev: 'send', id: old, text: 'stale', sf: 'test', raw: {} })).toBeUndefined()
  })

  it('edits across the buffered multiline boundary in UTF-16 units', () => {
    const f = fixture()
    f.surface.dispatch({ ev: 'edit', id: f.id(), from: 7, to: 9, text: '\n😀', cursor: 10, len: 18, sf: 'test', raw: {} })!()
    expect(f.edit).toHaveBeenCalledExactlyOnceWith('buffere\n😀last line')
  })

  it.each([
    { from: -1, to: 2, len: 18, cursor: 0 },
    { from: 2, to: 1, len: 18, cursor: 0 },
    { from: 0, to: 1, len: 17, cursor: 0 },
    { from: 0, to: 1, len: 18, cursor: 999 }
  ])('rejects invalid or outdated native edits: %j', range => {
    const f = fixture()
    f.surface.dispatch({ ev: 'edit', id: f.id(), ...range, text: 'x', sf: 'test', raw: {} })!()
    expect(f.edit).not.toHaveBeenCalled()
  })

  it('rejects oversized or empty atomic sends without clearing the draft', () => {
    const f = fixture()

    for (const text of ['', '   ', 'x'.repeat(MAX_NATIVE_DRAFT + 1)]) {
      f.surface.dispatch({ ev: 'send', id: f.id(), text, sf: 'test', raw: {} })!()
    }

    expect(f.submit).not.toHaveBeenCalled()
    expect(f.edit).not.toHaveBeenCalled()
  })

  it('rejects a hidden native surface without changing the Ink draft', () => {
    const f = fixture()
    const pending = f.surface.dispatch({ ev: 'send', id: f.id(), text: 'never submit', sf: 'test', raw: {} })!
    f.composer.setVisible(false)
    pending()
    expect(f.submit).not.toHaveBeenCalled()
    expect(f.edit).not.toHaveBeenCalled()
    f.composer.setVisible(true)
    expect(f.id()).toBeTruthy()
  })

  it('rejects retained handler calls after gone or cleanup', () => {
    for (const close of ['gone', 'close'] as const) {
      const f = fixture()
      const pending = f.surface.dispatch({ ev: 'send', id: f.id(), text: 'never submit', sf: 'test', raw: {} })!
      close === 'gone' ? f.surface.gone() : f.composer.close()
      pending()
      expect(f.submit).not.toHaveBeenCalled()
    }
  })
})
