// Per-feature journeys over the same fail-closed native-control adapter as the full suite.
import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { appendFile, readFile, writeFile } from 'node:fs/promises'
import { promisify } from 'node:util'
import { join } from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { NativeControl } from './adapter.ts'
import { assertOwnedInert, flatten, record, type Manifest, type Json } from './types.ts'

const manifest = JSON.parse(await readFile(process.argv[2]!, 'utf8')) as Manifest
assertOwnedInert(manifest)
const journey = process.argv[3]!
const native = new NativeControl(manifest)
const evidenceClass = manifest.evidenceClass ?? 'native-window'
const results: unknown[] = []
async function step(name: string, fn: () => Promise<void>, fixture = false) {
  const start = Date.now()
  try {
    await fn()
    results.push({ name, status:'pass', evidenceClass:evidenceClass + (fixture ? '+fixture-replay' : '+real-gateway'), ms:Date.now()-start })
  } catch (error) {
    await native.evidence(`${journey}-failure`).catch(captureError => console.error('diagnostic capture:',captureError))
    results.push({ name, status:'fail', evidenceClass, error:String(error), ms:Date.now()-start })
    throw error
  } finally { await writeFile(join(manifest.proof, 'steps.json'), JSON.stringify({ journey, results }, null, 2)) }
}
async function until<T>(fn: () => Promise<T>, accepts: (value:T) => boolean, label: string): Promise<T> {
  const end = Date.now()+30000
  let last: T | undefined
  do { last = await fn(); if (accepts(last)) return last; await delay(100) } while (Date.now()<end)
  throw new Error(`Timed out: ${label}; last=${JSON.stringify(last)?.slice(0,800)}`)
}
async function tap(name: string, role?: string) {
  // Resolve only after the actual native target stops moving/reconciling.
  // This is a pre-delivery wait, never a retry of potentially committed input.
  let previous = ''
  const matches = await until(async()=>{
    const snapshot = await native.snapshot()
    return snapshot.nodes.filter(n => n.name === name && (!role || n.role === role) && !n.states?.hidden)
  }, nodes=>{
    const identity = nodes.length===1 ? JSON.stringify({ref:nodes[0]!.ref.id,rect:nodes[0]!.rect}) : ''
    const stable = identity !== '' && identity === previous
    previous = identity
    return stable
  }, `stable exact owned visible target: ${role ?? ''} ${name}`)
  await native.click(matches[0]!.ref.id)
}
async function command(text: string) {
  assert.equal((await native.rendered()).get('dock.composer.line.input')?.p?.text, '')
  await native.type(text)
  await until(() => native.rendered(), ns => ns.get('dock.composer.line.input')?.p?.text === text, 'composer command')
  await native.key('Enter')
}
async function capture(label: string) {
  await native.evidence(`${journey}-${label}`)
}
async function sizes() {
  // Measure actual PTY cells; no inference from requested pixel dimensions.
  await native.snapshot()
  await native.ctl('font 15', 30000)
  for (const [cols, rows] of [[80,28],[120,36],[180,44]]) {
    let width = cols!*9+24, height = rows!*20+56
    let actual: unknown
    let matched = false
    for (let attempt=0; attempt<40; attempt++) {
      await native.snapshot()
      await native.ctl(`resize ${width} ${height}`, 30000)
      await delay(150)
      const state = record(await native.ctl('state', 30000))
      const pane = (state.panes as {id:number;cols:number;rows:number}[]).find(p => String(p.id) === manifest.pane)
      actual = pane
      if (!pane) break
      if (pane.cols === cols && pane.rows === rows) { matched = true; break }
      width += Math.abs(cols!-pane.cols) <= 1 ? Math.sign(cols!-pane.cols) : (cols!-pane.cols)*9
      height += Math.abs(rows!-pane.rows) <= 1 ? Math.sign(rows!-pane.rows) : (rows!-pane.rows)*20
    }
    await appendFile(join(manifest.proof,'sizes.jsonl'), JSON.stringify({ requested:[cols,rows], actual, matched, evidenceClass })+'\n')
    await capture(`${cols}x${rows}${matched ? '' : '-actual-mismatch'}`)
  }
}
let sid = ''
async function replay(type: string, payload: Record<string, Json> = {}) {
  assert(manifest.fixtureEvents)
  await appendFile(manifest.fixtureEvents, JSON.stringify({ type, session_id:sid, payload })+'\n', {mode:0o600})
}
async function fixtureTurn() {
  await replay('message.start')
  await replay('reasoning.delta', { text:'Do not copy this private reasoning fixture.' })
  await replay('tool.start', { name:'read_file', tool_id:'read-e2e', args:{path:'README.md',offset:1,limit:2} })
  const lines = (await readFile(join(manifest.root,'README.md'),'utf8')).split('\n').slice(0,2)
  await replay('tool.complete', { name:'read_file', tool_id:'read-e2e', result:{content:lines.map((s,i) => `${i+1}|${s}`).join('\n')} })
  await replay('message.delta', { text:'E2E visible answer.' })
  await replay('message.complete', { status:'complete', text:'E2E visible answer.' })
  await until(() => native.rendered(), ns => [...ns.values()].some(n => n.p?.role === 'omp.turn.copy'), 'completed fixture answer')
}
async function settings() {
  const before = await native.configBytes()
  await step('open /settings and real schema readback', async () => {
    await command('/settings')
    await until(() => native.prefs(), p => p?.p.title === 'Hermes settings', 'Settings sheet')
    const schema = await native.schema()
    await until(()=>native.wire(), rows=>rows.some(w=>w.dir==='delivered' && w.body.result && typeof w.body.result==='object' && !Array.isArray(w.body.result) && 'fields' in w.body.result), 'real settings.get response')
    const getter = await native.settings()
    await until(()=>native.prefs(), p=>Boolean(p?.p.sections?.some(section=>section.rows.length)), 'acknowledged populated Settings view')
    assert.deepEqual(Object.keys(getter.fields).sort(), Object.keys(schema).sort())
    await writeFile(join(manifest.proof,'schema-summary.json'), JSON.stringify({fields:Object.keys(schema).length,categories:new Set(Object.values(schema).map(x=>x.category)).size,types:[...new Set(Object.values(schema).map(x=>x.type))]}))
  })
  await step('navigate Session and profile field', async () => {
    await tap('Session', 'button')
    await until(() => native.prefs(), p => p?.p.page === 'session', 'Session page')
    await native.type('agent.environment_hint')
    await until(() => native.prefs(), p => p?.p.query === 'agent.environment_hint', 'global search')
    await until(() => native.fieldVisible('agent.environment_hint'), Boolean, 'painted profile row')
  })
  await step('edit and Escape cancels with byte-identical config', async () => {
    await native.key('ArrowDown')
    await until(() => native.prefs(), p => p?.p.focus === 'agent.environment_hint', 'selected field')
    await native.key('Enter')
    await until(() => native.prefs(), p => p?.p.editing?.row === 'agent.environment_hint', 'editor')
    await native.type(' cancelled-e2e-edit')
    await until(() => native.prefs(), p => Boolean(p?.p.editing?.draft?.includes('cancelled-e2e-edit')), 'typed edit')
    await capture('edit-before-cancel')
    await native.key('Escape')
    await until(() => native.prefs(), p => !p?.p.editing, 'editor cancelled')
    assert.equal(await native.configBytes(), before)
    assert(!(await native.wire()).some(w => w.dir === 'request' && w.body.method === 'settings.set'))
    await tap('Close settings','button')
    await until(() => native.prefs(), p => !p, 'closed')
    await command('/settings')
    await until(() => native.prefs(), p => p?.p.title === 'Hermes settings', 'readback reopened')
    assert.equal((await native.settings()).fields['agent.environment_hint']?.value, 'e2e-initial-hint')
    await sizes()
  })
}
async function fileLinks() {
  await step('read card from explicit fixture replay', fixtureTurn, true)
  await step('modifier click read href opens exact README target', async () => {
    const nodes = await native.rendered()
    const tool = [...nodes.values()].find(n => n.k === 'tool' && n.p?.href === `file://${manifest.root}/README.md#L1-L2`)
    assert(tool, 'fixture read tool has session-relative href')
    await sizes()
    const snap = await native.snapshot()
    const hosts = flatten(snap.tree).filter(n => n.title?.includes('README.md') && n.title?.includes('click'))
    assert.equal(hosts.length,1,'exact native read link title owner')
    const host = hosts[0]!
    const dumps = snap.dump.filter(d => d.visible && d.rect.every((v,i)=>Math.abs(v-(host.rect?.[i] ?? -100))<=1))
    const deepest = dumps.filter(d => !dumps.some(e=>e!==d && e.nth.startsWith(d.nth+'>')))
    assert.equal(deepest.length,1,'exact read link geometry')
    await native.ctl(`click ${deepest[0]!.nth} meta`, 30000)
    await native.ctl('file wait loaded',30000)
    const state = record(await native.ctl('state',30000))
    const opened = (state.file_blocks as {path:string;load:string}[]).find(b=>b.path === `${manifest.root}/README.md`)
    assert(opened && opened.load !== 'opening' && opened.load !== 'error', 'file must finish loading, not just allocate a block')
    await writeFile(join(manifest.proof,'opened-file.json'),JSON.stringify(state.file_blocks))
    // Opening a split changes the app pane's focus: whole-window diagnostic shot is
    // taken by the parent, not passed off as the adapter's original-pane capture.
  }, true)
}
async function answerCopy() {
  await step('completed answer fixture excludes reasoning and tool text',fixtureTurn,true)
  await step('native Copy action emits exact answer-only OSC52 bytes',async()=>{
    await capture('before-copy')
    await tap('Copy answer')
    await sizes()
    const observed = await until(async()=>{
      try { return (await readFile(join(manifest.proof,'clipboard-osc52.jsonl'),'utf8')).trim().split('\n').map(s=>JSON.parse(s) as {hex:string}) }
      catch (error) { if ((error as NodeJS.ErrnoException).code==='ENOENT') return []; throw error }
    }, rows=>rows.length>0, 'actual OSC52 bytes after native Copy action')
    const expected = Buffer.from(`\x1b]52;c;${Buffer.from('E2E visible answer.').toString('base64')}\x07`).toString('hex')
    assert.deepEqual(observed.map(r=>r.hex),[expected])
    await tap('Message','textbox')
    // Invoke the host Paste action, not text injection or clipboard seeding.
    await native.snapshot()
    await native.ctl('plugins run paste',30000)
    await native.snapshot()
    await delay(500)
    const pasted = (await native.rendered()).get('dock.composer.line.input')?.p?.text
    await writeFile(join(manifest.proof,'clipboard-readback.json'),JSON.stringify({pasted,expected:'E2E visible answer.'}))
    if (pasted !== '') assert.equal(pasted,'E2E visible answer.')
    else results.push({name:'host clipboard paste readback',status:'blocked',evidenceClass,reason:'Paste action produced no text. OSC52 is verified; host clipboard roundtrip is not. No claim this is a Hermes defect.'})
  },true)
}
async function todoHud() {
  const todos = Array.from({length:8},(_,i)=>({id:String(i),content:`E2E task ${i}`,status:i<3?'completed':i===3?'in_progress':'pending'}))
  await step('persistent summary from todo.updated replay',async()=>{
    await replay('todo.updated',{revision:1,todos})
    await until(()=>native.rendered(),ns=>[...ns.values()].some(n=>n.p?.role === 'omp.todo.summary' && n.p.text === '3/8 done · now: E2E task 3'),'truthful summary')
  },true)
  await step('expand and collapse through native summary action',async()=>{
    await tap('3/8 done · now: E2E task 3')
    await until(()=>native.rendered(),ns=>[...ns.values()].some(n=>n.k === 'checklist' && n.p?.mode === 'full'),'expanded checklist')
    await sizes()
    await tap('3/8 done · now: E2E task 3')
    await until(()=>native.rendered(),ns=>![...ns.values()].some(n=>n.k === 'checklist'),'collapsed checklist')
  },true)
}
async function shortcuts() {
  const before = await native.configBytes()
  await step('Alt+M opens model picker without changing the model', async()=>{
    await native.shortcut('alt+m')
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.k === 'picker' && n.p?.title === 'Models'), 'model picker from Alt+M')
    await capture('models')
    await native.key('Escape')
    await until(()=>native.rendered(), ns=>![...ns.values()].some(n=>n.k === 'picker'), 'model picker closed')
  })
  await step('Alt+, opens Hermes settings', async()=>{
    await native.shortcut('alt+,')
    await until(()=>native.prefs(), p=>p?.p.title === 'Hermes settings', 'Settings from Alt+,')
    await capture('settings')
    await tap('Close settings', 'button')
    await until(()=>native.prefs(), p=>!p, 'Settings closed')
  })
  await step('F1 opens action-table help', async()=>{
    await native.shortcut('f1')
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.head === 'Commands and shortcuts'), 'help from F1')
    await capture('help')
    await native.key('Escape')
    await until(()=>native.rendered(), ns=>![...ns.values()].some(n=>n.p?.head === 'Commands and shortcuts'), 'help closed')
  })
  await step('Alt+C sends exact read-only /context to real gateway', async()=>{
    await native.shortcut('alt+c')
    const rows = await until(()=>native.wire(), rows=>rows.some(w=>w.dir === 'request' && w.body.method === 'slash.exec'), '/context request')
    const calls = rows.filter(w=>w.dir === 'request' && w.body.method === 'slash.exec')
    assert.equal(calls.length, 1)
    const request = calls[0]!.body
    assert.deepEqual(request.params, {command:'context',session_id:sid})
    const replies = await until(()=>native.wire(), rows=>rows.some(w=>w.dir === 'delivered' && w.body.id === request.id), 'real /context response')
    const reply = replies.find(w=>w.dir === 'delivered' && w.body.id === request.id)!.body
    assert(!reply.error, JSON.stringify(reply))
    assert.equal(typeof record(reply.result).output, 'string')
    await capture('context')
    assert.equal(await native.configBytes(), before)
    assert(!(await native.wire()).some(w=>w.dir === 'denied' || (w.dir === 'request' && ['prompt.submit','config.set','settings.set'].includes(String(w.body.method)))))
  })
}
async function openui() {
  let scope = '', notice: { id:string; path:string; scope:string } | undefined
  await step('read exact current /visual scope from native help', async()=>{
    await command('/visual')
    const nodes = await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.head === 'Visual preview'), 'visual help')
    const text = [...nodes.values()].map(n=>n.p?.text).find(t=>typeof t === 'string' && t.startsWith('["'))
    assert.equal(typeof text, 'string', 'help exposes exact stored-session/branch scope')
    scope = String(text)
    assert.equal(JSON.parse(scope).length, 2)
    await capture('help')
    await native.key('Escape')
    await until(()=>native.rendered(),ns=>![...ns.values()].some(n=>n.p?.head === 'Visual preview'), 'dismissed visual help')
  })
  await step('real locked OpenUI CLI prepares an exact scoped candidate', async()=>{
    const {stdout,stderr} = await promisify(execFile)(process.execPath, [
      join(manifest.root,'ui-tsp/experiments/openui-preview/cli.mjs'), 'prepare',
      join(manifest.root,'ui-tsp/experiments/openui-generation/fixtures/explorer.openui'),
      join(manifest.root,'ui-tsp/experiments/openui-preview/fixtures/repository.json'), scope,
      join(manifest.proof,'openui-bundles'), '--json'
    ], {env:{...process.env,OPENUI_TELEMETRY_DISABLED:'1',DO_NOT_TRACK:'1'},timeout:30000})
    assert.equal(stderr,'')
    notice = JSON.parse(stdout)
    assert(notice && notice.scope === scope && /^[a-f0-9]{64}$/.test(notice.id))
    await writeFile(join(manifest.proof,'openui-candidate.json'),stdout)
  })
  await step('discover real CLI output through explicit completed-tool fixture replay', async()=>{
    assert(notice)
    const output = await readFile(join(manifest.proof,'openui-candidate.json'),'utf8')
    await replay('message.start')
    await replay('tool.start',{name:'terminal',tool_id:'openui-prepare',args:{command:'labelled harness prepare output replay'}})
    await replay('tool.complete',{name:'terminal',tool_id:'openui-prepare',result:{exit_code:0,output}})
    await replay('message.complete',{status:'complete',text:''})
    await until(()=>native.rendered(),ns=>[...ns.values()].some(n=>JSON.stringify(n).includes(notice!.id)), 'completed candidate tool output')
    await command('/visual')
    await until(()=>native.rendered(),ns=>[...ns.values()].some(n=>n.p?.head === 'Recent visual candidates'), 'candidate picker')
    await capture('picker')
    await native.key('Enter')
    await until(()=>native.rendered(),ns=>[...ns.values()].some(n=>n.p?.text === `Bundle: ${notice!.id}`), 'strictly validated selected bundle')
    await capture('selected')
  },true)
  await step('dismiss preview restores composer without submitting a model prompt', async()=>{
    await native.key('Escape')
    await until(()=>native.rendered(),ns=>![...ns.values()].some(n=>n.p?.head === 'Visual preview'), 'preview dismissed')
    await native.type('OpenUI unsent focus probe')
    await until(()=>native.rendered(),ns=>ns.get('dock.composer.line.input')?.p?.text === 'OpenUI unsent focus probe', 'composer focus restored')
    assert(!(await native.wire()).some(w=>w.dir==='request' && w.body.method === 'prompt.submit'))
    await capture('focus')
  })
}

async function smoke() {
  await step('launch welcome and real session without a model call',async()=>{
    assert(flatten((await native.snapshot()).tree).some(n=>(n.text ?? '').toLowerCase().includes('hermes')))
    await sizes()
  })
  await step('type composer draft; never submit prompt',async()=>{
    await native.type('E2E unsent draft')
    await until(()=>native.rendered(),ns=>ns.get('dock.composer.line.input')?.p?.text === 'E2E unsent draft','unsent native draft')
    assert(!(await native.wire()).some(w=>w.dir === 'request' && w.body.method === 'prompt.submit'))
    await capture('unsent-draft')
    for (let i=0;i<'E2E unsent draft'.length;i++) await native.key('Backspace')
    await until(()=>native.rendered(),ns=>ns.get('dock.composer.line.input')?.p?.text === '','cleared draft')
  })
  await step('clean /exit (parent verifies shell and leaked bytes)',async()=>{ await command('/exit') })
}
try {
  await until(()=>native.rendered(),ns=>ns.has('dock.composer.line.input'),'acknowledged frontend')
  const wire = await until(()=>native.wire(), rows=>rows.some(w=>w.dir==='delivered' && w.body.result && typeof w.body.result==='object' && !Array.isArray(w.body.result) && 'session_id' in w.body.result), 'real session creation')
  const ids = new Set(wire.filter(w=>w.dir==='request' && w.body.method==='session.create').map(w=>w.body.id))
  sid = String(record(wire.findLast(w=>w.dir==='delivered' && ids.has(w.body.id) && w.body.result)?.body.result).session_id)
  const journeys:Record<string,()=>Promise<void>> = {settings,'file-links':fileLinks,'answer-copy':answerCopy,'todo-hud':todoHud,shortcuts,smoke,openui}
  assert(journeys[journey],`Unknown journey: ${journey}`)
  await journeys[journey]!()
} catch (error) { console.error(error); process.exitCode=1 }
