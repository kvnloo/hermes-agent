import { randomUUID } from 'node:crypto'
import { execFile } from 'node:child_process'
import { closeSync, fstatSync, lstatSync, mkdtempSync, openSync, realpathSync, renameSync, rmdirSync, unlinkSync } from 'node:fs'
import { appendFile, mkdir, open, readFile, rename, unlink, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { StringDecoder } from 'node:string_decoder'
import { setTimeout as delay } from 'node:timers/promises'
import { promisify } from 'node:util'
import { defineEngine, EngineError, parseKey, resolveExpression, type EngineHandle, type Key, type OperationContext, type SemanticNode } from 'e2e/engine'
import { assertOwnedInert, flatten, nativeGateOpen, record, type Json, type Manifest, type Prefs, type SettingsResult, type TspFrame, type TspNode, type Wire } from './types.ts'

const exec = promisify(execFile)
interface Ax {
  id?: number; role?: string; name?: string; description?: string; value?: string | number
  bounds?: number[]; states?: string[]; children?: Ax[]; level?: number; actions?: string[]
}
interface Tree {
  tag?: string; id?: string; role?: string; class?: string; title?: string; text?: string; rect?: number[]
  input?: { value?: string; focused?: boolean; selectionStart?: number; selectionEnd?: number }
  children?: Tree[]
}
interface Dump { path: string; nth: string; rect: number[]; visible: boolean }
interface Snapshot { ax: Ax; tree: Tree[]; dump: Dump[]; nodes: SemanticNode[]; roots: SemanticNode[]; viewport: { width: number; height: number } }
interface Budget { deadline: number; signal: AbortSignal }
const roles: Record<string, string> = {
  Window:'window', Button:'button', Switch:'switch', CheckBox:'checkbox', RadioButton:'radio', RadioGroup:'radiogroup',
  ComboBox:'combobox', TextInput:'textbox', MultilineTextInput:'textbox', TextBox:'textbox', TextField:'textbox',
  SearchField:'searchbox', Meter:'meter', Heading:'heading', Group:'group', Region:'region', Tab:'tab', ListBox:'listbox'
}
const intrinsicRoles: Record<string, string> = { button:'button', input:'textbox', textarea:'textbox', select:'combobox', a:'link' }
const near = (a: readonly number[], b: readonly number[]) => a.length === 4 && b.length === 4 && a.every((v, i) => Math.abs(v - b[i]!) <= 1)
const box = (r: readonly number[]) => ({ x:r[0]!, y:r[1]!, width:r[2]!, height:r[3]! })
const expired = (budget: Budget) => budget.signal.aborted || budget.deadline - Date.now() <= 0
function preflight(budget: Budget): number {
  const remaining = Math.min(30000, budget.deadline - Date.now())
  if (remaining <= 0 || budget.signal.aborted) throw new EngineError('OPERATION_TIMEOUT', 'Native operation budget expired before delivery.', { retryable:false })
  return remaining
}
function axOwnerDump(ax: Ax, dump: Dump[], tree: Tree[], visibleOnly: boolean): Dump {
  if (ax.id === undefined || !ax.bounds) throw new EngineError('NOT_ACTIONABLE', 'Owned AX target has no unique native identity.', { retryable:false })
  const semantic = roles[ax.role ?? '']
  if (!semantic) throw new EngineError('NOT_ACTIONABLE', 'Owned AX target has no documented role.', { retryable:false })
  const hosts = flatten(tree).filter(node => node.tag && node.rect && near(node.rect, ax.bounds!) &&
    (node.role ? node.role === semantic : intrinsicRoles[node.tag!] === semantic || Boolean(ax.name && node.title === ax.name)))
  if (hosts.length !== 1) throw new EngineError('NOT_ACTIONABLE', 'Owned AX action has no unique tree-host identity.', { retryable:false })
  const host = hosts[0]!
  if (!host.rect || !near(host.rect, ax.bounds)) throw new EngineError('NOT_ACTIONABLE', 'Tree host bounds do not agree with the AX owner.', { retryable:false })
  const hostClasses = (host.class ?? '').split(/\s+/).filter(Boolean).slice().sort()
  const owned = dump.filter(node => {
    if (visibleOnly && !node.visible) return false
    if (!near(node.rect, ax.bounds!) || !near(node.rect, host.rect!)) return false
    const parts = (node.path.split('>').at(-1) ?? '').split('.').filter(Boolean)
    if (parts[0] !== host.tag) return false
    const dumpClasses = parts.slice(1).slice().sort()
    return dumpClasses.length === hostClasses.length && dumpClasses.every((name, index) => name === hostClasses[index])
  })
  if (owned.length !== 1) throw new EngineError('NOT_ACTIONABLE', 'Owned AX action has no unique dump identity.', { retryable:false })
  return owned[0]!
}

export class NativeControl {
  readonly manifest: Manifest
  #sequence = 0
  #readers = new Map<string,{ offset:number; carry:string; decoder:StringDecoder; rows:unknown[] }>()
  #nodes = new Map<string,TspNode>()
  #acks = new Map<string,number>()
  #scanned = 0
  #applied = 0
  #operation?: () => OperationContext
  constructor(manifest: Manifest) { this.manifest = manifest }
  bind(operation: () => OperationContext): this { this.#operation = operation; return this }

  #budget(context?: OperationContext): Budget {
    const op = context ?? this.#operation?.()
    if (op?.signal.aborted) throw new EngineError('OPERATION_TIMEOUT', 'Native operation aborted before delivery.', { retryable:false })
    const timeoutMs = op?.timeoutMs ?? 30000
    if (timeoutMs <= 0) throw new EngineError('OPERATION_TIMEOUT', 'Native operation budget expired before delivery.', { retryable:false })
    return { deadline: Date.now() + timeoutMs, signal: op?.signal ?? AbortSignal.timeout(timeoutMs) }
  }

  async ctl(scenario: string, timeout: number, signal?: AbortSignal, delivery?: { started: boolean }): Promise<unknown> {
    if (timeout <= 0 || signal?.aborted) throw new EngineError('OPERATION_TIMEOUT', 'Native control budget expired before delivery.', { retryable:false })
    if (delivery) delivery.started = true
    const { stdout } = await exec('tern', ['ctl','--control',this.manifest.control,scenario], { maxBuffer:32*1024*1024, timeout, signal, killSignal:'SIGKILL' })
    const result: unknown = JSON.parse(stdout)
    if (record(result).ok !== true) throw new EngineError('ENGINE_FAILURE', `Native control failed: ${scenario}: ${stdout}`, { retryable:false })
    return result
  }

  async #inspect(scenario: string, budget: Budget): Promise<unknown> {
    try { return await this.ctl(scenario, preflight(budget), budget.signal) }
    catch (cause) {
      if (expired(budget)) throw new EngineError('OPERATION_TIMEOUT', 'Native inspection exceeded its budget before delivery.', { retryable:false, cause })
      throw cause
    }
  }

  async #dispatch(scenario: string, budget: Budget): Promise<unknown> {
    const delivery = { started: false }
    try { return await this.ctl(scenario, preflight(budget), budget.signal, delivery) }
    catch (cause) {
      if (delivery.started) throw new EngineError('ACTION_MAY_HAVE_COMMITTED', 'Native input failed after dispatch; do not retry it.', { retryable:false, cause })
      if (cause instanceof EngineError && cause.code === 'OPERATION_TIMEOUT') throw cause
      if (expired(budget)) throw new EngineError('OPERATION_TIMEOUT', 'Native input budget expired before delivery.', { retryable:false, cause })
      throw cause
    }
  }

  async #committedSnapshot(budget: Budget): Promise<Snapshot> {
    try { return await this.snapshot(budget) }
    catch (cause) { throw new EngineError('ACTION_MAY_HAVE_COMMITTED', 'Native input may have committed; postflight capture failed.', { retryable:false, cause }) }
  }

  async #execBounded(file: string, args: string[], budget: Budget, extra: { cwd?: string; env?: NodeJS.ProcessEnv } = {}): Promise<string> {
    const timeout = preflight(budget)
    try {
      const { stdout } = await exec(file, args, { maxBuffer:32*1024*1024, timeout, signal:budget.signal, killSignal:'SIGKILL', ...extra })
      return stdout
    } catch (cause) {
      if (expired(budget)) throw new EngineError('OPERATION_TIMEOUT', 'Native resource operation exceeded its budget before completion.', { retryable:false, cause })
      throw cause
    }
  }

  async snapshot(input?: number | OperationContext | Budget): Promise<Snapshot> {
    const budget: Budget = input !== undefined && typeof input === 'object' && 'deadline' in input && 'signal' in input
      ? input
      : typeof input === 'number'
        ? { deadline: input, signal: AbortSignal.timeout(Math.max(1, Math.min(30000, input - Date.now()))) }
        : this.#budget(input)
    const ctl = (scenario:string) => this.#inspect(scenario, budget)
    const state = record(await ctl('state'))
    if (!nativeGateOpen(state.gate)) throw new EngineError('INVALID_STATE','Native Tern account gate blocks visible proof; restore access interactively before any input.',{ retryable:false })
    const panes = state.panes as { id:number }[] | undefined
    const focused = record(state.focused)
    if (!panes?.some(p => String(p.id) === this.manifest.pane) || String(focused.id) !== this.manifest.pane) throw new Error('Native input target changed; parent must reselect the prepared private pane.')
    if (focused.cwd !== this.manifest.root || typeof focused.running !== 'string' || !focused.running.includes(this.manifest.launch)) throw new Error('The prepared private pane is not running its recorded real native launcher.')
    const windowAx = await ctl('a11y') as Ax
    const payload = record(await ctl('tree'))
    const windowTree = payload.tree as Tree[]
    const dumped = record(await ctl('dump *'))
    const windowDump = dumped.elements as Dump[]
    const header = record(dumped.header)
    const viewport = record(header.viewport) as { width:number; height:number }
    if (!Array.isArray(windowTree) || !Array.isArray(windowDump)) throw new Error('Tern native tree/dump is missing; no text/replay fallback is allowed.')
    const visible = (r?: readonly number[]) => Boolean(r && r.length === 4 && r[2]! > 0 && r[3]! > 0 && r[0]! >= 0 && r[1]! >= 0 && r[0]! + r[2]! <= viewport.width + 1 && r[1]! + r[3]! <= viewport.height + 1)
    const panesInTree = flatten(windowTree).filter(node => {
      const classes = (node.class ?? '').split(' ')
      return classes.includes('tn-pane') && classes.includes('on') && !classes.includes('off') && visible(node.rect)
    })
    if (panesInTree.length !== 1) throw new Error('Cannot establish one visible focused native pane subtree.')
    const paneTree = panesInTree[0]!
    const paneDump = windowDump.filter(node => node.visible && near(node.rect, paneTree.rect!) && /^section\.tn-pane(?:\.|$)/.test(node.path.split('>').at(-1) ?? ''))
    if (paneDump.length !== 1) throw new Error('Cannot correlate the focused pane subtree with one native DOM owner.')
    const prefix = paneDump[0]!.nth
    const dump = windowDump.filter(node => node.nth === prefix || node.nth.startsWith(`${prefix}>`))
    const tree = [paneTree]
    const elements = flatten(tree)
    const end = record(await ctl('state'))
    if (!nativeGateOpen(end.gate)) throw new EngineError('INVALID_STATE','Native Tern account gate changed during capture; no input is permitted.',{ retryable:false })
    const after = record(end.focused)
    if (String(after.id) !== this.manifest.pane || after.cwd !== focused.cwd || after.running !== focused.running) throw new Error('Prepared pane ownership changed during native capture.')
    const surfaces = elements.filter(e => (e.class ?? '').split(' ').includes('sf-region') && e.rect)
    const inApp = (r?: readonly number[]) => Boolean(r && surfaces.some(e => r[0]! >= e.rect![0]! - 1 && r[1]! >= e.rect![1]! - 1 && r[0]! + r[2]! <= e.rect![0]! + e.rect![2]! + 1 && r[1]! + r[3]! <= e.rect![1]! + e.rect![3]! + 1))
    const owners = flatten([windowAx]).filter(node => node.role === 'Region' && node.name === 'Agent block' && node.bounds && near(node.bounds,paneTree.rect!))
    if (owners.length !== 1) throw new Error('Cannot correlate one native AX owner with the prepared pane.')
    const ax: Ax = owners[0]!
    const nodes: SemanticNode[] = flatten([ax]).filter(n => n.id !== undefined && n.bounds && n.bounds[2]! > 0 && n.bounds[3]! > 0).map(n => {
      const matching = elements.filter(e => e.rect && near(e.rect, n.bounds!))
      const host = matching.find(e => e.role === roles[n.role ?? '']) ?? matching.find(e => e.input)
      const states = n.states ?? []
      const secure = states.includes('protected') || states.includes('password')
      const value = host?.input?.value ?? n.value
      return {
        ref:{ id:`ax:${n.id}`, revision:'' }, role:roles[n.role ?? ''] ?? 'generic', name:n.name,
        ...(n.bounds ? { rect:box(n.bounds) } : {}),
        ...(n.level !== undefined ? { level:n.level } : {}),
        ...(!secure && value !== undefined ? { value:String(value) } : {}),
        attributes:{ 'native-role':n.role ?? '', ...(n.description ? { description:n.description } : {}) },
        states:{ hidden:!visible(n.bounds) || states.includes('invisible') || states.includes('hidden') || !dump.some(e => e.visible && near(e.rect,n.bounds!)), ...(states.includes('checked') ? { checked:true } : states.includes('unchecked') ? { checked:false } : {}),
          ...(states.includes('selected') ? { selected:true } : {}), ...(states.includes('disabled') ? { disabled:true } : {}),
          ...(states.includes('expanded') ? { expanded:true } : states.includes('collapsed') ? { expanded:false } : {}),
          ...(states.includes('focused') || host?.input?.focused ? { focused:true } : {}), ...(secure ? { secure:true } : {}) }
      }
    })
    const byId = new Map(nodes.map(node => [node.ref.id,node]))
    const lift = (node:Ax): SemanticNode[] => {
      const children = (node.children ?? []).flatMap(lift)
      const own = byId.get(`ax:${node.id}`)
      return own ? [{...own,children}] : children
    }
    const roots = lift(ax)
    for (const [i, e] of elements.entries()) if (e.text && visible(e.rect) && inApp(e.rect) && !nodes.some(node => node.name === e.text)) roots.push({ ref:{ id:`text:${i}:${e.text}`, revision:'' }, role:'text', text:e.text, name:e.text, rect:box(e.rect!) })
    return { ax, tree, dump, nodes:flatten(roots), roots, viewport }
  }

  async reveal(name:string, context?: OperationContext): Promise<void> {
    const budget = this.#budget(context)
    const fresh = await this.snapshot(budget)
    const targets = flatten([fresh.ax]).filter(node => node.name === name && node.id !== undefined)
    if (targets.length !== 1) throw new EngineError('NOT_ACTIONABLE', `Native reveal ${name} has ${targets.length} owned AX targets.`, { retryable:false })
    const target = targets[0]!
    const id = `ax:${target.id}`
    if (fresh.nodes.find(node => node.ref.id === id)?.states?.hidden === false) return
    if (!target.actions?.includes('scroll-into-view') || !target.bounds) throw new EngineError('UNSUPPORTED_CAPABILITY','The owned native target does not expose accessibility scrolling.',{ retryable:false })
    const owner = axOwnerDump(target, fresh.dump, fresh.tree, false)
    await this.#dispatch(`a11y scroll-into-view ${owner.nth}`, budget)
    for (;;) {
      const observed = await this.#committedSnapshot(budget)
      if (observed.nodes.find(node => node.ref.id === id)?.states?.hidden === false) return
      if (expired(budget)) throw new EngineError('ACTION_MAY_HAVE_COMMITTED','Native accessibility scrolling did not paint the target.',{ retryable:false })
      try { await delay(Math.min(100, preflight(budget)), undefined, { signal:budget.signal }) }
      catch (cause) { throw new EngineError('ACTION_MAY_HAVE_COMMITTED','Native accessibility scrolling may have committed before cancellation.',{ retryable:false,cause }) }
    }
  }

  async fieldVisible(label: string, context?: OperationContext): Promise<boolean> {
    const fresh = await this.snapshot(this.#budget(context))
    const labels = flatten(fresh.tree)
      .filter(node => (node.class ?? '').split(' ').includes('pf-row'))
      .flatMap(row => (row.children ?? []).filter(node => (node.class ?? '').split(' ').includes('pf-lbl')))
      .flatMap(rowLabel => (rowLabel.children ?? []).filter(node => (node.class ?? '').split(' ').includes('t')))
      .filter(title => flatten([title]).map(node => node.text ?? '').join('') === label
        && title.rect && fresh.dump.some(element => element.visible && near(element.rect,title.rect!)))
    if (labels.length > 1) throw new Error(`Multiple visible native row labels: ${label}`)
    return labels.length === 1
  }

  async click(id: string, context?: OperationContext): Promise<void> {
    const budget = this.#budget(context)
    const fresh = await this.snapshot(budget)
    const node = fresh.nodes.find(n => n.ref.id === id)
    if (!node) throw new EngineError('NODE_STALE', 'The native AX/tree target was replaced.', { retryable:true })
    if (node.states?.hidden || !node.rect) throw new EngineError('NOT_ACTIONABLE', 'Native target is not entirely visible in the isolated viewport.', { retryable:false })
    if (/Confirm exact change|Switch anyway|Allow|Grant|Sign in|Restart to update/.test(node.name ?? '')) throw new EngineError('NOT_ACTIONABLE', 'This suite never grants or confirms consequential actions.', { retryable:false })
    const ax = flatten([fresh.ax]).find(n => `ax:${n.id}` === id)
    const r = [node.rect.x,node.rect.y,node.rect.width,node.rect.height]
    let target: Dump
    if (ax?.actions?.includes('click')) {
      target = axOwnerDump(ax, fresh.dump, fresh.tree, true)
      await appendFile(join(this.manifest.proof,'native-actions.jsonl'),JSON.stringify({ time:Date.now(), id, name:node.name, role:node.role, rect:r, nth:target.nth, path:target.path, action:'a11y click' })+'\n',{ mode:0o600 })
      await this.#dispatch(`a11y click ${target.nth}`, budget)
    } else {
      let matches = fresh.dump.filter(e => e.visible && near(e.rect,r))
      const deepest = matches.filter(e => !matches.some(other => other !== e && other.path.startsWith(`${e.path}>`)))
      matches = deepest
      if (matches.length !== 1) throw new EngineError('NOT_ACTIONABLE', `AX ${node.name ?? id} has ${matches.length} deepest visible DOM matches (expected exactly one).`, { retryable:false })
      target = matches[0]!
      await appendFile(join(this.manifest.proof,'native-actions.jsonl'),JSON.stringify({ time:Date.now(), id, name:node.name, role:node.role, rect:r, nth:target.nth, path:target.path, action:'click' })+'\n',{ mode:0o600 })
      await this.#dispatch(`click ${target.nth}`, budget)
    }
    await this.#committedSnapshot(budget)
  }

  async key(key: Key, context?: OperationContext): Promise<void> {
    const parsed = parseKey(key)
    if (!parsed || parsed.modifiers.length) throw new EngineError('UNSUPPORTED_CAPABILITY', 'Modifier keys are intentionally unsupported: Tern0.6 Linux control translates Ctrl into Meta.', { retryable:false })
    const keys: Record<string,string> = { Enter:'enter',Escape:'escape',Backspace:'backspace',Delete:'delete',Home:'home',End:'end',ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down',Tab:'tab',Space:'space',PageDown:'pagedown',PageUp:'pageup' }
    const name = parsed.key.kind === 'named' ? parsed.key.name : parsed.key.char
    const combo = keys[name] ?? (name.length === 1 ? name : undefined)
    if (!combo) throw new EngineError('UNSUPPORTED_CAPABILITY', `Unsupported native key ${key}`, { retryable:false })
    const budget = this.#budget(context)
    await this.snapshot(budget)
    await this.#dispatch(`key ${combo}`, budget)
    await this.#committedSnapshot(budget)
  }

  async type(text: string, context?: OperationContext): Promise<void> {
    const budget = this.#budget(context)
    await this.snapshot(budget)
    await this.#dispatch(`type ${JSON.stringify(text)}`, budget)
    await this.#committedSnapshot(budget)
  }

  async #records(path:string, budget?: Budget): Promise<unknown[]> {
    if (budget) preflight(budget)
    let reader = this.#readers.get(path)
    if (!reader) {
      reader = {offset:0,carry:'',decoder:new StringDecoder('utf8'),rows:[]}
      this.#readers.set(path,reader)
    }
    const file = await open(path,'r')
    try {
      const {size} = await file.stat()
      if (size < reader.offset) throw new Error('A private proof record was truncated during the live attempt.')
      if (size > reader.offset) {
        const bytes = Buffer.allocUnsafe(size-reader.offset)
        let count = 0
        while (count < bytes.length) {
          if (budget && expired(budget)) throw new EngineError('OPERATION_TIMEOUT','Native record read exceeded its budget.',{ retryable:false })
          const {bytesRead} = await file.read(bytes,count,bytes.length-count,reader.offset+count)
          if (!bytesRead) break
          count += bytesRead
        }
        reader.offset += count
        const lines = (reader.carry+reader.decoder.write(bytes.subarray(0,count))).split('\n')
        reader.carry = lines.pop() ?? ''
        for (const line of lines) if (line) reader.rows.push(JSON.parse(line) as unknown)
      }
    } finally { await file.close() }
    return reader.rows
  }

  async wire(context?: OperationContext): Promise<Wire[]> { return await this.#records(this.manifest.record, this.#budget(context)) as Wire[] }
  async frames(context?: OperationContext): Promise<TspFrame[]> { return await this.#records(this.manifest.tsp, this.#budget(context)) as TspFrame[] }

  async rendered(context?: OperationContext): Promise<Map<string,TspNode>> {
    const budget = this.#budget(context)
    const nodes = this.#nodes
    const add = (node:TspNode): void => { nodes.set(node.id,{...node,p:{...node.p}}); for (const child of node.c ?? []) add(child) }
    const remove = (id:string): void => { for (const key of nodes.keys()) if (key === id || key.startsWith(`${id}.`)) nodes.delete(key) }
    const frames = await this.#records(this.manifest.tsp, budget) as TspFrame[]
    for (;this.#scanned<frames.length;this.#scanned++) {
      const frame = frames[this.#scanned]!
      if (frame.dir === 'in' && frame.body.ev === 'ack' && frame.body.sf && frame.body.s !== undefined) this.#acks.set(frame.body.sf,frame.body.s)
    }
    for (;this.#applied<frames.length;this.#applied++) {
      if (expired(budget)) throw new EngineError('OPERATION_TIMEOUT','Native render accounting exceeded its budget.',{ retryable:false })
      const frame = frames[this.#applied]!
      if (frame.dir !== 'out') continue
      if (frame.verb === 'f' && (frame.body.s ?? 0) > (this.#acks.get(frame.body.sf ?? '') ?? -1)) break
      if (frame.verb === 'x' && frame.body.id) nodes.clear()
      for (const op of frame.body.ops ?? []) {
        if (op[0] === 'add') add(op[4] as unknown as TspNode)
        else if (op[0] === 'del') remove(String(op[1]))
        else if (op[0] === 'set') {
          const node = nodes.get(String(op[1]))
          if (node) for (const [key,value] of Object.entries(op[2] as Record<string,Json>)) {
            if (value === null) delete node.p![key]
            else node.p![key] = value
          }
        } else if (op[0] === 'text') {
          const node = nodes.get(String(op[1]))
          if (node) node.p = {...node.p,text:op[2] === 'append' ? String(node.p?.text ?? '') + String(op[3]) : op[3]!}
        } else if (op[0] === 'splice') {
          const node = nodes.get(String(op[1]))
          if (node) {
            const text = String(node.p?.text ?? '')
            const from = Number(op[2]), count = Number(op[3])
            node.p = {...node.p,text:text.slice(0,from) + String(op[4]) + text.slice(from+count)}
          }
        }
      }
    }
    return nodes
  }

  async prefs(context?: OperationContext): Promise<Prefs | undefined> {
    const nodes = [...(await this.rendered(context)).values()].filter(n => n.k === 'prefs' && n.p?.title === 'Hermes settings')
    if (nodes.length > 1) throw new Error('Multiple live native Settings owners.')
    return nodes[0] as unknown as Prefs | undefined
  }

  async settings(context?: OperationContext): Promise<SettingsResult> {
    const wire = await this.wire(context)
    const ids = new Set(wire.filter(w => w.dir === 'request' && w.body.method === 'settings.get').map(w => w.body.id))
    const result = wire.filter(w => w.dir === 'delivered' && ids.has(w.body.id) && w.body.result).at(-1)?.body.result
    if (!result) throw new Error('No real delivered settings.get response has been observed.')
    return result as unknown as SettingsResult
  }

  async config(context?: OperationContext): Promise<Record<string,Json>> {
    const budget = this.#budget(context)
    const stdout = await this.#execBounded(this.manifest.python,[join(this.manifest.proof,'state.py'),join(this.manifest.proof,'manifest.json')],budget,{ cwd:this.manifest.root,env:{...process.env,HERMES_HOME:this.manifest.home,HERMES_PYTHON_SRC_ROOT:this.manifest.root} })
    return JSON.parse(stdout) as Record<string,Json>
  }

  async configBytes(context?: OperationContext): Promise<string> {
    preflight(this.#budget(context))
    return readFile(join(this.manifest.home,'config.yaml'),'utf8')
  }

  async schema(context?: OperationContext): Promise<Record<string,{ type:string; category:string }>> {
    const budget = this.#budget(context)
    const stdout = await this.#execBounded(this.manifest.python,[join(this.manifest.proof,'state.py'),join(this.manifest.proof,'manifest.json'),'schema'],budget,{cwd:this.manifest.root})
    return JSON.parse(stdout) as Record<string,{ type:string; category:string }>
  }

  async hold(method: 'settings.get' | 'settings.set', key?: string, context?: OperationContext): Promise<string> {
    preflight(this.#budget(context))
    const token = `native-e2e-${randomUUID()}`
    const temporary = `${this.manifest.gate}.${token}.tmp`
    await writeFile(temporary,JSON.stringify({token,method,key,expires:Date.now()+60000}),{mode:0o600})
    await rename(temporary,this.manifest.gate)
    return token
  }

  async release(context?: OperationContext): Promise<void> {
    preflight(this.#budget(context))
    await unlink(this.manifest.gate).catch(error => { if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error })
  }

  async evidence(label: string, context?: OperationContext): Promise<void> {
    const budget = this.#budget(context)
    const name = `${String(++this.#sequence).padStart(4,'0')}-${label.replace(/[^a-zA-Z0-9_-]/g,'-')}`
    const dir = join(this.manifest.proof,'observations')
    await mkdir(dir,{recursive:true,mode:0o700})
    const snapshot = await this.snapshot(budget)
    const pending = join(dir,`${name}.pending.png`)
    await this.#execBounded('grim',['-o','HEADLESS-1',pending],budget,{env:{...process.env,XDG_RUNTIME_DIR:this.manifest.runtime,WAYLAND_DISPLAY:this.manifest.display}})
    const after = record(await this.#inspect('state',budget))
    const focused = record(after.focused)
    if (!nativeGateOpen(after.gate) || String(focused.id) !== this.manifest.pane || focused.cwd !== this.manifest.root || typeof focused.running !== 'string' || !focused.running.includes(this.manifest.launch)) {
      throw new EngineError('INVALID_STATE','Native ownership changed during screenshot capture; this image is not accepted as evidence.',{ retryable:false })
    }
    await writeFile(join(dir,`${name}.json`),JSON.stringify(snapshot),{mode:0o600})
    await rename(pending,join(dir,`${name}.png`))
  }
}

export function nativeControlEngine(native: NativeControl): EngineHandle {
  let owner: { fd: number; path: string; dev: number; ino: number } | undefined
  return defineEngine({
    name:'hermes-native-control',version:'1.0.0',spiVersion:1,platform:'desktop',
    actions:['tap','press'],
    async startAttempt(context) {
      assertOwnedInert(native.manifest)
      context.signal.throwIfAborted()
      if (owner) throw new EngineError('NOT_ACTIONABLE', 'Native inert proof already has an active engine owner.', { retryable:false })
      const path = join(realpathSync(native.manifest.proof), '.native-settings-engine-owner')
      let fd: number
      try { fd = openSync(path, 'wx', 0o600) }
      catch (cause) { throw new EngineError('NOT_ACTIONABLE', 'Cannot claim native inert proof; use a distinct explorer fixture.', { retryable:false, cause }) }
      const stat = fstatSync(fd)
      owner = { fd, path, dev:stat.dev, ino:stat.ino }
    },
    async observe(context) { const s = await native.snapshot(context); return {location:`tern-private:${native.manifest.control}/${native.manifest.pane}`,root:{ref:{id:'root',revision:''},role:'window',children:s.roots},viewport:s.viewport} },
    async locate(expression, context) { return resolveExpression(expression,(await native.snapshot(context)).roots) },
    async perform(ref,action,context) {
      if (action.kind === 'tap') await native.click(ref.id, context)
      else if (action.kind === 'press') await native.key(action.key, context)
      else throw new EngineError('UNSUPPORTED_CAPABILITY',`Native suite adapter does not perform ${action.kind}`,{retryable:false})
    },
    keyboard:{ type:(text,_options,context) => native.type(text, context), press:(key,context) => native.key(key, context) },
    fixtures:{ native:context => context.fixture('native',new NativeControl(native.manifest).bind(() => context.operation()),{
      key:{kind:'resource',label:key => key},type:{kind:'resource',label:text => text},
      snapshot:{kind:'resource'},wire:{kind:'resource'},frames:{kind:'resource'},rendered:{kind:'resource'},
      prefs:{kind:'resource'},settings:{kind:'resource'},config:{kind:'resource'},configBytes:{kind:'resource'},
      fieldVisible:{kind:'resource',label:label => label},
      reveal:{kind:'resource',label:name => name},
      schema:{kind:'resource'},hold:{kind:'resource'},release:{kind:'resource'},evidence:{kind:'resource',label:label => label}
    }) },
    async endAttempt() {
      if (!owner) return
      const claim = owner
      owner = undefined
      try { await native.release() }
      finally {
        try {
          const quarantine = mkdtempSync(join(native.manifest.proof, '.native-settings-owner-release-'))
          const path = join(quarantine, 'owner')
          renameSync(claim.path, path)
          const stat = lstatSync(path)
          if (stat.dev !== claim.dev || stat.ino !== claim.ino) throw new EngineError('NOT_ACTIONABLE', 'Native owner identity changed; retain claimed evidence.', { retryable:false })
          unlinkSync(path)
          rmdirSync(quarantine)
        } finally { closeSync(claim.fd) }
      }
    }
  })
}
