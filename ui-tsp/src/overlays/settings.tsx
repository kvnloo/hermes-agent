import type { SettingsField, SettingsGetResult, SettingsSetResult } from '@hermes/shared/gateway-events'
import type { ActionEvent, ChangeEvent, JSX, Key, PrefsControl, PrefsProps, PrefsRow, SelectEvent } from '@stencil-hq/tern'
import { jsonEqual as equal } from '@stencil-hq/tern'

import type { App } from '../app.js'
import { Composer } from '../composer.js'
import type { Overlay } from '../overlay.js'

import { openModelPicker } from './models.js'
import { moveSelection, rank } from './search.js'

const SESSION_PAGE = 'session'
const EFFORTS = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'ultra']
export const SETTINGS_COMMANDS = [
  ['/settings', 'Edit profile defaults and live session controls in native Settings'],
  ['/prefs', 'Open native Settings (alias of /settings)']
] as const
type Value = null | boolean | number | string | Value[] | { [key: string]: Value }

interface Field extends Omit<SettingsField, 'value' | 'default'> {
  value: Value
  default: Value
}

interface Edit {
  key: string
  value: Value
  version: number
}

interface Confirmation extends Edit {
  message: string
  serial: number
}

// A replacement sheet must wait for an already-issued write before it reads that profile.
const operations = new WeakMap<App, Promise<unknown>>()

function ordered<T>(app: App, run: () => Promise<T>): Promise<T> {
  const result = (operations.get(app) ?? Promise.resolve()).then(run, run)
  operations.set(app, result.catch(() => undefined))

  return result
}

function display(value: Value): string {
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function json(value: unknown): Value {
  if (value === null || typeof value === 'string' || typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value))) {
    return value
  }

  if (Array.isArray(value)) {
    return value.map(json)
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, json(item)]))
  }

  throw new Error('The settings value is not valid JSON.')
}

function fields(result: SettingsGetResult): Record<string, Field> {
  return Object.fromEntries(Object.entries(result.fields).map(([key, field]) => [key, {
    ...field,
    default: json(field.default),
    value: json(field.value)
  }]))
}

type AcceptedType = NonNullable<SettingsField['accepted_types']>[number]

function valueType(value: Value): AcceptedType | 'null' {
  if (value === null) {
    return 'null'
  }

  if (Array.isArray(value)) {
    return 'list'
  }

  const type = typeof value

  if (type === 'boolean' || type === 'number' || type === 'string' || type === 'object') {
    return type
  }

  throw new Error('The settings value has an unsupported type.')
}

function isMixedDomain(field: Field): boolean {
  const presentationType = field.type === 'select' ? 'string' : field.type

  if (field.accepted_types?.some(type => type !== presentationType)) {
    return true
  }

  return field.accepted_values?.some(value => valueType(value) !== presentationType) ?? false
}

function stringValue(field: Field, value: string): string {
  if (field.accepted_values !== undefined && field.accepted_values !== null) {
    for (const accepted of field.accepted_values) {
      if (typeof accepted === 'string' && accepted.trim().toLowerCase() === value.trim().toLowerCase()) {
        if (field.type !== 'select' || !field.options || field.options.includes(accepted)) {
          return accepted
        }
      }
    }

    throw new Error('Choose one of the declared runtime values.')
  }

  if (field.type === 'select' && field.options && !field.options.includes(value)) {
    throw new Error('Choose one of the declared options.')
  }

  return value
}

function parse(field: Field, value: Value): Value {
  if (value === null && (field.nullable || field.sensitive)) {
    return null
  }

  if (field.accepted_types !== undefined && field.accepted_types !== null) {
    let parsed: Value = null
    let hasParsed = false

    if (typeof value === 'string') {
      try {
        parsed = json(JSON.parse(value) as unknown)
        hasParsed = true
      } catch {
        // The raw text may be a supported string value.
      }
    }

    const parsedType = valueType(parsed)

    if (hasParsed && parsedType !== 'null' && field.accepted_types.includes(parsedType)) {
      return typeof parsed === 'string' ? stringValue(field, parsed) : parsed
    }

    const inputType = valueType(value)

    if (inputType !== 'null' && field.accepted_types.includes(inputType)) {
      return typeof value === 'string' ? stringValue(field, value) : value
    }

    throw new Error(`Use one of the supported types: ${field.accepted_types.join(', ')}.`)
  }

  if (field.accepted_values !== undefined && field.accepted_values !== null && typeof value === 'string' && (field.type === 'string' || field.type === 'select')) {
    return stringValue(field, value)
  }

  switch (field.type) {
    case 'boolean': {
      const parsed = typeof value === 'string' ? JSON.parse(value) as unknown : value

      if (typeof parsed === 'boolean') {
        return parsed
      }

      throw new Error('Use a boolean value.')
    }

    case 'number': {
      const parsed = typeof value === 'string' && value.trim() ? Number(value) : value

      if (typeof parsed === 'number' && Number.isFinite(parsed)) {
        return parsed
      }

      throw new Error('Use a finite number.')
    }

    case 'select':
      if (typeof value === 'string' && field.options?.includes(value)) {
        return value
      }

      throw new Error('Choose one of the declared options.')

    case 'string':
      if (typeof value === 'string') {
        return value
      }

      throw new Error('Use a text value.')

    case 'list':
    case 'object': {
      const parsed = typeof value === 'string' ? json(JSON.parse(value)) : value

      const valid = field.type === 'list'
        ? Array.isArray(parsed)
        : parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)

      if (valid) {
        return parsed
      }

      throw new Error(`Use a JSON ${field.type === 'list' ? 'array' : 'object'}.`)
    }

    default:
      throw new Error(`Unsupported settings type: ${field.type}`)
  }
}

function control(field: Field, value: Value): PrefsControl {
  if (isMixedDomain(field)) {
    return {
      k: 'text',
      mono: true,
      placeholder: value === null ? (field.sensitive ? 'Private value. Leave unchanged to preserve.' : 'Unset') : undefined,
      secret: field.sensitive,
      value: value === null ? '' : display(value)
    }
  }

  // A raw environment reference is not a false switch or an empty numeric value.
  if ((field.type === 'boolean' || field.type === 'number') && typeof value === 'string') {
    return { k: 'text', mono: true, value }
  }

  if ((field.type === 'boolean' || field.type === 'number') && value === null) {
    return { k: 'text', placeholder: 'Unset', value: '' }
  }

  switch (field.type) {
    case 'boolean':
      return { k: 'switch', on: value === true }

    case 'number':
      return { k: 'number', value: typeof value === 'number' ? value : undefined }

    case 'select':
      return { k: 'choice', options: (field.options ?? []).map(option => ({ label: option || '(empty)', value: option })), value: value === null ? undefined : String(value) }

    default:
      return { k: 'text', mono: field.type === 'list' || field.type === 'object', placeholder: value === null ? (field.sensitive ? 'Private value. Leave unchanged to preserve.' : 'Unset') : undefined, secret: field.sensitive, value: value === null && field.type === 'string' ? '' : display(value) }
  }
}

/** One native preferences owner, bound to the session that opened it. */
class Settings implements Overlay {
  readonly key = 'settings'
  readonly modal = true
  readonly #app: App
  readonly #sid: string
  readonly #sessionGeneration: number
  #fields: Record<string, Field> = {}
  #profile = ''
  #page = 'profile.general'
  readonly #search = new Composer()
  readonly #editor = new Composer()
  #searching = false
  #selected: string | undefined
  #editing: string | undefined
  #option: string | undefined
  #editorInitial = ''
  #confirmationSerial = 0
  #state: 'loading' | 'ready' | 'error' = 'loading'
  #message = ''
  #generation = 0
  #drafts = new Map<string, Value>()
  #errors = new Map<string, string>()
  #pending = new Map<string, Edit>()
  #versions = new Map<string, number>()
  #accepted = new Map<string, Value>()
  #readback = new Map<string, Edit>()
  #saving: Edit | null = null
  #confirmation: Confirmation | null = null
  #sessionSaving = false
  #failedEffort: string | null = null
  #draining = false
  #drainWarning = false

  constructor(app: App, sid: string) {
    this.#app = app
    this.#sid = sid
    this.#sessionGeneration = app.sessionGeneration
  }

  #live(): boolean {
    return this.#sessionCurrent() && this.#app.overlays.includes(this)
  }

  #sessionCurrent(): boolean {
    return this.#app.sid === this.#sid && this.#app.sessionGeneration === this.#sessionGeneration
  }

  #canContinue(): boolean {
    return this.#live() || (this.#draining && this.#sessionCurrent())
  }

  #warnBackground(message: string) {
    if (this.#drainWarning) {
      return
    }

    this.#drainWarning = true
    this.#app.transcript.notice(message, 'warning')
    this.#app.changed()
  }

  #cancelUnownedWork() {
    if (this.#saving || this.#pending.size || this.#readback.size) {
      this.#warnBackground(this.#sessionCurrent()
        ? 'Committed Settings changes could not be completed because their Settings sheet was replaced.'
        : 'Committed Settings changes were not sent because the live session changed.')
    }

    this.#pending.clear()
    this.#readback.clear()
    this.#draining = false
  }

  #close() {
    if (this.#confirmation) {
      this.#cancelConfirmation()
    }

    if (!this.#sessionCurrent()) {
      this.#cancelUnownedWork()
    } else {
      this.#draining = Boolean(this.#saving || this.#pending.size)

      if (this.#errors.size || this.#readback.size) {
        this.#warnBackground('Some Settings values were not saved or confirmed before the sheet closed. Reopen Settings to review and retry.')
      }
    }

    this.#app.close(this)
  }

  async load() {
    const generation = ++this.#generation
    this.#state = 'loading'
    this.#message = ''
    this.#app.changed()

    try {
      const result = await ordered(this.#app, async () => {
        if (!this.#live()) {
          return undefined
        }

        return this.#app.gw.request<SettingsGetResult>('settings.get', { session_id: this.#sid })
      })

      if (!result || !this.#live() || generation !== this.#generation) {
        return
      }

      this.#profile = result.profile
      this.#reconcile(result)
      this.#state = 'ready'
      const pages = Object.values(this.#fields).map(field => `profile.${field.category}`)

      if (this.#page !== SESSION_PAGE && !pages.includes(this.#page)) {
        this.#page = pages[0] ?? SESSION_PAGE
      }
    } catch (error) {
      if (!this.#live() || generation !== this.#generation) {
        return
      }

      this.#state = 'error'
      this.#message = error instanceof Error ? error.message : String(error)
    }

    this.#app.changed()
  }

  #edit(key: string, input: Value) {
    const field = this.#fields[key]

    if (!this.#live() || !field || this.#state !== 'ready' || this.#confirmation) {
      return
    }

    const version = (this.#versions.get(key) ?? 0) + 1
    this.#versions.set(key, version)
    this.#drafts.set(key, input)
    this.#message = ''

    try {
      const value = parse(field, input)

      if (!this.#readback.has(key)) {
        this.#errors.delete(key)
      }

      const queued = this.#pending.get(key)
      const saving = this.#saving?.key === key ? this.#saving : undefined
      const readback = this.#readback.get(key)
      const expected = queued ? queued.value : saving ? saving.value : readback ? readback.value : field.value

      // Tern can commit the same draft at Enter and again at blur.
      if (equal(value, expected) || (!saving && !queued && this.#accepted.has(key) && equal(value, this.#accepted.get(key)!))) {
        if (queued) {
          queued.version = version
        } else if (saving) {
          saving.version = version
        } else if (this.#readback.has(key)) {
          this.#readback.get(key)!.version = version
        } else {
          this.#drafts.delete(key)
        }

        this.#app.changed()

        return
      }

      if (saving && equal(value, saving.value)) {
        saving.version = version
        this.#pending.delete(key)
      } else {
        this.#pending.set(key, { key, value, version })
      }

      void this.#flush()
    } catch (error) {
      this.#pending.delete(key)
      this.#errors.set(key, error instanceof Error ? error.message : String(error))
    }

    this.#app.changed()
  }

  async #flush(confirmed?: Confirmation) {
    if (!this.#canContinue()) {
      this.#cancelUnownedWork()

      return
    }

    if (this.#saving || (this.#confirmation && !confirmed) || (confirmed && this.#confirmation !== confirmed)) {
      return
    }

    const first = confirmed ?? this.#pending.values().next().value as Edit | undefined

    if (!first) {
      return
    }

    if (confirmed) {
      if (this.#pending.get(first.key)?.version === first.version) {
        this.#pending.delete(first.key)
      }

      this.#confirmation = null
    } else {
      this.#pending.delete(first.key)
    }

    this.#saving = first
    this.#app.changed()

    try {
      await ordered(this.#app, async () => {
        let edit: Edit | undefined = first
        let isConfirmed = confirmed !== undefined

        while (edit) {
          if (!this.#canContinue()) {
            this.#cancelUnownedWork()

            return
          }

          const attempt = edit
          try {
            const result = await this.#app.gw.request<SettingsSetResult>('settings.set', {
              key: edit.key,
              profile: this.#profile,
              session_id: this.#sid,
              value: edit.value,
              ...(isConfirmed ? { confirmed: true } : {})
            })

            if (!this.#canContinue()) {
              this.#cancelUnownedWork()

              return
            }

            if (result.confirm_required) {
              if (this.#live()) {
                this.#confirmation = { ...edit, message: result.confirm_message, serial: ++this.#confirmationSerial }

                return
              }

              if (this.#draining) {
                if (!this.#pending.has(edit.key) && this.#versions.get(edit.key) === edit.version) {
                  this.#drafts.delete(edit.key)
                }

                this.#warnBackground('A committed Settings change required additional confirmation and was not applied. Reopen Settings to review and submit it again.')
              }

              this.#saving = null
              edit = this.#pending.values().next().value as Edit | undefined

              if (edit) {
                this.#pending.delete(edit.key)
                this.#saving = edit
              }

              isConfirmed = false

              continue
            }

            this.#accepted.set(edit.key, edit.value)
            this.#readback.set(edit.key, edit)

            // A transport success is not a confirmed profile value.
            const current = await this.#app.gw.request<SettingsGetResult>('settings.get', { session_id: this.#sid })

            if (!this.#canContinue()) {
              this.#cancelUnownedWork()

              return
            }

            if (!current.fields[edit.key]) {
              throw new Error('The saved field is absent from the profile readback.')
            }

            this.#reconcile(current, edit.key)

            if (this.#live()) {
              this.#message = `Profile value confirmed: ${edit.key}.`
            }
          } catch (error) {
            if (this.#live()) {
              if (this.#versions.get(attempt.key) === attempt.version) {
                this.#errors.set(attempt.key, error instanceof Error ? error.message : String(error))
              }

              this.#message = 'The profile value is not confirmed. Retry or reload saved values.'
            } else if (this.#draining && this.#sessionCurrent()) {
              this.#warnBackground('One or more committed Settings changes could not be confirmed after the sheet closed. Reopen Settings to review and retry.')
            }
          }

          if (this.#live()) {
            this.#app.changed()
          }

          this.#saving = null

          if (this.#confirmation) {
            return
          }

          edit = this.#pending.values().next().value as Edit | undefined

          if (edit) {
            this.#pending.delete(edit.key)
            this.#saving = edit
          }

          isConfirmed = false
        }
      })
    } catch (error) {
      if (this.#live()) {
        this.#message = error instanceof Error ? error.message : String(error)
      } else if (this.#draining && this.#sessionCurrent()) {
        this.#warnBackground('One or more committed Settings changes could not be confirmed after the sheet closed. Reopen Settings to review and retry.')
      }
    } finally {
      this.#saving = null

      if (this.#live()) {
        this.#app.changed()
      }

      if (this.#draining) {
        if (!this.#sessionCurrent()) {
          this.#cancelUnownedWork()
        } else if (!this.#pending.size && !this.#confirmation) {
          if (this.#errors.size || this.#readback.size) {
            this.#warnBackground('Some Settings values were not saved or confirmed before the sheet closed. Reopen Settings to review and retry.')
          }

          this.#draining = false
        }
      }

      if (!this.#confirmation && (this.#live() || (this.#draining && this.#sessionCurrent()))) {
        void this.#flush()
      }
    }
  }
  #reconcile(result: SettingsGetResult, acceptedKey?: string) {
    const next = fields(result)

    // A coupled canonical update can invalidate another field's earlier acceptance.
    for (const key of this.#accepted.keys()) {
      if (key !== acceptedKey && (!next[key] || !this.#fields[key] || !equal(next[key].value, this.#fields[key].value))) {
        this.#accepted.delete(key)
      }
    }

    this.#fields = next

    for (const [key, edit] of this.#readback) {
      if (!this.#fields[key]) {
        throw new Error(`The saved field is absent from the profile readback: ${key}`)
      }

      if (this.#versions.get(key) === edit.version && !this.#pending.has(key)) {
        this.#drafts.delete(key)
        this.#errors.delete(key)
      }
    }

    this.#readback.clear()
  }

  #cancelConfirmation() {
    const confirmation = this.#confirmation
    this.#confirmation = null

    if (confirmation) {
      this.#drafts.delete(confirmation.key)
      this.#pending.delete(confirmation.key)
    }

    this.#app.changed()
    void this.#flush()
  }

  #retry() {
    if (this.#state === 'error' || this.#readback.size) {
      void this.load()

      return
    }

    if (this.#failedEffort && this.#errors.has('session.effort')) {
      void this.#effort(this.#failedEffort)
    }

    for (const key of this.#errors.keys()) {
      const draft = this.#drafts.get(key)

      if (draft !== undefined) {
        this.#edit(key, draft)
      }
    }
  }

  async #effort(value: Value) {
    if (!this.#live() || this.#sessionSaving || typeof value !== 'string' || !EFFORTS.includes(value) || (value === this.#app.info?.reasoning_effort && !this.#errors.has('session.effort'))) {
      return
    }

    this.#sessionSaving = true
    this.#message = ''
    this.#app.changed()

    try {
      await this.#app.setReasoning(value, 'session', this.#sid)

      if (this.#live()) {
        this.#errors.delete('session.effort')
        this.#failedEffort = null
      }
    } catch (error) {
      if (this.#live()) {
        this.#errors.set('session.effort', error instanceof Error ? error.message : String(error))
        this.#failedEffort = value
      }
    } finally {
      this.#sessionSaving = false

      if (this.#live()) {
        this.#app.changed()
      }
    }
  }

  #change(event: ChangeEvent) {
    if (!event.item || event.value === undefined) {
      return
    }

    try {
      if (event.item === 'session.effort') {
        void this.#effort(json(event.value))
      } else {
        this.#edit(event.item, event.value === null ? this.#fields[event.item]?.default ?? null : json(event.value))
      }
    } catch (error) {
      this.#errors.set(event.item, error instanceof Error ? error.message : String(error))
      this.#app.changed()
    }

    if (this.#editing === event.item && !this.#errors.has(event.item)) {
      this.#editing = undefined
    }
  }

  #rows(category: string): PrefsRow[] {
    const entries = Object.entries(this.#fields).filter(([, field]) => field.category === category)
    const shown = rank(entries, this.#search.text, ([key, field]) => `${key} ${field.description} ${field.category}`)

    return shown.map(({ item: [key, field] }) => ({
      changed: !equal(field.value, field.default),
      control: this.#editing === key && (field.type === 'number' || isMixedDomain(field))
        ? { k: 'text', mono: true, secret: field.sensitive, value: this.#editor.text }
        : control(field, this.#drafts.has(key) ? this.#drafts.get(key)! : field.value),
      defaultLabel: field.sensitive ? 'Private default' : `Default: ${display(field.default)}`,
      disabled: this.#state !== 'ready' ? 'Load profile settings first.' : undefined,
      hint: `${field.description}\nSaved profile value: ${field.sensitive ? 'Private. Credential nulls preserve the stored value.' : display(field.value)}\nDefault: ${field.sensitive ? 'Private' : display(field.default)}${field.nullable ? '\nThis value can be unset.' : ''}${!field.sensitive && field.accepted_types?.length ? `\nAccepted types: ${field.accepted_types.join(', ')}` : ''}${!field.sensitive && field.accepted_values?.length ? `\nAccepted values: ${field.accepted_values.map(display).join(', ')}` : ''}`,
      id: key,
      label: key,
      warning: this.#errors.get(key) ?? (this.#pending.has(key) ? 'Save queued behind an earlier change.' : this.#saving?.key === key ? 'Save in progress. The value is not confirmed yet.' : undefined)
    }))
  }

  #sessionRows(): PrefsRow[] {
    const rows: PrefsRow[] = [
      { control: { act: 'model', k: 'action', label: this.#app.info?.model || 'Choose session model' }, hint: 'Current live model. Uses the native model picker. Scope: this session only.', id: 'session.model', label: 'Model' },
      { control: { k: 'choice', options: EFFORTS.map(value => ({ label: value === 'none' ? 'off' : value, value })), value: this.#app.info?.reasoning_effort ?? '' }, disabled: this.#sessionSaving ? 'Wait for confirmed session effort.' : undefined, hint: 'Current live effort. Scope: this session only. The live reasoning owner confirms the value through config.get.', id: 'session.effort', label: 'Reasoning effort', warning: this.#errors.get('session.effort') }
    ]

    return rows.filter(row => !this.#search.text || `${row.id} ${row.label} ${row.hint}`.toLowerCase().includes(this.#search.text.toLowerCase()))
  }

  #sections(): NonNullable<PrefsProps['sections']> {
    const categories = [...new Set(Object.values(this.#fields).map(field => field.category))]

    const sections = categories.filter(category => this.#searching || this.#page === `profile.${category}`).map(category => ({
      id: `profile.${category}`,
      page: `profile.${category}`,
      rows: this.#rows(category),
      title: `${category.replace(/[._-]/g, ' ')} · ${this.#profile || 'active profile'} defaults`
    }))

    if (this.#searching || this.#page === SESSION_PAGE) {
      sections.unshift({ id: SESSION_PAGE, page: SESSION_PAGE, rows: this.#sessionRows(), title: 'Live session controls' })
    }

    return sections.filter(section => section.rows.length)
  }

  #select(event: SelectEvent) {
    const split = event.item.indexOf('=')

    if (split >= 0 && this.#editing === event.item.slice(0, split)) {
      this.#option = event.item.slice(split + 1)
    } else {
      this.#editing = undefined
      this.#selected = event.item
    }

    this.#app.changed()
  }

  #pageAction(event: ActionEvent) {
    if (event.act === 'page' && event.value && (event.value === SESSION_PAGE || Object.values(this.#fields).some(field => `profile.${field.category}` === event.value))) {
      this.#page = event.value
      this.#searching = false
      this.#search.reset('')
      this.#editing = undefined
      this.#selected = undefined
    } else if (event.act === 'close') {
      if (event.value) {
        this.#editing = undefined
      } else {
        this.#close()
      }
    } else if (event.act === 'model') {
      if (this.#live()) {
        openModelPicker(this.#app, { sessionOnly: true })
      }
    } else if (event.act === 'edit' && event.value) {
      this.#activate(event.value)
    }

    this.#app.changed()
  }

  #activate(key: string) {
    if (!this.#live()) {
      return
    }

    this.#selected = key

    if (key === 'session.model') {
      openModelPicker(this.#app, { sessionOnly: true })

      return
    }

    const field = this.#fields[key]
    const value = key === 'session.effort' ? this.#app.info?.reasoning_effort ?? '' : this.#drafts.has(key) ? this.#drafts.get(key)! : field?.value

    if (key !== 'session.effort' && (!field || this.#state !== 'ready')) {
      return
    }

    if (field?.type === 'boolean' && typeof value === 'boolean' && !isMixedDomain(field)) {
      this.#edit(key, value !== true)

      return
    }

    this.#editing = key
    this.#option = typeof value === 'string' ? value : undefined
    this.#editorInitial = value === null || value === undefined ? '' : display(value)
    this.#editor.reset(this.#editorInitial)
    this.#app.changed()
  }

  #commitEditor() {
    const key = this.#editing

    if (!key) {
      return
    }

    if (key === 'session.effort') {
      void this.#effort(this.#option ?? '')
      this.#editing = undefined

      return
    }

    const field = this.#fields[key]

    if (!field) {
      return
    }

    const choice = field.type === 'select' && !isMixedDomain(field)
    const number = field.type === 'number' && !isMixedDomain(field)

    if ((!choice && this.#editor.text === this.#editorInitial) || (choice && this.#option === undefined && field.value === null)) {
      this.#editing = undefined

      return
    }

    const input = choice ? this.#option ?? ''
      : number ? (this.#editor.text.trim() ? this.#editor.text : null)
        : this.#editor.text

    this.#edit(key, input)

    if (!this.#errors.has(key)) {
      this.#editing = undefined
    }
  }

  node(id: string): JSX.Element {
    if (!this.#sessionCurrent()) {
      return (
        <overlay anchor="center" head="Settings" key={id.slice('layer.'.length)} modal size="lg">
          <text key="expired" text="This Settings sheet belongs to an earlier session owner. Close it and reopen Settings for the current session." wrap="word" />
          {this.#button('close', 'Close', () => this.#close())}
        </overlay>
      )
    }

    if (this.#confirmation) {
      const ask = this.#confirmation

      return (
        <overlay anchor="center" head="Confirm profile change" key={id.slice('layer.'.length)} modal size="md">
          <col gap="md" key={`confirmation:${ask.serial}`}>
            <text key="scope" text={`Scope: profile ${this.#profile}. This does not replace live session pins.`} wrap="word" />
            <text key="target" text={`Setting: ${ask.key}`} />
            <code key="value" lang="json" text={this.#fields[ask.key]?.sensitive ? (ask.value === '' ? 'Clear this private value' : 'Replace with the private value you entered') : JSON.stringify(ask.value, null, 2)} />
            <text key="risk" text={ask.message} wrap="word" />
            <text key="default" text="Cancel is the default. Enter or Escape cancels this change." wrap="word" />
            <row gap="md" key="actions">
              {this.#button('cancel', 'Cancel (default)', () => {
                if (this.#confirmation === ask) {
                  this.#cancelConfirmation()
                }
              })}
              {this.#button('confirm', 'Confirm exact change', () => void this.#flush(ask))}
            </row>
          </col>
        </overlay>
      )
    }

    const session = this.#page === SESSION_PAGE
    const categories = [...new Set(Object.values(this.#fields).map(field => field.category))]
    const sections = this.#sections()
    const visible = sections.flatMap(section => section.rows.map(row => row.id))

    if (!this.#selected || !visible.includes(this.#selected)) {
      this.#selected = visible[0]
    }

    const selectedKey = this.#selected
    const selectedField = selectedKey ? this.#fields[selectedKey] : undefined

    return (
      <prefs
        cursor={this.#search.cursor}
        editing={this.#editing ? { cursor: this.#editor.cursor, draft: this.#editor.text, option: this.#option, row: this.#editing } : undefined}
        focus={this.#selected}
        key={id.slice('layer.'.length)}
        lead={session ? `Live session: ${this.#sid}. Model and effort changes affect only this session.` : `Profile: ${this.#profile || 'active profile'}. These defaults persist in profile config. They do not replace live session pins.`}
        onAction={{
          close: event => this.#pageAction(event),
          edit: event => this.#pageAction(event),
          model: event => this.#pageAction(event),
          page: event => this.#pageAction(event)
        }}
        onActivate={event => this.#activate(event.item)}
        onChange={event => this.#change(event)}
        onEdit={event => {
          const input = this.#editing ? this.#editor : this.#search
          input.edit(event)

          if (!this.#editing) {
            this.#searching = true
          }

          this.#app.changed()
        }}
        onSelect={event => this.#select(event)}
        onUndo={() => {
          (this.#editing ? this.#editor : this.#search).undo()
          this.#app.changed()
        }}
        page={this.#page}
        pages={[
          { group: 'Live state', icon: 'session', id: SESSION_PAGE, label: 'Session' },
          ...categories.map(category => ({
            changed: Object.values(this.#fields).filter(field => field.category === category && !equal(field.value, field.default)).length,
            group: 'Profile defaults',
            id: `profile.${category}`,
            label: category.replace(/[._-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
          }))
        ]}
        query={this.#searching ? this.#search.text : undefined}
        sections={sections}
        title="Hermes settings"
      >
        <col gap="md" key="body">
          {this.#state === 'loading' ? <text key="status" text="Load profile settings…" /> : null}
          {this.#message ? <text key="message" text={this.#message} tone={this.#state === 'error' ? 'error' : 'muted'} wrap="word" /> : null}
          <row gap="md" key="actions" role="omp.actions">
            {this.#state === 'error' || this.#errors.size || this.#readback.size ? this.#button('retry', 'Retry', () => this.#retry()) : null}
            {!this.#saving && !this.#pending.size ? this.#button('reload', 'Reload saved values', () => {
              if (this.#saving || this.#pending.size) {
                return
              }

              this.#drafts.clear()
              this.#errors.clear()
              this.#accepted.clear()
              this.#editing = undefined
              void this.load()
            }) : null}
            {selectedField && (!selectedField.sensitive || selectedField.type === 'list' || selectedField.type === 'object') ? this.#button('default', 'Use default for selected field', () => this.#edit(selectedKey!, selectedField.default)) : null}
            {selectedField?.nullable && !selectedField.sensitive ? this.#button('unset', 'Unset selected field', () => this.#edit(selectedKey!, null)) : null}
            {selectedField?.sensitive && selectedField.type === 'string' ? this.#button('clear', 'Clear private value', () => {
              this.#editing = undefined
              this.#edit(selectedKey!, '')
            }) : null}
            {this.#button('close', 'Close', () => this.#close())}
          </row>
        </col>
      </prefs>
    )
  }

  #button(key: string, text: string, onClick: () => void): JSX.Element {
    return <row key={key} onClick={onClick} role="omp.btn" title={text}><text key="label" text={text} /></row>
  }

  onKey(key: Key): boolean {
    if (this.#confirmation) {
      if (key.name === 'escape' || key.name === 'enter' || (key.ctrl && key.name === 'c')) {
        this.#cancelConfirmation()
      }

      return true
    }

    if (key.ctrl && key.name === 'c') {
      this.#close()

      return true
    }

    if (!this.#live()) {
      if (key.name === 'escape') {
        this.#close()
      }

      return true
    }

    if (this.#editing) {
      if (key.name === 'escape') {
        this.#editing = undefined
      } else if (key.name === 'enter' && !key.shift && !key.alt) {
        this.#commitEditor()
      } else if (this.#editing === 'session.effort' || (this.#fields[this.#editing]?.type === 'select' && !isMixedDomain(this.#fields[this.#editing]!))) {
        const options = this.#editing === 'session.effort' ? EFFORTS : this.#fields[this.#editing]?.options ?? []
        const step = key.name === 'up' || key.name === 'left' ? -1 : key.name === 'down' || key.name === 'right' ? 1 : 0

        if (step && options.length) {
          const at = options.indexOf(this.#option ?? '')
          this.#option = options[(at < 0 ? (step > 0 ? 0 : options.length - 1) : at + step + options.length) % options.length]
        }
      } else if (key.name !== 'up' && key.name !== 'down') {
        this.#editor.key(key)
      }

      return true
    }

    if (key.name === 'escape') {
      if (this.#searching) {
        this.#searching = false
        this.#search.reset('')
      } else {
        this.#close()
      }

      return true
    }

    const pages = [SESSION_PAGE, ...new Set(Object.values(this.#fields).map(field => `profile.${field.category}`))]

    if (key.name === 'tab' || (!this.#searching && (key.name === 'left' || key.name === 'right'))) {
      const step = key.shift || key.name === 'left' ? -1 : 1
      this.#page = pages[(Math.max(0, pages.indexOf(this.#page)) + step + pages.length) % pages.length]!
      this.#selected = undefined

      return true
    }

    const rows = this.#sections().flatMap(section => section.rows.map(row => row.id))

    if (!this.#selected || !rows.includes(this.#selected)) {
      this.#selected = rows[0]
    }

    const selected = moveSelection(key, rows, this.#selected)

    if (selected !== undefined) {
      this.#selected = selected

      return true
    }

    if (key.name === 'enter') {
      if (this.#selected) {
        this.#activate(this.#selected)
      }

      return true
    }

    if ((key.ctrl && key.name === 'f') || key.name === 'paste' || (key.text && !key.ctrl && !key.meta) || this.#searching) {
      this.#searching = true

      if (!(key.ctrl && key.name === 'f')) {
        this.#search.key(key)
      }
    }

    return true
  }
}

export function openSettings(app: App) {
  if (!app.sid) {
    app.transcript.notice('Start a live session before you open Settings.', 'warning')
    app.changed()

    return
  }

  const overlay = new Settings(app, app.sid)
  app.open(overlay)
  void overlay.load()
}
