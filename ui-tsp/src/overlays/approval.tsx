// Dock approvals share App's overlay generations, but never take the composer's caret.

import type { ClarifyLockResult, ClarifyNote } from '@hermes/shared/gateway-events'
import type { ServerRequest } from '@hermes/shared/json-rpc-channel'

import { type Action, approvalActionForKey } from '../actions.js'
import type { Attachments } from '../attachments.js'
import type { Overlay, OverlayHost } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'

export interface PromptHost extends OverlayHost {
  readonly bindings?: { readonly actions: readonly Action[] }
  owns(overlay: Overlay): boolean
  notice(message: string): void
  confirmDenial(id: string): Promise<void>
  promptAttachments?(): Attachments
  lockClarify?(request: string, question: string, answer: string | null, note?: ClarifyNote): Promise<ClarifyLockResult>
}

export interface ApprovalPrompt extends Overlay {
  readonly placement: 'dock'
  approve(): void
  answer(choice: string): Promise<boolean>
  denyAndConfirm(): Promise<boolean>
}

export function isApprovalPrompt(overlay: Overlay): overlay is ApprovalPrompt {
  return (
    overlay.placement === 'dock' &&
    'answer' in overlay &&
    typeof overlay.answer === 'function' &&
    'denyAndConfirm' in overlay &&
    typeof overlay.denyAndConfirm === 'function'
  )
}

interface Choice {
  id: string
  label: string
  detail: string
}

const CHOICES: Choice[] = [
  { detail: 'Run it this time only', id: 'once', label: 'Allow once' },
  { detail: 'Allow matching commands until the session ends', id: 'session', label: 'Allow for this session' },
  { detail: 'Remember this approval for every session', id: 'always', label: 'Always allow' },
  { detail: 'Tell the agent not to run it', id: 'deny', label: 'Deny' }
]

const str = (value: unknown): string => (typeof value === 'string' ? value : '')

export function approvalPrompt(host: PromptHost, req: ServerRequest): ApprovalPrompt {
  const p = req.params
  const offered = Array.isArray(p.choices) ? p.choices.filter(c => typeof c === 'string') : []
  const smartDenied = p.smart_denied === true

  const allowed = new Set(
    offered.length
      ? offered
      : smartDenied
        ? ['once', 'deny']
        : p.allow_permanent === false
          ? ['once', 'session', 'deny']
          : ['once', 'session', 'always', 'deny']
  )

  if (p.allow_session === false) {
    allowed.delete('session')
  }

  const choices = CHOICES.filter(choice => allowed.has(choice.id))
  let selected = 0
  let answering = false

  const respond = async (send: () => void | Promise<void>): Promise<boolean> => {
    if (answering || !host.owns(overlay)) {
      return false
    }

    answering = true
    host.changed()

    try {
      const sent = send()

      if (sent instanceof Promise) {
        await sent
      }

      if (!host.owns(overlay)) {
        return false
      }

      host.close(overlay)

      return true
    } catch (error) {
      if (host.owns(overlay)) {
        host.notice(`Could not answer approval: ${error instanceof Error ? error.message : String(error)}`)
      }

      return false
    } finally {
      answering = false
      host.changed()
    }
  }

  const overlay: ApprovalPrompt = {
    key: `prompt:${req.id}`,
    placement: 'dock',
    approve: () => { if (allowed.has('once')) { void overlay.answer('once') } },
    answer: choice => respond(() => req.respond({ choice })),
    // Ordinary choices retain the response-frame path. Transactions need the
    // existing acknowledged proxy: the channel swallows respond() send failures.
    denyAndConfirm: () => respond(() => host.confirmDenial(req.id)),
    node: id => (
      <col gap="sm" key={id.slice('dock.'.length)} role="omp.editor.ask.approval">
        <col gap="xs" key="body">
          <md
            key="question"
            role="omp.ask.question"
            text={answering ? 'Sending approval response…' : 'Allow this command?'}
          />
          {str(p.command) ? <code key="command" lang="bash" text={str(p.command)} wrap /> : null}
          {str(p.description) || smartDenied ? (
            <md
              key="why"
              text={`${smartDenied ? '**The safety check advised against it**' : '**Flagged**'}${str(p.description) ? ` · ${str(p.description)}` : ''}`}
            />
          ) : null}
          <list
            aria="Approval choices"
            key="options"
            // The native list scrolls the selected item into this bounded viewport;
            // command and warning stay outside it, visible before every decision.
            max={{ lines: 4 }}
            onActivate={ev => {
              const choice = choices.find(c => `${id}.body.options.${c.id}` === ev.item)

              if (choice) {
                void overlay.answer(choice.id)
              }
            }}
            onSelect={ev => {
              const index = choices.findIndex(c => `${id}.body.options.${c.id}` === ev.item)

              if (index >= 0) {
                selected = index
                host.changed()
              }
            }}
            role="omp.ask.options"
            selected={choices[selected] ? `${id}.body.options.${choices[selected]!.id}` : undefined}
          >
            {choices.map((choice, i) => (
              <item
                detail={[{ t: choice.detail }]}
                key={choice.id}
                label={[{ t: `${i + 1}. ${choice.label}` }]}
                role="omp.ask.option"
              />
            ))}
          </list>
          <row gap="sm" key="actions" role="omp.actions">
            <ActionButton
              key="deny"
              onClick={() => void overlay.answer('deny')}
              role="omp.btn"
              text="Deny"
              title="Deny · escape (empty draft)"
            />
            <ActionButton
              key="choose"
              onClick={() => void overlay.answer(choices[selected]?.id ?? 'deny')}
              role="omp.btn"
              text="Choose"
              title="Up/down · enter (empty draft)"
            />
          </row>
          <text
            key="hint"
            text="Empty draft: ↑/↓ · enter · 1–4 · esc denies. Type a message to deny and steer."
            tone="muted"
          />
        </col>
      </col>
    ),
    onKey: key => {
      const action = approvalActionForKey(key)

      if (!action) {
        return false
      }

      if (answering) {
        return true
      }

      switch (action.kind) {
        case 'move':
          selected = choices.length ? (selected + action.delta + choices.length) % choices.length : 0
          host.changed()

          break

        case 'choose':
          void overlay.answer(choices[selected]?.id ?? 'deny')

          break

        case 'deny':
          void overlay.answer('deny')

          break
        case 'digit': {
          const choice = choices[action.index]

          if (choice) {
            void overlay.answer(choice.id)
          }

          break
        }
      }

      return true
    }
  }

  return overlay
}
