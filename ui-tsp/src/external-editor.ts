import { spawnSync } from 'node:child_process'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import type { App } from './app.js'

export type DraftOpener = (file: string) => void | Promise<void>

/** Fixed argv, never a shell command containing the draft or its path. */
export const openDraftFile: DraftOpener = file => {
  const inTern = Boolean(process.env.TERN_WINDOW_KEY)

  const argv = inTern
    ? ['tern', 'open', '--wait', file]
    : [...(process.env.VISUAL || process.env.EDITOR || 'vi').trim().split(/\s+/), file]

  const raw = process.stdin.isRaw

  try {
    if (!inTern && process.stdin.isTTY) {
      process.stdin.setRawMode(false)
    }

    const result = spawnSync(argv[0]!, argv.slice(1), { stdio: inTern ? 'pipe' : 'inherit' })

    if (result.error) {
      throw result.error
    }

    if (result.status !== 0) {
      throw new Error('External editor cancelled or failed; the composer draft was kept.')
    }
  } finally {
    if (!inTern && process.stdin.isTTY) {
      process.stdin.setRawMode(raw)
    }
  }
}

/** Private file round-trip shared by composer and revision-bound plan editing. */
export async function editTextExternal(initial: string, opener: DraftOpener = openDraftFile): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), 'hermes-plan-'))

  try {
    const file = join(dir, 'plan.md')
    await writeFile(file, initial, { mode: 0o600 })
    await opener(file)

    return await readFile(file, 'utf8')
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
}

const active = new WeakSet<App>()

/** A private file round-trip; concurrent/stale edits never replace a newer draft. */
export async function editExternal(app: App, opener: DraftOpener = openDraftFile): Promise<void> {
  if (active.has(app)) {
    return
  }

  active.add(app)
  const sid = app.sid
  const rev = app.composer.rev
  const initial = app.composer.text
  let dir: string | undefined

  try {
    dir = await mkdtemp(join(tmpdir(), 'hermes-draft-'))
    const file = join(dir, 'draft.txt')
    await writeFile(file, initial, { mode: 0o600 })
    await opener(file)
    const text = await readFile(file, 'utf8')

    if (app.sid === sid && app.composer.rev === rev) {
      app.composer.set(text)
    } else {
      app.transcript.panel('External editor result (draft changed while editing)', text)
    }
  } catch (error) {
    app.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
  } finally {
    if (dir) {
      await rm(dir, { recursive: true, force: true })
    }

    active.delete(app)
    app.changed()
  }
}
