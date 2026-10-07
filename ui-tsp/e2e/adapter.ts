import { randomUUID } from 'node:crypto'
import { execFile } from 'node:child_process'
import { appendFile, mkdir, open, readFile, rename, unlink, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { StringDecoder } from 'node:string_decoder'
import { promisify } from 'node:util'
import { defineEngine, EngineError, parseKey, resolveExpression, type EngineHandle, type Key, type SemanticNode } from 'e2e/engine'
import { flatten, record, type Json, type Manifest, type Prefs, type SettingsResult, type TspFrame, type TspNode, type Wire } from './types.ts'

const exec = promisify(execFile)
interface Ax {
  id?: number; role?: string; name?: string; description?: string; value?: string | number
  bounds?: number[]; states?: string[]; children?: Ax[]; level?: number
}
interface Tree {
  tag?: string; id?: string; role?: string; class?: string; title?: string; text?: string; rect?: number[]
  input?: { value?: string; focused?: boolean; selectionStart?: number; selectionEnd?: number }
  children?: Tree[]
}
interface Dump { path: string; nth: string; rect: number[]; visible: boolean }
interface Snapshot { ax: Ax; tree: Tree[]; dump: Dump[]; nodes: SemanticNode[]; roots: SemanticNode[]; viewport: { width: number; height: number } }
const roles: Record<string, string> = {
  Window:'window', Button:'button', Switch:'switch', CheckBox:'checkbox', RadioButton:'radio', RadioGroup:'radiogroup',
  ComboBox:'combobox', TextInput:'textbox', MultilineTextInput:'textbox', TextBox:'textbox', TextField:'textbox',
  SearchField:'searchbox', Meter:'meter', Heading:'heading', Group:'group', Region:'region', Tab:'tab', ListBox:'listbox'
}
const near = (a: readonly number[], b: readonly number[]) => a.length === 4 && b.length === 4 && a.every((v, i) => Math.abs(v - b[i]!) <= 1)
const box = (r: readonly number[]) => ({ x:r[0]!, y:r[1]!, width:r[2]!, height:r[3]! })

export class NativeControl {
  readonly manifest: Manifest
  #sequence = 0
  #readers = new Map<string,{ offset:number; carry:string; decoder:StringDecoder; rows:unknown[] }>()
  #nodes = new Map<string,TspNode>()
  #acks = new Map<string,number>()
  #scanned = 0
  #applied = 0
  constructor(manifest: Manifest) { this.manifest = manifest }

  async ctl(scenario: string): Promise<unknown> {
    const { stdout } = await exec('tern', ['ctl','--control',this.manifest.control,scenario], { maxBuffer:32*1024*1024, timeout:30000 })
    const result: unknown = JSON.parse(stdout)
    if (record(result).ok !== true) throw new EngineError('ENGINE_FAILURE', `Native control failed: ${scenario}: ${stdout}`, { retryable:false })
    return result
  }

  async snapshot(): Promise<Snapshot> {
    const state = record(await this.ctl('state'))
    const panes = state.panes as { id:number }[] | undefined
    const focused = record(state.focused)
    if (!panes?.some(p => String(p.id) === this.manifest.pane) || String(focused.id) !== this.manifest.pane) throw new Error('Native input target changed; parent must reselect the prepared private pane.')
    if (focused.cwd !== this.manifest.root || typeof focused.running !== 'string' || !focused.running.includes(this.manifest.launch)) throw new Error('The prepared private pane is not running its recorded real native launcher.')
    // Serial captures avoid combining snapshots from independently racing UI actions.
    const ax = await this.ctl('a11y') as Ax
    const payload = record(await this.ctl('tree'))
    const tree = payload.tree as Tree[]
    const dumped = record(await this.ctl('dump *'))
    const dump = dumped.elements as Dump[]
    const header = record(dumped.header)
    const viewport = record(header.viewport) as { width:number; height:number }
    if (!Array.isArray(tree) || !Array.isArray(dump)) throw new Error('Tern native tree/dump is missing; no text/replay fallback is allowed.')
    const elements = flatten(tree)
    const visible = (r?: readonly number[]) => Boolean(r && r.length === 4 && r[2]! > 0 && r[3]! > 0 && r[0]! >= 0 && r[1]! >= 0 && r[0]! + r[2]! <= viewport.width + 1 && r[1]! + r[3]! <= viewport.height + 1)
    const surfaces = elements.filter(e => (e.class ?? '').split(' ').includes('sf-region') && e.rect)
    const inApp = (r?: readonly number[]) => Boolean(r && surfaces.some(e => r[0]! >= e.rect![0]! - 1 && r[1]! >= e.rect![1]! - 1 && r[0]! + r[2]! <= e.rect![0]! + e.rect![2]! + 1 && r[1]! + r[3]! <= e.rect![1]! + e.rect![3]! + 1))
    const nodes: SemanticNode[] = flatten([ax]).filter(n => n.id !== undefined && n.bounds && inApp(n.bounds)).map(n => {
      const matching = elements.filter(e => e.rect && near(e.rect, n.bounds!))
      const host = matching.find(e => e.role === roles[n.role ?? '']) ?? matching.find(e => e.input)
      const states = n.states ?? []
      const secure = states.includes('protected') || states.includes('password')
      // Do not invent values from defaults, text labels, or unchecked absence.
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
    // Add only native DOM text not already named by AX. This prevents one
    // form label from becoming two locator matches (AX field + DOM label).
    for (const [i, e] of elements.entries()) if (e.text && visible(e.rect) && inApp(e.rect) && !nodes.some(node => node.name === e.text)) roots.push({ ref:{ id:`text:${i}:${e.text}`, revision:'' }, role:'text', text:e.text, name:e.text, rect:box(e.rect!) })
    return { ax, tree, dump, nodes:flatten(roots), roots, viewport }
  }

  async fieldVisible(label: string): Promise<boolean> {
    const fresh = await this.snapshot()
    // Scope to the painted native row label, not the identical search query.
    const labels = flatten(fresh.tree)
      .filter(node => (node.class ?? '').split(' ').includes('pf-row'))
      .flatMap(row => (row.children ?? []).filter(node => (node.class ?? '').split(' ').includes('pf-lbl')))
      .flatMap(label => (label.children ?? []).filter(node => (node.class ?? '').split(' ').includes('t')))
      .filter(title => flatten([title]).map(node => node.text ?? '').join('') === label
        && title.rect && fresh.dump.some(element => element.visible && near(element.rect,title.rect!)))
    if (labels.length > 1) throw new Error(`Multiple visible native row labels: ${label}`)
    return labels.length === 1
  }

  async click(id: string): Promise<void> {
    const fresh = await this.snapshot()
    const node = fresh.nodes.find(n => n.ref.id === id)
    if (!node) throw new EngineError('NODE_STALE', 'The native AX/tree target was replaced.', { retryable:true })
    if (node.states?.hidden || !node.rect) throw new EngineError('NOT_ACTIONABLE', 'Native target is not entirely visible in the isolated viewport.', { retryable:false })
    if (/Confirm exact change|Switch anyway|Allow|Grant|Sign in|Restart to update/.test(node.name ?? '')) throw new EngineError('NOT_ACTIONABLE', 'This suite never grants or confirms consequential actions.', { retryable:false })
    const r = [node.rect.x,node.rect.y,node.rect.width,node.rect.height]
    let matches = fresh.dump.filter(e => e.visible && near(e.rect,r))
    // An AX field may share its bounds with a generic parent. Prefer the
    // descendant semantic element; never guess by class or row position.
    const deepest = matches.filter(e => !matches.some(other => other !== e && other.path.startsWith(`${e.path}>`)))
    matches = deepest
    if (matches.length !== 1) throw new EngineError('NOT_ACTIONABLE', `AX ${node.name ?? id} has ${matches.length} deepest visible DOM matches (expected exactly one).`, { retryable:false })
    const target = matches[0]!
    await appendFile(join(this.manifest.proof,'native-actions.jsonl'),JSON.stringify({ time:Date.now(), id, name:node.name, role:node.role, rect:r, nth:target.nth, path:target.path })+'\n',{ mode:0o600 })
    try { await this.ctl(`click ${target.nth}`) } catch (cause) { throw new EngineError('ACTION_MAY_HAVE_COMMITTED','Native click failed after dispatch; do not retry it.',{ retryable:false, cause }) }
    await this.snapshot()
  }

  async key(key: Key): Promise<void> {
    const parsed = parseKey(key)
    if (!parsed || parsed.modifiers.length) throw new EngineError('UNSUPPORTED_CAPABILITY', 'Modifier keys are intentionally unsupported: Tern0.6 Linux control translates Ctrl into Meta.', { retryable:false })
    const keys: Record<string,string> = { Enter:'enter',Escape:'escape',Backspace:'backspace',Delete:'delete',Home:'home',End:'end',ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down',Tab:'tab',Space:'space',PageDown:'pagedown',PageUp:'pageup' }
    const name = parsed.key.kind === 'named' ? parsed.key.name : parsed.key.char
    const combo = keys[name] ?? (name.length === 1 ? name : undefined)
    if (!combo) throw new EngineError('UNSUPPORTED_CAPABILITY', `Unsupported native key ${key}`, { retryable:false })
    await this.snapshot()
    await this.ctl(`key ${combo}`)
    await this.snapshot()
  }

  async type(text: string): Promise<void> {
    await this.snapshot()
    await this.ctl(`type ${JSON.stringify(text)}`)
    await this.snapshot()
  }

  async #records(path:string): Promise<unknown[]> {
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

  async wire(): Promise<Wire[]> { return await this.#records(this.manifest.record) as Wire[] }

  async frames(): Promise<TspFrame[]> { return await this.#records(this.manifest.tsp) as TspFrame[] }

  async rendered(): Promise<Map<string,TspNode>> {
    const nodes = this.#nodes
    const add = (node:TspNode): void => { nodes.set(node.id,{...node,p:{...node.p}}); for (const child of node.c ?? []) add(child) }
    const remove = (id:string): void => { for (const key of nodes.keys()) if (key === id || key.startsWith(`${id}.`)) nodes.delete(key) }
    const frames = await this.frames()
    for (;this.#scanned<frames.length;this.#scanned++) {
      const frame = frames[this.#scanned]!
      if (frame.dir === 'in' && frame.body.ev === 'ack' && frame.body.sf && frame.body.s !== undefined) this.#acks.set(frame.body.sf,frame.body.s)
    }
    for (;this.#applied<frames.length;this.#applied++) {
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

  async prefs(): Promise<Prefs | undefined> {
    const nodes = [...(await this.rendered()).values()].filter(n => n.k === 'prefs' && n.p?.title === 'Hermes settings')
    if (nodes.length > 1) throw new Error('Multiple live native Settings owners.')
    return nodes[0] as unknown as Prefs | undefined
  }

  async settings(): Promise<SettingsResult> {
    const wire = await this.wire()
    const ids = new Set(wire.filter(w => w.dir === 'request' && w.body.method === 'settings.get').map(w => w.body.id))
    const result = wire.filter(w => w.dir === 'delivered' && ids.has(w.body.id) && w.body.result).at(-1)?.body.result
    if (!result) throw new Error('No real delivered settings.get response has been observed.')
    return result as unknown as SettingsResult
  }

  async config(): Promise<Record<string,Json>> {
    const { stdout } = await exec(this.manifest.python,[join(this.manifest.proof,'state.py'),join(this.manifest.proof,'manifest.json')],{ cwd:this.manifest.root,env:{...process.env,HERMES_HOME:this.manifest.home,HERMES_PYTHON_SRC_ROOT:this.manifest.root},timeout:10000 })
    return JSON.parse(stdout) as Record<string,Json>
  }

  async configBytes(): Promise<string> { return readFile(join(this.manifest.home,'config.yaml'),'utf8') }

  async schema(): Promise<Record<string,{ type:string; category:string }>> {
    const { stdout } = await exec(this.manifest.python,[join(this.manifest.proof,'state.py'),join(this.manifest.proof,'manifest.json'),'schema'],{cwd:this.manifest.root,timeout:30000})
    return JSON.parse(stdout) as Record<string,{ type:string; category:string }>
  }

  async hold(method: 'settings.get' | 'settings.set', key?: string): Promise<string> {
    const token = `native-e2e-${randomUUID()}`
    const temporary = `${this.manifest.gate}.${token}.tmp`
    await writeFile(temporary,JSON.stringify({token,method,key,expires:Date.now()+60000}),{mode:0o600})
    await rename(temporary,this.manifest.gate)
    return token
  }

  async release(): Promise<void> { await unlink(this.manifest.gate).catch(error => { if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error }) }

  async evidence(label: string): Promise<void> {
    const name = `${String(++this.#sequence).padStart(4,'0')}-${label.replace(/[^a-zA-Z0-9_-]/g,'-')}`
    const dir = join(this.manifest.proof,'observations')
    await mkdir(dir,{recursive:true,mode:0o700})
    await writeFile(join(dir,`${name}.json`),JSON.stringify(await this.snapshot()),{mode:0o600})
    await exec('grim',['-o','HEADLESS-1',join(dir,`${name}.png`)],{env:{...process.env,XDG_RUNTIME_DIR:this.manifest.runtime,WAYLAND_DISPLAY:this.manifest.display},timeout:10000})
  }
}

export function nativeControlEngine(native: NativeControl): EngineHandle {
  return defineEngine({
    name:'hermes-native-control',version:'1.0.0',spiVersion:1,platform:'desktop',
    actions:['tap','press'],
    async observe() { const s = await native.snapshot(); return {location:`tern-private:${native.manifest.control}/${native.manifest.pane}`,root:{ref:{id:'root',revision:''},role:'window',children:s.roots},viewport:s.viewport} },
    async locate(expression) { return resolveExpression(expression,(await native.snapshot()).roots) },
    async perform(ref,action) {
      if (action.kind === 'tap') await native.click(ref.id)
      else if (action.kind === 'press') await native.key(action.key)
      else throw new EngineError('UNSUPPORTED_CAPABILITY',`Native suite adapter does not perform ${action.kind}`,{retryable:false})
    },
    keyboard:{ type:text => native.type(text),press:key => native.key(key) },
    fixtures:{ native:context => context.fixture('native',new NativeControl(native.manifest),{
      key:{kind:'resource',label:key => key},type:{kind:'resource',label:text => text},
      snapshot:{kind:'resource'},wire:{kind:'resource'},frames:{kind:'resource'},rendered:{kind:'resource'},
      prefs:{kind:'resource'},settings:{kind:'resource'},config:{kind:'resource'},configBytes:{kind:'resource'},
      fieldVisible:{kind:'resource',label:label => label},
      schema:{kind:'resource'},hold:{kind:'resource'},release:{kind:'resource'},evidence:{kind:'resource',label:label => label}
    }) },
    async endAttempt() { await native.release() }
  })
}
