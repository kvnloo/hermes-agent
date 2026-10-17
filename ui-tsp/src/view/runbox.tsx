// A single semantic run box for Hermes terminal and execute_code tool results.
// Hermes owns outcomes; this adapter only renders the fields its gateway emitted.

import type { JSX } from '@stencil-hq/tern'

import type { ToolCall } from '../model.js'

import { duration } from './time.js'

export type RunState = 'running' | 'ok' | 'exit' | 'timeout' | 'cancelled' | 'background' | 'error'

export interface RunBoxInput {
  command: string
  cwd?: string
  output?: string
  error?: string
  language?: string
  state: RunState
  exit?: number
  /** Present only when distinct tool.start and tool.complete events were observed. */
  elapsedMs?: number
  /** The native folded preview omits some of the retained output lines. */
  truncated?: boolean
  previewLines?: number
  previewSide?: 'first' | 'last'
  background?: boolean
  processId?: number
  sessionId?: string
  /** The backend explicitly spilled its output capture (which retains head and tail). */
  captureTruncated?: boolean
}

const RUN_WORD: Record<RunState, string> = {
  running: 'running',
  ok: 'ok',
  exit: 'exit',
  timeout: 'timeout',
  cancelled: 'cancelled',
  background: 'background',
  error: 'error'
}

const RUN_TONE: Record<RunState, 'muted' | 'success' | 'warning' | 'error'> = {
  running: 'muted',
  ok: 'success',
  exit: 'error',
  timeout: 'warning',
  cancelled: 'muted',
  background: 'muted',
  error: 'error'
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
  const status = result?.status
  const error = typeof result?.error === 'string' ? result.error : ''
  const exit = numericExit(result?.exit_code)

  if (call.status === 'cancelled' || status === 'cancelled' || status === 'interrupted') {
    return 'cancelled'
  }

  if (!error && (status === 'yielded_to_background' ||
    (namedSession(result?.session_id) && (call.args.background === true || numericExit(result?.pid) !== undefined)))) {
    return 'background'
  }

  // Hermes catches backend timeout exceptions as exit=124 with this
  // message, not a dedicated timeout boolean. Plain `exit 124` is NOT
  // necessarily a timeout and stays a normal nonzero command exit.
  if (status === 'timeout' || status === 'timed_out' || status === 'hermes_timed_out' ||
    (exit === 124 && /^Command timed out after \d+(?:\.\d+)? seconds\b/i.test(error))) {
    return 'timeout'
  }

  if (call.status === 'running') {
    return 'running'
  }

  if (error && (exit === undefined || exit === -1 || exit === 0)) {
    return 'error'
  }

  if (exit !== undefined) {
    return exit === 0 && !error ? 'ok' : 'exit'
  }

  return call.status === 'error' || error ? 'error' : 'ok'
}

/**
 * Avoid synthesized duration facts: a late tool.complete can manufacture a
 * matching start for transcript recovery, which is NOT a measured interval.
 */
export function runElapsed(call: ToolCall): number | undefined {
  if (call.startedObserved !== true || typeof call.finishedAt !== 'number' ||
    !Number.isFinite(call.startedAt) || !Number.isFinite(call.finishedAt) ||
    call.finishedAt < call.startedAt || call.status === 'running') {
    return undefined
  }

  return call.finishedAt - call.startedAt
}

function outputLineCount(output: string): number {
  return output ? output.replace(/\n$/, '').split('\n').length : 0
}

/** Testable, source-grounded footer facts; formatting never creates outcomes. */
export function runFootFacts(input: RunBoxInput): string[] {
  const facts: string[] = []
  const exit = numericExit(input.exit)

  if (input.state === 'ok' && exit === 0) {
    facts.push('exit 0')
  } else if (input.state === 'exit' && exit !== undefined) {
    // State text already says `exit N`; do not repeat it.
  } else if (input.state === 'background') {
    if (numericExit(input.processId) !== undefined) {
      facts.push('pid ' + input.processId)
    } else if (input.sessionId) {
      facts.push('session ' + input.sessionId)
    }
  }

  if (input.elapsedMs !== undefined && Number.isFinite(input.elapsedMs) && input.elapsedMs >= 0 &&
      input.state !== 'running' && input.state !== 'background') {
    facts.push(duration(input.elapsedMs))
  }

  const lines = outputLineCount(input.output ?? '')
  const limit = numericExit(input.previewLines)

  if (input.truncated && limit !== undefined && limit > 0 && lines > limit) {
    facts.push('truncated: showing ' + (input.previewSide === 'first' ? 'first ' : 'last ') + limit + ' lines')
  }

  if (input.captureTruncated) {
    facts.push('capture truncated: head + tail retained')
  }

  return facts
}

/** One run: input, live/retained output, optional error and factual state footer. */
export function runBox(input: RunBoxInput): JSX.Element {
  const word = input.state === 'exit' && numericExit(input.exit) !== undefined
    ? 'exit ' + input.exit
    : RUN_WORD[input.state]
  const facts = runFootFacts(input)
  const tone = RUN_TONE[input.state]

  return (
    <col gap="none" key="run" role="omp.run" tone={tone}>
      <row align="start" gap="xs" key="input" role="omp.run.input">
        <icon aria="Input" key="prompt" name="arrow-left" role="omp.run.prompt" />
        <code key="code" lang={input.language ?? 'bash'} numbers={false} text={input.command} wrap />
      </row>
      {input.cwd ? (
        <text key="cwd" role="omp.run.cwd" spans={[{ s: 'muted', t: input.cwd }]} wrap="word" />
      ) : null}
      {input.output || input.error ? (
        <row align="start" gap="xs" key="result" role="omp.run.result">
          <icon aria="Output" key="prompt" name="arrow-right" role="omp.run.prompt" />
          <col gap="none" key="outputs" role="omp.run.outputs">
            {input.output ? (
              <ansi follow={input.state === 'running'} key="output" role="omp.run.output" text={input.output} />
            ) : null}
            {input.error ? (
              <text key="error" role="omp.tool.error" spans={[{ s: 'error', t: input.error }]} wrap="word" />
            ) : null}
          </col>
        </row>
      ) : null}
      <row align="center" gap="sm" key="foot" role="omp.run.foot">
        <text key="state" role="omp.run.state" spans={[{ s: tone, t: word }]} />
        {facts.length ? (
          <text key="facts" role="omp.run.facts" spans={[{ s: 'muted', t: facts.join(' · ') }]} wrap="word" />
        ) : null}
      </row>
    </col>
  )
}
