import type { ModelHubGetResult, ModelHubSetParams, ModelHubSetResult, ModelRoute } from '@hermes/shared/gateway-events'
import type { JSX, Key } from '@stencil-hq/tern'

import type { App } from '../app.js'
import type { Overlay } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'

import { openModelPicker } from './models.js'
import { confirmOverlay } from './prompts.js'
import { moveSelection } from './search.js'

// Keep replacement sheets behind any already-issued profile write/readback.
const operations = new WeakMap<App, Promise<unknown>>()

function ordered<T>(app: App, run: () => Promise<T>): Promise<T> {
  const result = (operations.get(app) ?? Promise.resolve()).then(run, run)
  operations.set(app, result.catch(() => undefined))

  return result
}

/** Management is profile-scoped; /model remains temporary live-session selection. */
export function openModelHub(app: App) {
  const sid = app.sid

  if (!sid) {
    app.transcript.notice('Start a live session before opening Models management.', 'warning')
    app.changed()

    return
  }

  let data: ModelHubGetResult | undefined
  let generation = 0
  let busy = false
  let message = ''
  let page = 'roles'
  let selected = ''
  let confirmation: ModelHubSetParams | undefined
  const live = () => app.sid === sid && app.overlays.includes(overlay)
  const label = (route: ModelRoute | null | undefined) => route ? `${route.provider} / ${route.model}` : 'Automatic (inherit)'

  const load = async () => {
    const token = ++generation

    try {
      const result = await ordered(app, () => app.gw.request<ModelHubGetResult>('model.hub.get', { session_id: sid }))

      if (live() && token === generation) {
        data = result
        message = ''
      }
    } catch (error) {
      if (live() && token === generation) {
        message = error instanceof Error ? error.message : String(error)
      }
    }

    app.changed()
  }

  const save = async (intent: ModelHubSetParams, confirmed = false) => {
    if (!live() || busy || !data || (confirmed && confirmation !== intent)) {
      return
    }

    busy = true
    confirmation = undefined
    message = 'Applying profile change; awaiting canonical readback…'
    app.changed()

    try {
      await ordered(app, async () => {
        if (!live()) {
          return
        }

        const result = await app.gw.request<ModelHubSetResult>('model.hub.set', { ...intent, confirmed })

        if (!live()) {
          return
        }

        if (result.confirm_required) {
          confirmation = intent
          app.open(confirmOverlay(app, {
            confirm: 'Confirm exact profile change',
            detail: `Profile: ${intent.profile}. Scope: profile defaults only. ${intent.operation}: ${intent.role ?? ''} ${label(intent.route)}${intent.operation === 'fallbacks' ? `; ordered fallbacks: ${intent.fallbacks?.map(label).join(' → ') || '(clear)'}` : ''}. ${result.confirm_message}`,
            onCancel: () => {
              if (confirmation === intent) {
                confirmation = undefined
                message = 'Change cancelled.'
                app.changed()
              }
            },
            onConfirm: () => void save(intent, true),
            title: 'Confirm model management'
          }))

          return
        }

        const canonical = await app.gw.request<ModelHubGetResult>('model.hub.get', { session_id: sid })

        if (live()) {
          data = canonical
          message = 'Profile model settings confirmed. Live session model pins unchanged.'
        }
      })
    } catch (error) {
      if (live()) {
        message = `${error instanceof Error ? error.message : String(error)} Reload before retrying.`
      }
    } finally {
      busy = false
      app.changed()
    }
  }

  const change = (operation: ModelHubSetParams['operation'], extra: Partial<ModelHubSetParams> = {}) => {
    if (!data || !live() || busy || confirmation || !data.operations.writable) {
      return
    }

    void save({ fallbacks: [], operation, profile: data.profile, revision: data.revision, scope: 'profile', session_id: sid, ...extra })
  }

  const pick = (role?: string) => {
    if (!data || !live() || busy || confirmation || !data.operations.writable) {
      return
    }

    const revision = data.revision
    const fallbacks = data.fallbacks
    openModelPicker(app, {
      onChoose: route => {
        if (!live() || data?.revision !== revision) {
          return
        }

        change(role ? 'role' : 'fallbacks', role ? { role, route } : { fallbacks: [...fallbacks, route] })
      },
      sessionOnly: true
    })
  }

  const button = (key: string, text: string, run: () => void): JSX.Element => {
    const revision = data?.revision

    return <ActionButton disabled={!live() || busy || Boolean(confirmation)} key={key} onClick={() => { if (live() && !busy && !confirmation && data?.revision === revision) { run() } }} role="omp.btn" text={text} title={text} />
  }

  const overlay: Overlay = {
    key: 'model-hub',
    modal: true,
    node: id => {
      const expired = app.sid !== sid
      const roles = data?.roles ?? []
      const providers = data?.providers ?? []
      const fallbacks = data?.fallbacks ?? []

      const entries = page === 'roles' ? roles.map(role => ({ id: role.id, label: role.label, detail: label(role.route) }))
        : page === 'fallbacks' ? fallbacks.map((route, index) => ({ id: String(index), label: `${index + 1}. ${label(route)}` }))
          : providers.map(provider => ({ id: provider.slug, label: provider.name, detail: `${provider.authenticated === false ? 'Locked' : 'Configured'} · ${provider.models?.length ?? 0} models` }))

      if (!entries.some(entry => entry.id === selected)) {
        selected = entries[0]?.id ?? ''
      }

      const provider = providers.find(row => row.slug === selected)
      const canWrite = Boolean(data?.operations.writable) && !busy && !confirmation && !expired
      const index = Number(selected)

      return (
        <overlay anchor="center" head="Models management" key={id.slice('layer.'.length)} modal size="lg">
          <col gap="md" key="body">
            <text key="scope" text={expired ? 'This model hub belongs to a previous session. Close and reopen it.' : `Profile: ${data?.profile || 'loading'}. Auxiliary roles and fallback chain: profile defaults only. No session role overrides are supported.`} wrap="word" />
            {!expired ? <>
              <row gap="md" key="pages">
                {button('roles', 'Auxiliary roles', () => { page = 'roles'; app.changed() })}
                {button('fallbacks', 'Fallback chain', () => { page = 'fallbacks'; app.changed() })}
                {button('providers', 'Providers', () => { page = 'providers'; app.changed() })}
                {button('session', 'Choose live session model', () => openModelPicker(app, { sessionOnly: true }))}
              </row>
              <list aria="Model management entries" key="entries" onActivate={event => {
                selected = event.item.split('.entries.').at(-1) ?? ''

                if (page === 'roles') { pick(selected) }
                app.changed()
              }} onSelect={event => { selected = event.item.split('.entries.').at(-1) ?? ''; app.changed() }} selected={`${id}.body.entries.${selected}`}>
                {entries.map(entry => <item detail={[{ t: 'detail' in entry ? String(entry.detail) : '' }]} key={entry.id} label={[{ t: entry.label }]} />)}
              </list>
              <text key="status" text={busy ? 'Applying profile change; awaiting canonical readback…' : message || (!data ? 'Loading supported operations…' : data.operations.writable ? 'Choose an operation. Changes require confirmation.' : 'Administrator-managed: read-only.')} wrap="word" />
              {page === 'providers' ? <text key="login" text={`${provider?.name ?? 'Providers'}: ${data?.operations.login_hint ?? ''} Reload after setup. Login secrets never enter this inventory.`} wrap="word" /> : null}
              {page === 'fallbacks' ? <text key="bounds" text={`Ordered chain; maximum ${data?.operations.max_fallbacks ?? 0}. Repeated routes, primary cycles, locked/unavailable models are rejected by Hermes.`} wrap="word" /> : null}
              {canWrite ? <row gap="md" key="manage">
                {page === 'roles' && selected ? button('assign', 'Assign selected role', () => pick(selected)) : null}
                {page === 'roles' && selected ? button('clear', 'Clear selected role to automatic', () => change('role', { role: selected, route: null })) : null}
                {page === 'roles' ? button('reset', 'Reset auxiliary roles only', () => change('reset_roles')) : null}
                {page === 'fallbacks' && fallbacks.length < (data?.operations.max_fallbacks ?? 0) ? button('add', 'Add fallback', () => pick()) : null}
                {page === 'fallbacks' && fallbacks[index] ? button('remove', 'Remove selected fallback', () => change('fallbacks', { fallbacks: fallbacks.filter((_, at) => at !== index) })) : null}
                {page === 'fallbacks' && index > 0 && fallbacks[index] ? button('earlier', 'Move selected fallback earlier', () => {
                  const next = [...fallbacks]; [next[index - 1], next[index]] = [next[index]!, next[index - 1]!]
                  change('fallbacks', { fallbacks: next })
                }) : null}
                {page === 'fallbacks' ? button('reset-chain', 'Clear fallback chain only', () => change('fallbacks')) : null}
              </row> : null}
              <text key="recents" text={`Session cycle recents (navigation only; a requested switch may be pending until next turn): ${app.modelRecents.list(sid).map(label).join(' · ') || '(none)'}`} wrap="word" />
              {!busy && !confirmation ? button('reload', 'Reload canonical model settings', () => void load()) : null}
            </> : null}
            <ActionButton key="close" onClick={() => app.close(overlay)} role="omp.btn" text="Close" title="Close" />
          </col>
        </overlay>
      )
    },
    onKey: (key: Key) => {
      if (key.name === 'escape') {
        app.close(overlay)
      } else if (live() && !busy && !confirmation) {
        const pages = ['roles', 'fallbacks', 'providers']

        const ids = page === 'roles' ? data?.roles.map(role => role.id) ?? []
          : page === 'fallbacks' ? data?.fallbacks.map((_, index) => String(index)) ?? []
            : data?.providers.map(provider => provider.slug) ?? []

        if (key.name === 'tab') {
          page = pages[(pages.indexOf(page) + (key.shift ? 2 : 1)) % pages.length]!
        } else if (key.name === 'enter' && page === 'roles' && selected) {
          pick(selected)
        } else {
          selected = moveSelection(key, ids, selected) ?? selected
        }

        app.changed()
      }

      return true
    }
  }

  app.open(overlay)
  void load()
}
