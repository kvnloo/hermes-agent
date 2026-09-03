import { type ChildProcess, execFileSync } from 'node:child_process'
import { accessSync, constants } from 'node:fs'
import { delimiter, join, resolve, win32 } from 'node:path'

export type RealtimeVoiceLane = 'codex' | 'default'

export interface RealtimeVoiceLaunch {
  command: string
  args: string[]
  killTree?: boolean
}

export interface RealtimeVoiceLaunchEnvironment {
  ComSpec?: string
  HERMES_PYTHON?: string
  HERMES_PYTHON_SRC_ROOT?: string
  PATH?: string
  Path?: string
  PATHEXT?: string
}

export const executableOnPath = (
  name: string,
  pathValue: string | undefined,
  platform: NodeJS.Platform = process.platform,
  pathExtValue = process.env.PATHEXT
): string | null => {
  const pathDelimiter = platform === 'win32' ? win32.delimiter : delimiter

  const extensions =
    platform === 'win32'
      ? (pathExtValue || '.COM;.EXE;.BAT;.CMD')
          .split(';')
          .filter(Boolean)
          .map(extension => (extension.startsWith('.') ? extension : `.${extension}`))
      : ['']

  const accessMode = platform === 'win32' ? constants.F_OK : constants.X_OK

  for (const directory of (pathValue ?? '').split(pathDelimiter)) {
    if (!directory) {
      continue
    }

    for (const extension of extensions) {
      const candidate = join(directory, `${name}${extension}`)

      try {
        accessSync(candidate, accessMode)

        return candidate
      } catch {
        // Continue searching PATH and, on Windows, PATHEXT.
      }
    }
  }

  return null
}

const CMD_SHIM_PATTERN = /\.(?:bat|cmd)$/i
const CMD_META_PATTERN = /([()%!^"`<>&|;, *?])/g

const escapeCmdToken = (value: string): string => value.replace(CMD_META_PATTERN, '^$1')

export const buildCmdShimCommandLine = (executable: string, args: readonly string[] = []): string => {
  const escapedArgs = args.map(argument => {
    const quoted = argument.replace(/(\\*)"/g, '$1$1\\"').replace(/(\\*)$/, '$1$1')

    return `"${escapeCmdToken(quoted)}"`
  })

  return `"${[escapeCmdToken(executable), ...escapedArgs].join(' ')}"`
}

export const resolveRealtimeVoiceLaunch = (
  lane: RealtimeVoiceLane,
  environment: RealtimeVoiceLaunchEnvironment = process.env,
  findExecutable: (name: string, pathValue: string | undefined) => string | null = (name, pathValue) =>
    executableOnPath(name, pathValue, process.platform, environment.PATHEXT)
): RealtimeVoiceLaunch | null => {
  if (lane === 'codex') {
    const installed = findExecutable('hermes-codex-live', environment.PATH ?? environment.Path)

    if (!installed) {
      return null
    }

    return CMD_SHIM_PATTERN.test(installed)
      ? {
          command: environment.ComSpec?.trim() || 'cmd.exe',
          args: ['/d', '/s', '/c', buildCmdShimCommandLine(installed)],
          killTree: true
        }
      : { command: installed, args: [] }
  }

  const python = environment.HERMES_PYTHON?.trim()
  const sourceRoot = environment.HERMES_PYTHON_SRC_ROOT?.trim()

  return python && sourceRoot ? { command: python, args: ['-u', resolve(sourceRoot, 'hermes'), 'talk'] } : null
}

export interface RealtimeVoiceStopDependencies {
  killProcessTree?: (pid: number, force: boolean) => void
  platform?: NodeJS.Platform
}

let activeProcess: ChildProcess | null = null
let activeProcessNeedsTreeKill = false
let stopPromise: Promise<void> | null = null
const backpressuredInputs = new WeakSet<NonNullable<ChildProcess['stdin']>>()

export function writeRealtimeVoiceControl(child: ChildProcess, payload: string, required = true): void {
  const input = child.stdin

  if (!input?.writable || (!required && backpressuredInputs.has(input))) {
    return
  }

  if (!input.write(payload)) {
    backpressuredInputs.add(input)
    input.once('drain', () => backpressuredInputs.delete(input))
  }
}

export const registerRealtimeVoiceProcess = (child: ChildProcess, launch?: RealtimeVoiceLaunch): void => {
  if (activeProcess && activeProcess !== child) {
    throw new Error('A native realtime voice process is already registered.')
  }

  activeProcess = child
  activeProcessNeedsTreeKill = launch?.killTree === true
}

export const unregisterRealtimeVoiceProcess = (child: ChildProcess): void => {
  if (activeProcess === child) {
    activeProcess = null
    activeProcessNeedsTreeKill = false
  }
}

export const stopRegisteredRealtimeVoiceProcess = (
  graceMs = 1_500,
  dependencies: RealtimeVoiceStopDependencies = {}
): Promise<void> => {
  if (stopPromise) {
    return stopPromise
  }

  const child = activeProcess

  if (!child || child.exitCode !== null || child.signalCode !== null) {
    activeProcess = null
    activeProcessNeedsTreeKill = false

    return Promise.resolve()
  }

  const treeKill =
    activeProcessNeedsTreeKill && (dependencies.platform ?? process.platform) === 'win32' && Number.isInteger(child.pid)

  const killProcessTree =
    dependencies.killProcessTree ??
    ((pid: number, force: boolean) => {
      execFileSync('taskkill', ['/pid', String(pid), '/T', ...(force ? ['/F'] : [])], { stdio: 'ignore' })
    })

  const stopChild = (force: boolean): boolean => {
    if (treeKill) {
      killProcessTree(child.pid!, force)

      return true
    }

    return child.kill(force ? 'SIGKILL' : 'SIGINT')
  }

  let resolveStop: () => void = () => {}

  const promise = new Promise<void>(resolve => {
    resolveStop = resolve
  })

  let settled = false

  const finish = () => {
    if (settled) {
      return
    }

    settled = true
    clearTimeout(timer)
    child.off('exit', finish)
    resolveStop()
  }

  const timer = setTimeout(() => {
    try {
      stopChild(true)
    } finally {
      finish()
    }
  }, graceMs)

  child.once('exit', finish)

  try {
    if (!stopChild(false)) {
      finish()
    }
  } catch {
    if (!treeKill) {
      finish()
    } else {
      try {
        stopChild(true)
      } catch {
        // The process tree may already be gone.
      } finally {
        finish()
      }
    }
  }

  const stopping = promise.finally(() => {
    if (activeProcess === child) {
      activeProcess = null
      activeProcessNeedsTreeKill = false
    }

    stopPromise = null
  })

  stopPromise = stopping

  return stopping
}

export type RealtimeVoicePhase = 'composing' | 'listening' | 'solving'
export const MAX_REALTIME_VOICE_FRAME_CHARS = 65_536
export const MAX_REALTIME_VOICE_TEXT_CHARS = 10_000

export interface RealtimeVoiceTranscript {
  final: boolean
  role: 'assistant' | 'user'
  text: string
}

export interface RealtimeVoiceEnvelope {
  protocol_version: 1
  sequence: number
  surface_session_id: string
}

export interface RealtimeVoiceCanonicalIdentity {
  realtime_epoch: number
  realtime_sequence: number
  realtime_session_id: string
  realtime_turn_id: string | null
}
export type RealtimeVoiceEvent = RealtimeVoiceEnvelope &
  Partial<RealtimeVoiceCanonicalIdentity> &
  (
    | { type: 'delegate'; id: string; request: string }
    | { type: 'error'; message: string }
    | { type: 'warning'; message: string }
    | { type: 'metric'; name: string; value_ms: number }
    | ({ type: 'transcript' } & RealtimeVoiceTranscript)
  )

export class RealtimeVoiceOrderGuard {
  private surfaceSessionId: string | null = null
  private surfaceSequence = 0
  private realtimeSessionId: string | null = null
  private realtimeSequence = 0
  private realtimeEpoch = 0

  accept(event: RealtimeVoiceEvent): boolean {
    if (
      (this.surfaceSessionId !== null && event.surface_session_id !== this.surfaceSessionId) ||
      event.sequence <= this.surfaceSequence
    ) {
      return false
    }

    if (
      event.realtime_session_id !== undefined &&
      ((this.realtimeSessionId !== null && event.realtime_session_id !== this.realtimeSessionId) ||
        event.realtime_sequence === undefined ||
        event.realtime_sequence <= this.realtimeSequence ||
        event.realtime_epoch === undefined ||
        event.realtime_epoch < this.realtimeEpoch)
    ) {
      return false
    }

    this.surfaceSessionId = event.surface_session_id
    this.surfaceSequence = event.sequence

    if (event.realtime_session_id !== undefined) {
      this.realtimeSessionId = event.realtime_session_id
      this.realtimeSequence = event.realtime_sequence!
      this.realtimeEpoch = event.realtime_epoch!
    }

    return true
  }
}
const EVENT_PREFIX = 'talk: event '

const STATE_PREFIX = 'talk: state '

export const parseRealtimeVoicePhase = (line: string): RealtimeVoicePhase | null => {
  if (!line.startsWith(STATE_PREFIX)) {
    return null
  }

  if (line.length > MAX_REALTIME_VOICE_FRAME_CHARS) {
    return null
  }

  const phase = line.slice(STATE_PREFIX.length).trim()

  return phase === 'listening' || phase === 'solving' || phase === 'composing' ? phase : null
}

export const isRealtimeVoiceReadyPhase = (phase: RealtimeVoicePhase | null): boolean => phase === 'listening'

export const parseRealtimeVoiceEvent = (line: string): RealtimeVoiceEvent | null => {
  if (line.length > MAX_REALTIME_VOICE_FRAME_CHARS) {
    return null
  }

  if (!line.startsWith(EVENT_PREFIX)) {
    return null
  }

  try {
    const value: unknown = JSON.parse(line.slice(EVENT_PREFIX.length))

    if (!value || typeof value !== 'object') {
      return null
    }

    const event = value as Record<string, unknown>

    if (
      event.protocol_version !== 1 ||
      typeof event.surface_session_id !== 'string' ||
      !event.surface_session_id ||
      !Number.isSafeInteger(event.sequence) ||
      Number(event.sequence) < 1
    ) {
      return null
    }

    const envelope: RealtimeVoiceEnvelope = {
      protocol_version: 1,
      surface_session_id: event.surface_session_id,
      sequence: Number(event.sequence)
    }

    const hasCanonicalIdentity = [
      event.realtime_session_id,
      event.realtime_turn_id,
      event.realtime_epoch,
      event.realtime_sequence
    ].some(item => item !== undefined)

    let canonicalIdentity: Partial<RealtimeVoiceCanonicalIdentity> = {}

    if (hasCanonicalIdentity) {
      if (
        typeof event.realtime_session_id !== 'string' ||
        !event.realtime_session_id ||
        !(
          event.realtime_turn_id === null ||
          (typeof event.realtime_turn_id === 'string' && event.realtime_turn_id.length > 0)
        ) ||
        !Number.isSafeInteger(event.realtime_epoch) ||
        Number(event.realtime_epoch) < 0 ||
        !Number.isSafeInteger(event.realtime_sequence) ||
        Number(event.realtime_sequence) < 1
      ) {
        return null
      }

      canonicalIdentity = {
        realtime_session_id: event.realtime_session_id,
        realtime_turn_id: event.realtime_turn_id,
        realtime_epoch: Number(event.realtime_epoch),
        realtime_sequence: Number(event.realtime_sequence)
      }
    }

    const eventEnvelope = { ...envelope, ...canonicalIdentity }

    if (
      event.type === 'delegate' &&
      typeof event.id === 'string' &&
      event.id.length > 0 &&
      typeof event.request === 'string' &&
      event.request.trim()
    ) {
      return { ...eventEnvelope, type: 'delegate', id: event.id, request: event.request.trim() }
    }

    if (event.type === 'error' && typeof event.message === 'string' && event.message.trim()) {
      return { ...eventEnvelope, type: 'error', message: event.message.trim() }
    }

    if (
      event.type === 'metric' &&
      typeof event.name === 'string' &&
      event.name.length > 0 &&
      typeof event.value_ms === 'number' &&
      Number.isFinite(event.value_ms) &&
      event.value_ms >= 0
    ) {
      return { ...eventEnvelope, type: 'metric', name: event.name, value_ms: event.value_ms }
    }

    if (event.type === 'warning' && typeof event.message === 'string' && event.message.trim()) {
      return { ...eventEnvelope, type: 'warning', message: event.message.trim() }
    }

    if (
      event.type === 'transcript' &&
      (event.role === 'user' || event.role === 'assistant') &&
      typeof event.text === 'string' &&
      typeof event.final === 'boolean'
    ) {
      return {
        ...eventEnvelope,
        type: 'transcript',
        role: event.role,
        text: event.text,
        final: event.final
      }
    }
  } catch {
    return null
  }

  return null
}

export const encodeRealtimeVoiceDelegationResult = (id: string, output: string): string =>
  `${JSON.stringify({
    type: 'delegate.result',
    id,
    output: output.slice(0, MAX_REALTIME_VOICE_TEXT_CHARS)
  })}\n`

export const encodeRealtimeVoiceDelegationProgress = (id: string, text: string): string =>
  `${JSON.stringify({
    type: 'delegate.progress',
    id,
    text: text.slice(0, MAX_REALTIME_VOICE_TEXT_CHARS)
  })}\n`
