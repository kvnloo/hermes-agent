// A single semantic run box for Hermes terminal and execute_code tool results.
// Hermes owns outcomes; this adapter only renders the fields its gateway emitted.

import type { JSX } from '@stencil-hq/tern'

import { displayOptional, displayText } from '../display-text.js'
import type { ToolCall } from '../model.js'

import { duration } from './time.js'

export type RunState = 'running' | 'ok' | 'exit' | 'timeout' | 'cancelled' | 'background' | 'error' | 'unknown'

export interface RunBoxInput {
  command: string
  cwd?: string
  output?: string
  /** Structured output built from exact spans of the visible literal output. */
  renderOutput?: (visible: string) => JSX.Element[]
  statusNodes?: JSX.Element[]
  runKey?: string
  error?: string
  language?: string
  state: RunState
  exit?: number
  /** Present only when distinct tool.start and tool.complete events were observed. */
  elapsedMs?: number
  /** The native folded preview omits some of the retained output lines. */
  truncated?: boolean
  /** Output-only folding keeps the command, errors and status footer visible. */
  collapsed?: boolean
  onToggle?(): void
  previewLines?: number
  previewSide?: 'first' | 'last'
  background?: boolean
  processId?: number
  sessionId?: string
  /** The backend explicitly spilled its output capture (which retains head and tail). */
  captureTruncated?: boolean
  captureFacts?: string[]
  captureNote?: string
}

const RUN_WORD: Record<RunState, string> = {
  running: 'running',
  ok: 'ok',
  exit: 'exit',
  timeout: 'timeout',
  cancelled: 'cancelled',
  background: 'background',
  error: 'error',
  unknown: 'no result recorded'
}

const RUN_TONE: Record<RunState, 'pending' | 'muted' | 'success' | 'warning' | 'error'> = {
  running: 'pending',
  ok: 'success',
  exit: 'error',
  timeout: 'warning',
  cancelled: 'muted',
  background: 'pending',
  error: 'error',
  unknown: 'muted'
}

function numericExit(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isSafeInteger(value) ? value : undefined
}

function namedSession(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined
}

/**
 * Status precedence follows Hermes's terminal_tool result envelope.
 * In particular, background spawn success is NOT foreground exit 0.
 */
export function runState(call: ToolCall, result: Record<string, unknown> | undefined): RunState {
  if (call.status === 'unknown') {
    return 'unknown'
  }

  const status = result?.status
  const error = typeof result?.error === 'string' ? result.error : ''
  const output = typeof result?.output === 'string' ? result.output : ''
  const exit = numericExit(result?.exit_code)

  if (call.status === 'cancelled' || status === 'cancelled' || status === 'interrupted') {
    return 'cancelled'
  }

  if (
    !error &&
    (status === 'yielded_to_background' ||
      (namedSession(result?.session_id) && (call.args.background === true || numericExit(result?.pid) !== undefined)))
  ) {
    return 'background'
  }

  // Foreground finalization retains the executor's timeout suffix, but not
  // its internal hermes_timed_out flag. Plain exit 124 is still just an exit.
  if (
    status === 'timeout' ||
    (exit === 124 &&
      (/^Command timed out after \d+(?:\.\d+)? seconds\b/i.test(error) ||
        /(?:^|\n)\[Command timed out after \d+(?:\.\d+)?s\]\s*$/.test(output)))
  ) {
    return 'timeout'
  }

  if (call.status === 'running') {
    return 'running'
  }

  if ((error || status === 'error' || call.status === 'error') && (exit === undefined || exit === -1 || exit === 0)) {
    return 'error'
  }

  if (exit !== undefined) {
    return exit === 0 && !error ? 'ok' : 'exit'
  }

  return call.status === 'error' || status === 'error' || error ? 'error' : 'ok'
}

/**
 * Avoid synthesized duration facts: a late tool.complete can manufacture a
 * matching start for transcript recovery, which is NOT a measured interval.
 */
export function runElapsed(call: ToolCall): number | undefined {
  if (
    call.startedObserved !== true ||
    typeof call.finishedAt !== 'number' ||
    !Number.isFinite(call.startedAt) ||
    !Number.isFinite(call.finishedAt) ||
    call.finishedAt < call.startedAt ||
    call.status === 'running'
  ) {
    return undefined
  }

  return call.finishedAt - call.startedAt
}

export function outputLineCount(output: string): number {
  return output ? output.replace(/\n$/, '').split('\n').length : 0
}

/** Testable, source-grounded footer facts; formatting never creates outcomes. */
export function runFootFacts(input: RunBoxInput): string[] {
  const facts: string[] = []
  const exit = numericExit(input.exit)

  if (
    exit !== undefined &&
    exit !== -1 &&
    input.state !== 'background' &&
    input.state !== 'running' &&
    input.state !== 'exit'
  ) {
    facts.push('exit ' + exit)
  }

  if (input.state === 'background') {
    if (numericExit(input.processId) !== undefined) {
      facts.push('pid ' + input.processId)
    } else if (input.sessionId) {
      facts.push('session ' + input.sessionId)
    }
  }

  if (
    input.elapsedMs !== undefined &&
    Number.isFinite(input.elapsedMs) &&
    input.elapsedMs >= 0 &&
    input.state !== 'running' &&
    input.state !== 'background'
  ) {
    facts.push(duration(input.elapsedMs))
  }

  const lines = outputLineCount(input.output ?? '')
  const limit = numericExit(input.previewLines)

  if (input.truncated && input.collapsed !== false && limit !== undefined && limit > 0 && lines > limit) {
    facts.push('truncated: showing ' + (input.previewSide === 'first' ? 'first ' : 'last ') + limit + ' lines')
  }

  if (input.captureTruncated) {
    facts.push(input.captureNote ?? 'capture truncated: head + tail retained')
  }

  return [...facts, ...(input.captureFacts ?? [])]
}

/** One run: input, live/retained output, optional error and factual state footer. */
export function runBox(input: RunBoxInput): JSX.Element {
  const word =
    input.state === 'exit' && numericExit(input.exit) !== undefined ? 'exit ' + input.exit : RUN_WORD[input.state]

  const facts = runFootFacts(input)
  const tone = RUN_TONE[input.state]
  const lines = (input.output ?? '').replace(/\n$/, '').split('\n')
  const limit = input.previewLines ?? lines.length
  const folded = input.truncated && input.collapsed !== false

  const output = folded
    ? (input.previewSide === 'first' ? lines.slice(0, limit) : lines.slice(-limit)).join('\n')
    : input.output

  return (
    <col gap="none" key={input.runKey ?? 'run'} role="omp.run" tone={tone}>
      <row align="start" gap="xs" key="input" role="omp.run.input">
        <icon aria="Input" key="prompt" name="arrow-left" role="omp.run.prompt" />
        <code key="code" lang={input.language ?? 'bash'} numbers={false} text={displayText(input.command)} wrap />
      </row>
      {input.cwd ? <text key="cwd" role="omp.run.cwd" spans={[{ s: 'muted', t: displayText(input.cwd) }]} wrap="word" /> : null}
      {input.output || input.error ? (
        <row align="start" gap="xs" key="result" role="omp.run.result">
          <icon aria="Output" key="prompt" name="arrow-right" role="omp.run.prompt" />
          <col gap="none" key="outputs" role="omp.run.outputs">
            {input.output ? (
              input.renderOutput ? input.renderOutput(output ?? '') : <code key="output" lang="text" numbers={false} role="omp.run.output" text={displayOptional(output)} wrap />
            ) : null}
            {input.error ? (
              <text
                key="error"
                role="omp.tool.error"
                spans={[{ s: input.state === 'timeout' ? 'warning' : 'error', t: displayText(input.error) }]}
                wrap="word"
              />
            ) : null}
          </col>
        </row>
      ) : null}
      {input.statusNodes}
      <row align="center" gap="sm" key="foot" role="omp.run.foot" wrap>
        <text key="state" role="omp.run.state" spans={[{ s: tone, t: word }]} />
        {facts.length ? (
          <text key="facts" role="omp.run.facts" spans={[{ s: 'muted', t: displayText(facts.join(' · ')) }]} wrap="word" />
        ) : null}
        {input.truncated && input.onToggle ? (
          <text
            key="toggle"
            onClick={input.onToggle}
            role="omp.run.toggle"
            text={folded ? 'Show all output' : 'Show less output'}
          />
        ) : null}
      </row>
    </col>
  )
}
