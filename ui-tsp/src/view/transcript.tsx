// Transcript entries as nodes of the `main` region, in the roles Tern's chat
// styles (Reader, Spine, Console) are written against: `omp.user` cards,
// `omp.assistant` columns holding `omp.thinking` sections, streamed `md` and
// `tool` nodes, and an `omp.turn.usage` footer.

import { type JSX, Node, node } from '@stencil-hq/tern'

import { answerText, copyAnswer } from '../answer-actions.js'
import { rewriteLocalMarkdownLinks } from '../links.js'
import type { MediaPreview } from '../media-delivery.js'
import type { Block, Entry, NoticeEntry, TurnEntry, UserEntry } from '../model.js'
import { settledTool } from '../tool-presentation.js'

import { ActionButton } from './action-button.js'
import { attachmentNodes } from './attachments.js'
import type { TableCharts } from './table-charts.js'
import { age, compact, duration } from './time.js'
import { toolNode } from './tools.js'
import { type WelcomeContext, welcomeNode } from './welcome.js'

/** What entry views need from the app. */
export interface TranscriptContext {
  charts?: TableCharts
  /** Absolute cwd reported by the owning Hermes session. */
  cwd: string
  /** Terminal clock preference; older hosts default to 24-hour time. */
  hour12?: boolean
  /** The negotiated node kind, not an assumed SDK feature. */
  media?: boolean
  /** Confirmed local gateway transport AND local session terminal backend. */
  hostLocal?: boolean
  attachmentHostLocal?: boolean
  gatewayRemote?: boolean
  mediaHost?: 'frontend' | 'gateway' | 'compute'
  mediaPreview?: MediaPreview
  mediaRevision?: number
  focusBrowser?(id: string): void
  now: number
  welcome: WelcomeContext
  copy(text: string): void
  onCopyError?(): void
  /** View-only fold state; gateway transcript/tool data remain unchanged. */
  toolsHidden?: boolean
  toolCollapsed?(turnId: string, callId: string): boolean | undefined
  foldRevision?(turnId: string): number
  toggleTool?(turnId: string, callId: string): void
  inspectAgent?(callId: string, agentId: string): void
  rewind?(entry: UserEntry): void
  rewindDisabledReason?(entry: UserEntry): string | undefined
  retry?(turnId: string): void
  canRetry?(turnId: string): boolean
}

const kNode = Symbol('tsp.node')
const projections = new WeakMap<Node, JSX.Element[]>()

/** An entry carrying its last built node and the revision it was built at. */
interface Built {
  [kNode]?: { rev: number; hour12: boolean; cwd: string; media: boolean; hostLocal: boolean; foldRev: number; chartRev: number; mediaKey: string; toolsHidden: boolean; rewindKey: string; node: JSX.Element }
}

/**
 * The node of one entry; `id` is its full node id (`main.<key>`). Turns rebuild only when
 * their `rev` moved and prompts, notices and panels never change, so a long transcript
 * costs one turn's build per frame (timer ages are fixed at first build, see time.ts).
 */
export function entryNode(e: Entry, id: string, cx: TranscriptContext): JSX.Element {
  if (e.kind === 'welcome') {
    return welcomeNode(e.id, cx.welcome)
  }

  // Entries are plain objects; the symbol slot rides on them (weak type: widen first).
  const holder: object = e
  const built: Built = holder
  const rev = e.kind === 'turn' ? e.rev : 0
  const foldRev = e.kind === 'turn' ? (cx.foldRevision?.(e.id) ?? 0) : 0
  const rewindKey = e.kind === 'user' ? `${e.rowId}:${cx.rewindDisabledReason?.(e) ?? ''}` : ''
  const chartRev = cx.charts?.revision ?? 0
  const cached = built[kNode]
  const media = cx.media ?? false
  const hostLocal = cx.hostLocal ?? false
  const hour12 = cx.hour12 ?? false
  const mediaKey = `${cx.mediaRevision}:${cx.attachmentHostLocal}:${cx.gatewayRemote}:${cx.mediaHost}`

  if (cached?.rev === rev && cached.hour12 === hour12 && cached.chartRev === chartRev && cached.cwd === cx.cwd && cached.media === media && cached.hostLocal === hostLocal && cached.mediaKey === mediaKey && cached.foldRev === foldRev && cached.toolsHidden === !!cx.toolsHidden && cached.rewindKey === rewindKey) {
    return cached.node
  }

  const node = buildEntry(e, id, cx)
  built[kNode] = { node, rev, hour12, chartRev, cwd: cx.cwd, media, hostLocal, mediaKey, foldRev, toolsHidden: !!cx.toolsHidden, rewindKey }

  return node
}

/** Consecutive settled tools must be main siblings for Tern's host work folding.
 * Keep non-work runs (including thought chains) intact and retain turn ownership.
 * Active/error/unknown work is deliberately nested outside host work groups.
 */
export function projectedEntryNodes(e: Entry, id: string, cx: TranscriptContext): JSX.Element[] {
  const original = entryNode(e, id, cx)

  if (e.kind !== 'turn' || !e.blocks.some(b => b.kind === 'tool') || !(original instanceof Node)) {
    return [original]
  }

  const cached = projections.get(original)

  if (cached) { return cached }
  const projected: JSX.Element[] = []
  let content: JSX.Element[] = []
  let key = e.id

  const flush = () => {
    projected.push(node('col', { key, role: content.some(child => child instanceof Node && child.props.role === 'omp.thinking.live') ? 'omp.activity' : 'omp.assistant' }, content))
    content = []
  }

  const lastText = e.blocks.findLast(b => b.kind === 'text')

  for (const block of e.blocks) {
    if (block.kind !== 'tool') {
      const rendered = blockNode(block, `main.${key}.${block.id}`, e.status === 'live' && block === lastText, cx, e.id, e.status !== 'live')

      if (rendered) { content.push(rendered) }

      continue
    }

    if (content.length || key === e.id) { flush() }
    const workKey = `${e.id}~${block.id}`
    const tool = blockNode(block, `main.${workKey}`, false, cx, e.id)

    if (tool instanceof Node) {
      const safe = settledTool(block.call)
      projected.push(safe
        ? node(tool.kind, { ...tool.props, key: workKey, hidden: cx.toolsHidden || undefined }, tool.children)
        : node('col', { key: workKey, role: 'omp.activity' }, [tool]))
    }

    key = `${workKey}~after`
  }

  content.push(...turnTail(e, `main.${key}`, cx))

  if (content.length) { flush() }
  projections.set(original, projected)

  return projected
}

/** Release presentation bytes once Tern owns the settled subtree. */
export function forgetEntryNode(e: Entry): void {
  const holder: object = e
  const built: Built = holder
  delete built[kNode]
}

function buildEntry(e: Exclude<Entry, { kind: 'welcome' }>, id: string, cx: TranscriptContext): JSX.Element {
  switch (e.kind) {
    case 'user':
      return userNode(e, cx)

    case 'turn':
      return turnNode(e, id, cx)

    case 'notice':
      return noticeNode(e)

    case 'panel':
      return (
        <card collapsible head={[{ s: 'strong', t: e.title }]} key={e.id} role="omp.custom" tone="neutral">
          {e.format === 'plain' ? <text key="body" spans={[{ s: 'mono', t: e.text }]} wrap="none" /> : <md key="body">{e.text}</md>}
        </card>
      )
  }
}

function userNode(e: UserEntry, cx: TranscriptContext): JSX.Element {
  const at = new Date(e.at || Date.now())
  const disabled = cx.rewindDisabledReason?.(e)

  return (
    <card key={e.id} role="omp.user" tone="user">
      <row gap="xs" key="tools" role="omp.user.tools">
        <text
          key="time"
          role="omp.user.time"
          spans={[{ s: 'dim mono', t: at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: cx.hour12 ?? false }) }]}
          title={at.toLocaleString([], { hour12: cx.hour12 ?? false })}
        />
        <ActionButton key="copy" onClick={() => cx.copy(e.text)} role="omp.user.tool" text="Copy" title="Copy message" />
        <ActionButton key="rewind" onClick={disabled ? undefined : () => cx.rewind?.(e)} role="omp.user.tool" spans={disabled ? [{ s: 'dim', t: 'Rewind (unavailable)' }] : undefined} text={disabled ? undefined : 'Rewind'} title={disabled ?? 'Rewind to this message'} />
      </row>
      <md key="body">{e.text}</md>
      {e.attachments?.length ? attachmentNodes(e.attachments, cx.media ?? false, cx.attachmentHostLocal ?? cx.hostLocal ?? true, cx.mediaPreview, cx.gatewayRemote) : null}
    </card>
  )
}

function turnNode(turn: TurnEntry, id: string, cx: TranscriptContext): JSX.Element {
  const live = turn.status === 'live'
  const lastText = turn.blocks.findLast(b => b.kind === 'text')
  const children = turn.blocks.map(b => blockNode(b, `${id}.${b.id}`, live && b === lastText, cx, turn.id, !live))

  return (
    <col key={turn.id} role="omp.assistant">
      {children}
      {turnTail(turn, id, cx)}
    </col>
  )
}

function turnTail(turn: TurnEntry, id: string, cx: TranscriptContext): JSX.Element[] {
  const live = turn.status === 'live'
  const children: JSX.Element[] = []

  if (turn.status === 'error') {
    children.push(
      node('card', { head: `${id}.error.head`, key: 'error', role: 'omp.error', tone: 'error' }, [
        <row gap="sm" key="head">
          <text key="title" spans={[{ s: 'error strong', t: 'Request failed' }]} />
          {turn.errorCode ? <badge key="code" role="omp.error.code" text={turn.errorCode} tone="error" /> : null}
        </row>,
        <text
          key="message"
          lines={8}
          role="omp.error.message"
          spans={[{ s: 'mono', t: turn.error ?? '' }]}
          wrap="word"
        />,
        turn.errorHint ? <md key="hint">{turn.errorHint}</md> : null,
        turn.retryable && cx.retry && cx.canRetry?.(turn.id) ? (
          <ActionButton key="retry" onClick={() => cx.retry?.(turn.id)} role="omp.error.retry" text="Retry" title="Retry this failed text-only prompt" />
        ) : null
      ])
    )
  } else if (turn.status === 'interrupted') {
    children.push(
      <text key="abort" role="omp.assistant.abort" spans={[{ s: 'error', t: 'Interrupted' }]} wrap="word" />
    )
  }

  if (turn.warning) {
    children.push(<text key="warning" role="omp.notice" spans={[{ s: 'warning', t: turn.warning }]} wrap="word" />)
  }

  if (!live && turn.endedAt && (turn.usage?.total || turn.usage?.input || turn.usage?.output)) {
    children.push(usageNode(turn))
  }

  if (!live && answerText(turn)) {
    children.push(
      <row align="center" gap="xs" key="answer-actions" role="omp.turn.actions">
        <ActionButton
          key="copy"
          onClick={() => copyAnswer(turn, cx.copy, () => cx.onCopyError?.())}
          role="omp.turn.copy"
          text="Copy"
          title="Copy answer"
        />
      </row>
    )
  }

  return children
}

function blockNode(b: Block, id: string, streaming: boolean, cx: TranscriptContext, turnId: string, settled = true): JSX.Element | null {
  switch (b.kind) {
    case 'steering':
      return (
        <col key={b.id} role="omp.steering">
          <text key="label" text="Steering" tone="muted" />
          <md key="body">{b.text}</md>
        </col>
      )

    case 'text':
      return (
        <md key={b.id} stream={streaming || undefined}>
          {streaming ? b.text : rewriteLocalMarkdownLinks(cx.charts?.markdown(b.text, settled) ?? b.text, cx.cwd)}
        </md>
      )

    case 'tool':
      return toolNode(b.call, cx.now, cx.cwd, cx.toolCollapsed?.(turnId, b.call.id),
        cx.toggleTool ? () => cx.toggleTool?.(turnId, b.call.id) : undefined, cx.media, cx.inspectAgent, cx.focusBrowser, cx.hostLocal ?? false, cx.mediaPreview, cx.mediaHost)

    case 'thinking':
      return thinkingNode(b, id, cx)
  }
}

function thinkingNode(b: Extract<Block, { kind: 'thinking' }>, id: string, cx: TranscriptContext): JSX.Element | null {
  if (!b.text.trim()) { return null }

  const head = `${id}.head`

  if (b.endedAt === undefined) {
    return (
      <section collapsed={false} collapsible head={head} key={b.id} role="omp.thinking.live">
        <row gap="sm" key="head">
          <spinner key="spin" role="omp.thinking.spin" style="starburst" />
          <text key="label" spans={[{ s: 'muted', t: 'Thinking…' }]} />
          <elapsed age={age(b, b.startedAt, cx.now)} format="short" key="age" />
        </row>
        <md key="body" stream>
          {b.text}
        </md>
      </section>
    )
  }

  const took = b.endedAt - b.startedAt

  // `took` isn't a typed section prop: Tern reads it on `omp.thinking` to
  // chain consecutive thoughts into one "Thought for Ns" disclosure.
  return node(
    'section',
    { collapsed: true, collapsible: true, head, key: b.id, role: 'omp.thinking', took: took > 0 ? took : undefined },
    [
      <text key="head" spans={[{ s: 'muted', t: took >= 1000 ? `Thought for ${duration(took)}` : 'Thought' }]} />,
      <md key="body">{b.text}</md>
    ]
  )
}

function usageNode(turn: TurnEntry): JSX.Element {
  const u = turn.usage ?? {}
  const ms = (turn.endedAt ?? turn.startedAt) - turn.startedAt
  const input = u.input ?? u.prompt ?? 0
  const output = u.output ?? u.completion ?? 0
  const total = u.total ?? input + output
  const cost = typeof u.cost_usd === 'number' && u.cost_usd > 0 ? ` · $${u.cost_usd.toFixed(2)}` : ''
  const title = `This turn: ${duration(ms)} · ${total.toLocaleString()} tokens (${input.toLocaleString()} in · ${output.toLocaleString()} out)${cost}`

  return (
    <row align="center" gap="xs" key="usage" role="omp.turn.usage" title={title}>
      <icon key="icon" name="time" />
      <text key="text">{`${duration(ms)} · ${compact(total)} tok${cost} this turn`}</text>
    </row>
  )
}

function noticeNode(e: NoticeEntry): JSX.Element {
  const tone = e.tone === 'info' ? 'muted' : e.tone

  return <text key={e.id} role={`omp.notice.${e.tone}`} spans={[{ s: tone, t: e.text }]} wrap="word" />
}
