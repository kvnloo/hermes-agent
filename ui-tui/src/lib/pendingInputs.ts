import { randomUUID } from 'node:crypto'
import {
  closeSync,
  existsSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync
} from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

import type { SubmissionDestination } from '../app/submissionDestination.js'
import type { QueueItem } from '../hooks/useQueue.js'
import { t } from '../i18n/runtime.js'
import { PASTE_SNIPPET_RE } from '../protocol/paste.js'

const directory = (home?: string) =>
  join(home ?? process.env.HERMES_HOME ?? join(homedir(), '.hermes'), 'tui-pending-inputs')

const recordName = /^[0-9a-f-]{36}\.json$/
const successors = new Map<string, SubmissionDestination>()
export let pendingInputRevision = 0

type ExpansionSnapshot = NonNullable<QueueItem['expansionSnapshot']>

/** Freeze the token-only transform before the composer is cleared. Unlike a
 * function closure, these exact replacements survive an fsync/rename journal
 * and can be applied repeatedly after cold recovery or another busy retry.
 */
function snapshotExpansion(item: QueueItem): ExpansionSnapshot | undefined {
  if (item.expansionSnapshot) {
    return item.expansionSnapshot
  }
  if (!item.expand) {
    return undefined
  }

  const labels = item.display.match(PASTE_SNIPPET_RE) ?? []
  if (!labels.length) {
    return undefined
  }

  return labels.map(label => {
    // expandTokens() trims its whole result. A private wrapper keeps leading
    // and trailing whitespace *inside* the paste intact when capturing it.
    const left = `__hermes_queue_${randomUUID()}_left__`
    const right = `__hermes_queue_${randomUUID()}_right__`
    const expanded = item.expand!(left + label + right)
    const value = expanded.startsWith(left) && expanded.endsWith(right)
      ? expanded.slice(left.length, -right.length)
      : label

    return { label, value }
  })
}

function validExpansionSnapshot(value: unknown): value is ExpansionSnapshot {
  return Array.isArray(value) && value.every(
    (entry: unknown) => entry !== null && typeof entry === 'object' &&
      typeof (entry as { label?: unknown }).label === 'string' &&
      typeof (entry as { value?: unknown }).value === 'string'
  )
}

/** Reconstruct the same paste/image-token expansion; no shell commands run here.
 * A new index is used per invocation, so a retry cannot consume the mapping.
 */
function expandFromSnapshot(snapshot: ExpansionSnapshot): (value: string) => string {
  return value => {
    // Interpolation can consume earlier tokens. Match surviving labels by identity
    // and consume repeated labels in their original order.
    const remainingByLabel = new Map<string, string[]>()
    for (const { label, value: payload } of snapshot) {
      const values = remainingByLabel.get(label)
      if (values) {
        values.push(payload)
      } else {
        remainingByLabel.set(label, [payload])
      }
    }

    return value.replace(new RegExp(`[ \\t]?(?:${PASTE_SNIPPET_RE.source})`, 'g'), match => {
      const label = match.trimStart()
      const payload = remainingByLabel.get(label)?.shift()
      if (payload === undefined) {
        return match
      }
      return payload ? match.slice(0, match.length - label.length) + payload : ''
    }).trim()
  }
}

export const pendingDestinationKey = (destination: SubmissionDestination) =>
  JSON.stringify([destination.profileHome, destination.profile, destination.sid])

export function pendingInputOwner(destination: SubmissionDestination): SubmissionDestination {
  let current = destination
  const seen = new Set<string>()

  while (!seen.has(pendingDestinationKey(current))) {
    const key = pendingDestinationKey(current)
    seen.add(key)
    const next = successors.get(key)

    if (!next) {
      break
    }

    current = next
  }

  return current
}

// Resume authorizes the source → successor mapping; navigation alone does not.
export function migratePendingInputs(previous: SubmissionDestination, successorSid: string, successorStoredSid?: string): void {
  if (!previous.sid || !successorSid || (previous.sid === successorSid && previous.storedSid === successorStoredSid)) {
    return
  }

  const successor = Object.freeze({ ...previous, sid: successorSid, storedSid: successorStoredSid ?? null })

  for (const item of loadPendingInputs(previous, true)) {
    // Cold resume knows the stored ID, not the prior process's runtime handle.
    successors.set(pendingDestinationKey(item.ownerDestination ?? item.destination!), successor)
    item.ownerDestination = successor

    if (!item.failed) {
      item.destination = successor
    }

    savePendingInput(item)
  }

  successors.set(pendingDestinationKey(previous), successor)
  pendingInputRevision++
}

function syncDirectory(dir: string) {
  if (process.platform === 'win32') {
    return
  }

  const fd = openSync(dir, 'r')

  try {
    fsyncSync(fd)
  } finally {
    closeSync(fd)
  }
}

// Separate files avoid read/modify/write loss between two native clients.
export function savePendingInput(item: QueueItem): void {
  if (!item.submissionId || !item.destination?.sid) {
    return
  }

  const dir = directory(item.destination?.profileHome)
  mkdirSync(dir, { recursive: true, mode: 0o700 })
  const path = join(dir, `${item.submissionId}.json`)
  const temporary = `${path}.${process.pid}.tmp`
  const ownerDestination = pendingInputOwner(item.ownerDestination ?? item.destination)
  const durableExpansion = snapshotExpansion(item)
  if (durableExpansion) {
    item.expansionSnapshot = durableExpansion
    item.expand = expandFromSnapshot(durableExpansion)
  }
  const { submissionId, display, text, expansionSnapshot, preparedText, attachments, controlMethod, executionGeneration, inFlight, failed, createdAt, queued, legacyAttempted } = item
  const destination = inFlight || failed ? item.destination : ownerDestination
  writeFileSync(
    temporary,
    JSON.stringify({
      submissionId,
      destination,
      ownerDestination,
      display,
      text,
      expansionSnapshot,
      preparedText,
      attachments,
      controlMethod,
      executionGeneration,
      legacyAttempted,
      createdAt,
      queued,
      attempted: inFlight || failed
    }),
    { mode: 0o600, flush: true }
  )
  renameSync(temporary, path)
  syncDirectory(dir)
}

export function removePendingInput(item: QueueItem): void {
  if (!item.submissionId) {
    return
  }

  const dir = directory(item.destination?.profileHome)

  if (!existsSync(dir)) {
    return
  }

  rmSync(join(dir, `${item.submissionId}.json`), { force: true })
  syncDirectory(dir)
}

export function loadPendingInputs(destination: SubmissionDestination, durableResume = false): QueueItem[] {
  const dir = directory(destination.profileHome)

  if (!existsSync(dir)) {
    return []
  }

  return readdirSync(dir)
    .filter(name => recordName.test(name))
    .flatMap(name => {
      // A missing record is a concurrent client's acknowledgement, not corruption.
      let raw: string

      try {
        raw = readFileSync(join(dir, name), 'utf8')
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
          return []
        }

        throw error
      }

      const record = JSON.parse(raw)

      if (
        record.submissionId + '.json' !== name ||
        typeof record.text !== 'string' ||
        typeof record.display !== 'string' ||
        (record.expansionSnapshot !== undefined && !validExpansionSnapshot(record.expansionSnapshot))
      ) {
        throw new Error(t('canonical.queue.invalidRecord', name))
      }

      const owner = record.ownerDestination ?? record.destination

      if (
        (durableResume
          ? (owner?.storedSid || owner?.sid) !== (destination.storedSid || destination.sid)
          : owner?.sid !== destination.sid) ||
        owner?.profileHome !== destination.profileHome || owner?.profile !== destination.profile
      ) {
        return []
      }

      return [{
        ...record,
        ...(record.expansionSnapshot ? { expand: expandFromSnapshot(record.expansionSnapshot) } : {}),
        inFlight: false,
        failed: Boolean(record.attempted)
      }]
    })
    .sort((a, b) => (a.createdAt ?? 0) - (b.createdAt ?? 0))
}
