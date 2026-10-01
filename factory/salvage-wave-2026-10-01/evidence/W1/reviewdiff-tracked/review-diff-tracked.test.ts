import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test } from 'vitest'

import { reviewDiff } from './git-review-ops'

// Behaviour contract: reviewDiff (unstaged) never renders a tracked file as a
// new-file all-add. An empty unstaged diff also means a clean or fully staged
// tracked file (e.g. `git add` after the renderer's reviewList snapshot, so
// the row still says staged=false); only a file git doesn't know yet gets the
// synthesized all-add. Real git, no child_process mock.

const tempDirs: string[] = []

afterEach(() => {
  for (const dir of tempDirs.splice(0)) {
    fs.rmSync(dir, { force: true, recursive: true })
  }
})

function makeRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-review-diff-tracked-'))

  tempDirs.push(dir)
  execFileSync('git', ['init', '-q'], { cwd: dir })
  execFileSync('git', ['config', 'user.email', 'hermes-test@example.com'], { cwd: dir })
  execFileSync('git', ['config', 'user.name', 'Hermes Test'], { cwd: dir })
  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'tracked\n')
  execFileSync('git', ['add', 'tracked.txt'], { cwd: dir })
  execFileSync('git', ['commit', '-qm', 'initial'], { cwd: dir })

  return dir
}

test('reviewDiff (unstaged) never renders a tracked file as a new-file all-add', async () => {
  const dir = makeRepo()

  // Pristine tracked file: nothing unstaged to show.
  assert.equal(await reviewDiff(dir, 'tracked.txt', 'uncommitted', null, false, 'git'), '')

  // Fully staged after the renderer's reviewList snapshot (stale staged=false).
  fs.writeFileSync(path.join(dir, 'tracked.txt'), 'tracked\nstaged edit\n')
  execFileSync('git', ['add', 'tracked.txt'], { cwd: dir })
  assert.equal(await reviewDiff(dir, 'tracked.txt', 'uncommitted', null, false, 'git'), '')
})

test('reviewDiff (unstaged) still synthesizes an all-add for an untracked file', async () => {
  const dir = makeRepo()

  fs.writeFileSync(path.join(dir, 'new.txt'), 'fresh\n')

  const diff = await reviewDiff(dir, 'new.txt', 'uncommitted', null, false, 'git')

  assert.match(diff, /new file mode/)
  assert.match(diff, /\+fresh/)
})
