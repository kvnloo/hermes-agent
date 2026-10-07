import { isDeepStrictEqual } from 'node:util'
import { readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { expect, test as base, type Screen } from 'e2e'
import { NativeControl } from './adapter.ts'
import { flatten, type Json, type Prefs, type SettingsResult, type Wire } from './types.ts'

const test = base.extend<{ native:NativeControl }>()
let baseline: SettingsResult
let initialConfig: Record<string,Json>
let initialSession: string

function leaf(config: Record<string,Json>, key: string): Json | undefined {
  let value: Json | undefined = config
  for (const part of key.split('.')) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
    value = value[part]
  }
  return value
}

async function settingsOpen(screen:Screen,native:NativeControl): Promise<void> {
  await screen.getByText('Settings',{exact:true}).tap()
  await expect.poll(async () => (await native.prefs())?.p.title).toBe('Hermes settings')
  await expect.poll(async () => (await native.settings()).fields['agent.max_turns']?.type).toBe('number')
  await expect.poll(async () => (await native.prefs())?.p.sections?.some(s => s.rows.length)).toBe(true)
}

async function search(native:NativeControl,key:string,label=key): Promise<Prefs> {
  if ((await native.prefs())?.p.query !== undefined) {
    await native.key('Escape')
    await expect.poll(async () => (await native.prefs())?.p.query).toBeUndefined()
  }
  await native.type(key)
  await expect.poll(async () => (await native.prefs())?.p.query).toBe(key)
  await expect.poll(() => native.fieldVisible(label)).toBe(true)
  const prefs = await native.prefs()
  if (!prefs) throw new Error('Native settings sheet closed during search.')
  return prefs
}

async function selectField(native:NativeControl,key:string,label=key): Promise<void> {
  const prefs = await search(native,key,label)
  const count = prefs.p.sections?.flatMap(s => s.rows).length ?? 0
  for (let i=0;i<=count && (await native.prefs())?.p.focus !== key;i++) {
    const prior = (await native.prefs())?.p.focus
    await native.key('ArrowDown')
    await expect.poll(async () => (await native.prefs())?.p.focus).not.toBe(prior)
  }
  await expect.poll(async () => (await native.prefs())?.p.focus).toBe(key)
}

async function editor(screen:Screen,native:NativeControl,key:string,text:string): Promise<void> {
  await search(native,key)
  const field = (await native.snapshot()).nodes.find(n => n.role === 'textbox' && n.name === key && !n.states?.hidden)
  if (field) await screen.getByRole('textbox',key,{exact:true}).tap()
  else {
    await selectField(native,key)
    await native.key('Enter')
  }
  await expect.poll(async () => (await native.prefs())?.p.editing?.row).toBe(key)
  const draft = (await native.prefs())?.p.editing?.draft
  if (draft === undefined) throw new Error(`Native editor ${key} does not expose an acknowledged program-owned draft.`)
  await native.key('End')
  await expect.poll(async () => (await native.prefs())?.p.editing?.cursor).toBe(draft.length)
  const remaining = Array.from(draft)
  while (remaining.length) {
    remaining.pop()
    await native.key('Backspace')
    await expect.poll(async () => (await native.prefs())?.p.editing?.draft).toBe(remaining.join(''))
  }
  await expect.poll(async () => (await native.prefs())?.p.editing?.draft).toBe('')
  await native.type(text)
  await expect.poll(async () => (await native.prefs())?.p.editing?.draft).toBe(text)
  // Native DOM must show the typed draft too; a sent frame alone is not acceptance.
  if (text) await expect.poll(async () => flatten((await native.snapshot()).tree).some(n => n.text === text || n.input?.value === text)).toBe(true)
  await native.key('Enter')
}

async function saved(native:NativeControl,key:string,value:Json,options?:{absent:true}): Promise<void> {
  await expect.poll(async () => leaf(await native.config(),key)).toEqual(options?.absent ? undefined : value)
  await expect.poll(async () => (await native.settings()).fields[key]?.value).toEqual(value)
  await expect.poll(() => native.fieldVisible(key)).toBe(true)
  const field = (await native.settings()).fields[key]!
  const unsetScalar = value === null && (field.type === 'boolean' || field.type === 'number')
  const expected = unsetScalar ? '' : field.type === 'boolean' ? value === true
    : field.type === 'number' ? (typeof value === 'number' ? value : undefined)
      : field.type === 'select' ? (value === null ? undefined : String(value))
        : value === null && field.type === 'string' ? '' : typeof value === 'string' ? value : JSON.stringify(value)
  await expect.poll(async () => {
    const control = (await native.prefs())?.p.sections?.flatMap(s => s.rows).find(r => r.id === key)?.control
    return field.type === 'boolean' && !unsetScalar ? control?.on : control?.value
  }).toEqual(expected)
  await expect.poll(async () => (await native.prefs())?.p.sections?.flatMap(s => s.rows).find(r => r.id === key)?.warning).toBeUndefined()
}

async function requestAfter(native:NativeControl,offset:number,method:string,key?:string): Promise<Wire> {
  await expect.poll(async () => (await native.wire()).slice(offset).some(w => w.dir === 'request' && w.body.method === method && (!key || w.body.params?.key === key))).toBe(true)
  return (await native.wire()).slice(offset).find(w => w.dir === 'request' && w.body.method === method && (!key || w.body.params?.key === key))!
}

async function close(screen:Screen,native:NativeControl): Promise<void> {
  await screen.getByRole('button','Close settings',{exact:true}).tap()
  await expect.poll(async () => await native.prefs()).toBeUndefined()
}

async function composer(native:NativeControl): Promise<{text:string;cursor:number}> {
  const node = (await native.rendered()).get('dock.composer.line.input')
  if (!node || typeof node.p?.text !== 'string' || typeof node.p.cursor !== 'number') throw new Error('Real native composer text/caret evidence is unavailable.')
  return {text:node.p.text,cursor:node.p.cursor}
}

async function localCommand(native:NativeControl,command:string): Promise<void> {
  const before = await composer(native)
  if (before.text) throw new Error('Local command requires an empty composer; never discard or send a draft.')
  await native.type(command)
  await expect.poll(() => composer(native)).toEqual({text:command,cursor:command.length})
  await native.key('Enter')
}

async function choice(screen:Screen,native:NativeControl,key:string,value:string,options:readonly string[],label=key,confirmation=false): Promise<void> {
  await search(native,key,label)
  const radioName = key === 'session.effort' && value === 'none' ? 'off' : value || '(empty)'
  const inline = (await native.snapshot()).nodes.filter(n => n.role === 'radio' && n.name === radioName && !n.states?.hidden)
  if (inline.length === 1) {
    await screen.getByRole('radio',radioName,{exact:true}).tap()
    if (!confirmation) await expect(screen.getByRole('radio',radioName,{exact:true})).toBeChecked()
    return
  }
  await selectField(native,key,label)
  await native.key('Enter')
  await expect.poll(async () => (await native.prefs())?.p.editing?.row).toBe(key)
  for (let i=0;i<options.length && (await native.prefs())?.p.editing?.option !== value;i++) {
    const prior = (await native.prefs())?.p.editing?.option
    await native.key('ArrowDown')
    await expect.poll(async () => (await native.prefs())?.p.editing?.option).not.toBe(prior)
  }
  expect((await native.prefs())?.p.editing?.option).toBe(value)
  await native.key('Enter')
}

test.describe('real native profile settings (no turns, confirmations or provider grants)',{serial:true},() => {
  test.afterEach(async ({native}) => { await native.release() })

  // The real driver reached field 480/934 in 15 minutes; retain complete coverage.
  test('opens a real gateway-owned sheet and reaches every canonical page and leaf',{timeout:2400000},async ({screen,native}) => {
    const wire = await native.wire()
    const sessionRequests = new Set(wire.filter(w => w.dir === 'request' && ['session.create','session.resume'].includes(w.body.method ?? '')).map(w => w.body.id))
    const creation = wire.filter(w => w.dir === 'delivered' && sessionRequests.has(w.body.id) && w.body.result && typeof w.body.result === 'object' && !Array.isArray(w.body.result) && 'session_id' in w.body.result).at(-1)
    initialSession = String((creation?.body.result as Record<string,Json>)?.session_id ?? '')
    if (!initialSession) throw new Error('No delivered active-session creation or resume was recorded.')
    initialConfig = await native.config()
    expect(leaf(initialConfig,'auth.adopt_external_logins')).toBe(false)
    expect(leaf(initialConfig,'telemetry.shared_metrics.send')).toBe(false)
    await settingsOpen(screen,native)
    baseline = await native.settings()
    const schema = await native.schema()
    expect(Object.keys(baseline.fields).sort()).toEqual(Object.keys(schema).sort())
    expect([...new Set(Object.values(baseline.fields).map(f => f.type))].sort()).toEqual(['boolean','list','number','object','select','string'])
    const pages = (await native.prefs())?.p.pages ?? []
    expect(pages.map(p => p.id).sort()).toEqual(['session',...new Set(Object.values(baseline.fields).map(f => `profile.${f.category}`))].sort())
    for (const page of pages) {
      const button = (await native.snapshot()).nodes.find(n => n.role === 'button' && n.name === page.label && !n.states?.hidden)
      if (button) await screen.getByRole('button',page.label,{exact:true}).tap()
      else for (let i=0;i<pages.length && (await native.prefs())?.p.page !== page.id;i++) {
        const prior = (await native.prefs())?.p.page
        await native.key('Tab')
        await expect.poll(async () => (await native.prefs())?.p.page).not.toBe(prior)
      }
      await expect.poll(async () => (await native.prefs())?.p.page).toBe(page.id)
      await expect.poll(async () => (await native.prefs())?.p.sections?.every(s => s.id === page.id)).toBe(true)
      await native.evidence(`page-${page.id}`)
    }
    for (const [key,field] of Object.entries(baseline.fields)) {
      const prefs = await search(native,key)
      const row = prefs.p.sections?.flatMap(s => s.rows).find(r => r.id === key)
      expect(row?.changed).toBe(!isDeepStrictEqual(field.value,field.default))
      const control = row!.control
      if ((field.type === 'boolean' || field.type === 'number') && typeof field.value === 'string') {
        expect(control.k).toBe('text')
        expect(control.value).toBe(field.value)
      } else if ((field.type === 'boolean' || field.type === 'number') && field.value === null) {
        expect(control.k).toBe('text')
        expect(control.value).toBe('')
      } else if (field.type === 'boolean') {
        expect(control.k).toBe('switch')
        expect(control.on).toBe(field.value)
      } else if (field.type === 'number') {
        expect(control.k).toBe('number')
        if (typeof field.value === 'number') expect(control.value).toEqual(field.value)
        else expect(control.value).toBeUndefined()
      } else if (field.type === 'select') {
        expect(control.k).toBe('choice')
        if (field.value === null) expect(control.value).toBeUndefined()
        else expect(control.value).toEqual(String(field.value))
        expect((control.options as {value:string}[]).map(option => option.value)).toEqual(field.options ?? [])
      } else {
        expect(control.k).toBe('text')
        expect(control.value).toBe(field.value === null && field.type === 'string' ? '' : typeof field.value === 'string' ? field.value : JSON.stringify(field.value))
      }
      expect(prefs.p.sections?.some(s => s.id === `profile.${field.category}` && s.rows.some(r => r.id === key))).toBe(true)
    }
    await search(native,'agent.max_turns')
    await native.key('Escape')
    await expect.poll(async () => (await native.prefs())?.p.query).toBeUndefined()
    const offset = (await native.wire()).length
    await native.type('no-field-native-e2e-zzzzzz')
    await expect.poll(async () => (await native.prefs())?.p.sections?.length).toBe(0)
    expect((await native.wire()).slice(offset).filter(w => w.dir === 'request' && w.body.method === 'settings.set')).toHaveLength(0)
    await native.evidence('empty-global-search')
    await native.key('Escape')
  })

  test('native switch, number, enum, text, list and object persist and revert sparsely',async ({screen,native}) => {
    const bool = 'display.show_reasoning', number = 'agent.max_turns', select = 'display.resume_display'
    await search(native,bool)
    const toggle = screen.getByRole('switch',bool,{exact:true})
    await expect(toggle).toBeChecked({checked:baseline.fields[bool]!.value === true})
    await toggle.tap()
    await saved(native,bool,baseline.fields[bool]!.value !== true)
    await expect(toggle).toBeChecked({checked:baseline.fields[bool]!.value !== true})
    await search(native,number)
    await screen.getByRole('button',`Increase ${number}`,{exact:true}).tap()
    await saved(native,number,Number(baseline.fields[number]!.value)+1)
    await screen.getByRole('button',`Decrease ${number}`,{exact:true}).tap()
    await saved(native,number,baseline.fields[number]!.value)
    await selectField(native,number)
    expect(baseline.fields[number]!.value).not.toEqual(baseline.fields[number]!.default)
    await screen.getByText('Use default for selected field',{exact:true}).tap()
    await saved(native,number,baseline.fields[number]!.default)
    await editor(screen,native,number,String(baseline.fields[number]!.value))
    await saved(native,number,baseline.fields[number]!.value)
    await search(native,select)
    const option = baseline.fields[select]!.options!.find(o => o !== baseline.fields[select]!.value)!
    await choice(screen,native,select,option,baseline.fields[select]!.options!)
    await saved(native,select,option)
    const cases: [string,Json][] = [
      ['agent.environment_hint','native text: "quoted" \\ slash Ω'],
      ['toolsets',['hermes-cli','native-e2e-unused']],
      ['agent.reasoning_overrides',{'native-settings-e2e':'high'}]
    ]
    for (const [key,value] of cases) {
      await editor(screen,native,key,typeof value === 'string' ? value : JSON.stringify(value))
      await saved(native,key,value)
      await native.evidence(`saved-${key}`)
    }
    await close(screen,native)
    await settingsOpen(screen,native)
    for (const [key,value] of cases) {
      await search(native,key)
      expect((await native.settings()).fields[key]!.value).toEqual(value)
      await selectField(native,key)
      await screen.getByText('Use default for selected field',{exact:true}).tap()
      await saved(native,key,baseline.fields[key]!.default)
      // Explicit object {} reversion must delete its prior entry, not deep-merge it.
      expect(leaf(await native.config(),key)).toEqual(baseline.fields[key]!.default)
      if (JSON.stringify(baseline.fields[key]!.value) !== JSON.stringify(baseline.fields[key]!.default)) {
        await editor(screen,native,key,typeof baseline.fields[key]!.value === 'string' ? String(baseline.fields[key]!.value) : JSON.stringify(baseline.fields[key]!.value))
        await saved(native,key,baseline.fields[key]!.value)
      }
    }
    await selectField(native,bool)
    const nonDefault = baseline.fields[bool]!.default !== true
    if ((await native.settings()).fields[bool]!.value !== nonDefault) {
      await screen.getByRole('switch',bool,{exact:true}).tap()
      await saved(native,bool,nonDefault)
    }
    await screen.getByText('Use default for selected field',{exact:true}).tap()
    await saved(native,bool,baseline.fields[bool]!.default)
    if (baseline.fields[bool]!.default !== baseline.fields[bool]!.value) {
      await screen.getByRole('switch',bool,{exact:true}).tap()
      await saved(native,bool,baseline.fields[bool]!.value)
    }
    await selectField(native,select)
    if ((await native.settings()).fields[select]!.value === baseline.fields[select]!.default) {
      const nonDefault = baseline.fields[select]!.options!.find(value => value !== baseline.fields[select]!.default)!
      await choice(screen,native,select,nonDefault,baseline.fields[select]!.options!)
      await saved(native,select,nonDefault)
      await selectField(native,select)
    }
    await screen.getByText('Use default for selected field',{exact:true}).tap()
    await saved(native,select,baseline.fields[select]!.default)
    if (baseline.fields[select]!.default !== baseline.fields[select]!.value) {
      await choice(screen,native,select,String(baseline.fields[select]!.value),baseline.fields[select]!.options!)
      await saved(native,select,baseline.fields[select]!.value)
    }
    const raw = await native.config()
    expect(raw.e2e_preserve).toEqual(initialConfig.e2e_preserve)
    expect(raw.model).toEqual(initialConfig.model)
    expect(raw.auth).toEqual(initialConfig.auth)
    expect(Object.keys(raw).length).toBeLessThan(Object.keys(baseline.fields).length)
    await native.evidence('sparse-reversion')
  })

  test('invalid JSON and wrong structured shape are visible errors with zero writes',async ({screen,native}) => {
    for (const [key,inputs] of [['toolsets',['[invalid', '{}']],['agent.reasoning_overrides',['{invalid','[]']]] as const) {
      for (const input of inputs) {
        const before = await native.configBytes(), offset = (await native.wire()).length
        await editor(screen,native,key,input)
        await expect.poll(async () => Boolean((await native.prefs())?.p.sections?.flatMap(s => s.rows).find(r => r.id === key)?.warning)).toBe(true)
        expect(await native.configBytes()).toBe(before)
        expect((await native.wire()).slice(offset).filter(w => w.dir === 'request' && w.body.method === 'settings.set')).toHaveLength(0)
        await native.evidence(`invalid-${key}`)
        await native.key('Escape')
        await screen.getByText('Reload saved values',{exact:true}).tap()
        await expect.poll(async () => (await native.prefs())?.p.sections?.flatMap(s => s.rows).find(r => r.id === key)?.warning).toBeUndefined()
      }
    }
  })

  test('native action opens the session-only model picker and cancellation restores the owner',async ({screen,native}) => {
    await screen.getByRole('button','Session',{exact:true}).tap()
    const owner = (await native.prefs())!.id, before = await native.configBytes(), offset = (await native.wire()).length
    await search(native,'session.model','Model')
    const row = (await native.prefs())!.p.sections!.flatMap(s => s.rows).find(r => r.id === 'session.model')!
    await screen.getByRole('button',String(row.control.label),{exact:true}).tap()
    await expect.poll(async () => [...(await native.rendered()).values()].some(n => n.k === 'picker' && n.p?.title === 'Models')).toBe(true)
    await expect(screen.getByText('Models',{exact:true})).toBeVisible()
    const picker = [...(await native.rendered()).values()].find(n => n.k === 'picker' && n.p?.title === 'Models')!
    expect((picker.p?.actions as {id:string}[]).map(action => action.id)).not.toContain('global')
    await native.evidence('session-model-action-cancel-only')
    await native.key('Escape')
    await expect.poll(async () => (await native.prefs())?.id).toBe(owner)
    expect(await native.configBytes()).toBe(before)
    expect((await native.wire()).slice(offset).filter(w => w.dir === 'request' && w.body.method === 'config.set')).toHaveLength(0)
  })

  test('nullable Unset and default reset do not replace live reasoning pins',async ({screen,native}) => {
    await close(screen,native)
    await localCommand(native,'/reasoning high --session')
    await expect.poll(async () => (await native.snapshot()).nodes.find(n => n.role === 'meter' && n.name === 'Thinking effort')?.value).toBe('high')
    const profileBefore = await native.configBytes()
    await settingsOpen(screen,native)
    await screen.getByRole('button','Session',{exact:true}).tap()
    await expect.poll(async () => (await native.prefs())?.p.lead).toContain(initialSession)
    await expect.poll(async () => (await native.prefs())?.p.sections?.flatMap(s => s.rows).find(r => r.id === 'session.effort')?.control.value).toBe('high')
    expect(await native.configBytes()).toBe(profileBefore)
    await selectField(native,'agent.reasoning_effort')
    await screen.getByText('Unset selected field',{exact:true}).tap()
    await saved(native,'agent.reasoning_effort',null,{absent:true})
    await expect.poll(async () => (await native.snapshot()).nodes.find(n => n.role === 'meter' && n.name === 'Thinking effort')?.value).toBe('high')
    await screen.getByText('Use default for selected field',{exact:true}).tap()
    await saved(native,'agent.reasoning_effort',baseline.fields['agent.reasoning_effort']!.default,{absent:true})
    await search(native,'agent.reasoning_effort')
    await choice(screen,native,'agent.reasoning_effort','low',baseline.fields['agent.reasoning_effort']!.options!)
    await saved(native,'agent.reasoning_effort','low')
    await screen.getByRole('button','Session',{exact:true}).tap()
    await expect.poll(async () => (await native.prefs())?.p.page).toBe('session')
    await choice(screen,native,'session.effort','medium',baseline.fields['agent.reasoning_effort']!.options!,'Reasoning effort')
    await expect.poll(async () => (await native.snapshot()).nodes.find(n => n.role === 'meter' && n.name === 'Thinking effort')?.value).toBe('medium')
    expect(leaf(await native.config(),'agent.reasoning_effort')).toBe('low')
    await native.evidence('profile-default-versus-live-reasoning')
    await close(screen,native)
    await localCommand(native,'/prefs')
    await expect.poll(async () => (await native.prefs())?.p.title).toBe('Hermes settings')
  })

  test('execution/privacy/provider/consent requests only Cancel, byte-identically',async ({screen,native}) => {
    const cases: [string,string | boolean][] = [
      ['terminal.backend','docker'],['auth.adopt_external_logins',true],['model','native-e2e-cancelled-model'],['telemetry.shared_metrics.send',true]
    ]
    for (const [key,value] of cases) {
      const before = await native.configBytes(), offset = (await native.wire()).length
      if (typeof value === 'boolean') {
        await search(native,key)
        await screen.getByRole('switch',key,{exact:true}).tap()
      } else if (baseline.fields[key]!.type === 'select') await choice(screen,native,key,value,baseline.fields[key]!.options!,key,true)
      else await editor(screen,native,key,value)
      const request = await requestAfter(native,offset,'settings.set',key)
      await expect.poll(async () => (await native.wire()).find(w => w.dir === 'delivered' && w.body.id === request.body.id)?.body.result).toMatchObject({key,confirm_required:true})
      await expect(screen.getByText(`Setting: ${key}`,{exact:true})).toBeVisible()
      await native.evidence(`cancel-confirmation-${key}`)
      await screen.getByText('Cancel (default)',{exact:true}).tap()
      await expect.poll(async () => (await native.prefs())?.p.title).toBe('Hermes settings')
      expect(await native.configBytes()).toBe(before)
      expect((await native.wire()).slice(offset).filter(w => w.dir === 'request' && w.body.params?.confirmed === true)).toHaveLength(0)
    }
    // Default keyboard behavior is Cancel too, never an implicit grant.
    await search(native,'auth.adopt_external_logins')
    const before = await native.configBytes()
    await screen.getByRole('switch','auth.adopt_external_logins',{exact:true}).tap()
    await expect(screen.getByText('Cancel (default)',{exact:true})).toBeVisible()
    await native.key('Enter')
    await expect.poll(async () => (await native.prefs())?.p.title).toBe('Hermes settings')
    expect(await native.configBytes()).toBe(before)
  })

  test('real unreadable config load/save errors retry without overwriting corrupt bytes',async ({screen,native}) => {
    const path = join(native.manifest.home,'config.yaml'), good = await native.configBytes(), corrupt = 'agent: [unterminated\n'
    try {
      await close(screen,native)
      await writeFile(path,corrupt,{mode:0o600})
      await screen.getByText('Settings',{exact:true}).tap()
      await expect(screen.getByText('Retry',{exact:true})).toBeVisible()
      expect(await native.configBytes()).toBe(corrupt)
      await native.evidence('real-load-error')
      await writeFile(path,good,{mode:0o600})
      await screen.getByText('Retry',{exact:true}).tap()
      await expect.poll(async () => (await native.settings()).fields['agent.max_turns']?.value).toEqual(baseline.fields['agent.max_turns']!.value)
      await search(native,'agent.max_turns')
      await writeFile(path,corrupt,{mode:0o600})
      const offset = (await native.wire()).length
      await screen.getByRole('button','Increase agent.max_turns',{exact:true}).tap()
      const request = await requestAfter(native,offset,'settings.set','agent.max_turns')
      await expect.poll(async () => (await native.wire()).find(w => w.dir === 'delivered' && w.body.id === request.body.id)?.body.error?.code).toBe(5098)
      await expect(screen.getByText('Retry',{exact:true})).toBeVisible()
      expect(await native.configBytes()).toBe(corrupt)
      await native.evidence('real-save-error')
      await writeFile(path,good,{mode:0o600})
      await screen.getByText('Retry',{exact:true}).tap()
      await saved(native,'agent.max_turns',Number(baseline.fields['agent.max_turns']!.value)+1)
      await screen.getByRole('button','Decrease agent.max_turns',{exact:true}).tap()
      await saved(native,'agent.max_turns',baseline.fields['agent.max_turns']!.value)
    } catch (error) { await writeFile(path,good,{mode:0o600}); throw error }
  })

  test('real outstanding writes serialize rapid reversion and replacement sheets wait for readback',async ({screen,native}) => {
    const key = 'display.show_reasoning', original = baseline.fields[key]!.value === true
    await search(native,key)
    const offset = (await native.wire()).length, token = await native.hold('settings.set',key)
    try {
      await screen.getByRole('switch',key,{exact:true}).tap()
      const first = await requestAfter(native,offset,'settings.set',key)
      await expect.poll(async () => (await native.wire()).some(w => w.dir === 'held' && w.body.id === first.body.id)).toBe(true)
      expect(leaf(await native.config(),key)).toBe(!original)
      await screen.getByRole('switch',key,{exact:true}).tap()
      await expect(screen.getByRole('switch',key,{exact:true})).toBeChecked({checked:original})
      expect((await native.wire()).slice(offset).filter(w => w.dir === 'request' && w.body.method === 'settings.set')).toHaveLength(1)
      await native.release()
      await saved(native,key,original)
      const writes = (await native.wire()).slice(offset).filter(w => w.dir === 'request' && w.body.method === 'settings.set')
      expect(writes.map(w => w.body.params?.value)).toEqual([!original,original])
      expect(new Set(writes.map(w => w.body.id)).size).toBe(2)
      await native.evidence(`rapid-reversion-${token}`)
    } finally { await native.release() }
    await search(native,'agent.max_turns')
    const old = (await native.prefs())!.id, next = Number(baseline.fields['agent.max_turns']!.value)+1
    const offset2 = (await native.wire()).length
    await native.hold('settings.set','agent.max_turns')
    try {
      await screen.getByRole('button','Increase agent.max_turns',{exact:true}).tap()
      const pending = await requestAfter(native,offset2,'settings.set','agent.max_turns')
      await expect.poll(async () => (await native.wire()).some(w => w.dir === 'held' && w.body.id === pending.body.id)).toBe(true)
      await close(screen,native)
      await screen.getByText('Settings',{exact:true}).tap()
      await expect.poll(async () => (await native.prefs())?.id).not.toBe(old)
      expect((await native.wire()).slice(offset2).filter(w => w.dir === 'request' && w.body.method === 'settings.get')).toHaveLength(0)
      await native.release()
      await search(native,'agent.max_turns')
      await saved(native,'agent.max_turns',next)
      expect((await native.prefs())!.id).not.toBe(old)
      await native.evidence('replacement-owner-readback')
      await screen.getByRole('button','Decrease agent.max_turns',{exact:true}).tap()
      await saved(native,'agent.max_turns',baseline.fields['agent.max_turns']!.value)
    } finally { await native.release() }
  })

  test('late real loads cannot populate a closed owner and composer draft/caret survive Settings',async ({screen,native}) => {
    await close(screen,native)
    await native.type('native draft Ω tail')
    await native.key('ArrowLeft')
    await native.key('ArrowLeft')
    const draft = await composer(native), offset = (await native.wire()).length
    const token = await native.hold('settings.get')
    try {
      await screen.getByText('Settings',{exact:true}).tap()
      const old = (await native.prefs())!.id
      const pending = await requestAfter(native,offset,'settings.get')
      await expect.poll(async () => (await native.wire()).some(w => w.dir === 'held' && w.body.id === pending.body.id)).toBe(true)
      await close(screen,native)
      await expect.poll(() => composer(native)).toEqual(draft)
      await screen.getByText('Settings',{exact:true}).tap()
      await expect.poll(async () => (await native.prefs())?.id).not.toBe(old)
      await native.release()
      await expect.poll(async () => (await native.prefs())?.p.sections?.some(s => s.rows.length)).toBe(true)
      expect((await native.prefs())!.id).not.toBe(old)
      await close(screen,native)
      await expect.poll(() => composer(native)).toEqual(draft)
      await native.type('!')
      await expect.poll(() => composer(native)).toEqual({text:draft.text.slice(0,draft.cursor)+'!'+draft.text.slice(draft.cursor),cursor:draft.cursor+1})
      expect((await native.wire()).slice(offset).filter(w => w.dir === 'request' && w.body.method === 'prompt.submit')).toHaveLength(0)
      await native.evidence(`draft-caret-owner-${token}`)
    } finally { await native.release() }
    const current = await composer(native)
    await native.key('End')
    const remaining = Array.from(current.text)
    while (remaining.length) {
      remaining.pop()
      await native.key('Backspace')
      await expect.poll(async () => (await composer(native)).text).toBe(remaining.join(''))
    }
    await expect.poll(() => composer(native)).toEqual({text:'',cursor:0})
  })

  test('new sessions retain saved defaults, independent live pins and profile ownership',async ({screen,native}) => {
    const before = await native.configBytes(), offset = (await native.wire()).length
    const foreignPath = join(native.manifest.proof,'host-home/.hermes/profiles/foreign/config.yaml')
    const foreignBefore = await readFile(foreignPath,'utf8')
    await native.hold('settings.get')
    try {
      await screen.getByText('Settings',{exact:true}).tap()
      const oldRequest = await requestAfter(native,offset,'settings.get')
      await expect.poll(async () => (await native.wire()).some(w => w.dir === 'held' && w.body.id === oldRequest.body.id)).toBe(true)
      expect(oldRequest.body.params?.session_id).toBe(initialSession)
      await close(screen,native)
      await localCommand(native,'/new')
      const current = await requestAfter(native,offset,'session.create')
      await expect.poll(async () => (await native.wire()).find(w => w.dir === 'delivered' && w.body.id === current.body.id)?.body.result).toHaveProperty('session_id')
    } finally { await native.release() }
    await expect.poll(async () => await native.prefs()).toBeUndefined()
    expect(await native.configBytes()).toBe(before)
    const creation = await requestAfter(native,offset,'session.create')
    await expect.poll(async () => (await native.wire()).find(w => w.dir === 'delivered' && w.body.id === creation.body.id)?.body.result).toHaveProperty('session_id')
    const response = (await native.wire()).find(w => w.dir === 'delivered' && w.body.id === creation.body.id)!.body.result as Record<string,Json>
    const sid = String(response.session_id)
    expect(sid).not.toBe(initialSession)
    await expect.poll(async () => (await native.snapshot()).nodes.find(n => n.role === 'meter' && n.name === 'Thinking effort')?.value).toBe('low')
    await settingsOpen(screen,native)
    await screen.getByRole('button','Session',{exact:true}).tap()
    await expect.poll(async () => (await native.prefs())?.p.lead).toContain(sid)
    await search(native,'agent.max_turns')
    await screen.getByRole('button','Increase agent.max_turns',{exact:true}).tap()
    await saved(native,'agent.max_turns',Number(baseline.fields['agent.max_turns']!.value)+1)
    await screen.getByRole('button','Decrease agent.max_turns',{exact:true}).tap()
    await saved(native,'agent.max_turns',baseline.fields['agent.max_turns']!.value)
    expect(leaf(await native.config(),'model')).toEqual(initialConfig.model)
    expect(leaf(await native.config(),'e2e_preserve')).toEqual(initialConfig.e2e_preserve)
    expect((await native.settings()).profile).toBe(baseline.profile)
    expect(await readFile(foreignPath,'utf8')).toBe(foreignBefore)
    await native.evidence('new-session-profile-ownership')
    await close(screen,native)
    const all = await native.wire()
    expect(all.filter(w => w.dir === 'denied')).toHaveLength(0)
    expect(all.filter(w => w.dir === 'request' && (w.body.method === 'prompt.submit' || w.body.params?.confirmed === true))).toHaveLength(0)
  })
})
