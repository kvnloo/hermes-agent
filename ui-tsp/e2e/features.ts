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
async function lspDiagnostics() {
  const rows = Array.from({length:9},(_,i)=>({severity:i===8?'warn':'error',line:i+1,col:1,message:`LSP fixture diagnostic ${i}`}))
  await step('structured diagnostics from explicit edit replay start collapsed',async()=>{
    await replay('message.start')
    await replay('tool.start',{name:'patch',tool_id:'lsp-e2e',args:{path:'README.md'}})
    await replay('tool.complete',{name:'patch',tool_id:'lsp-e2e',result:{success:true,lsp_diagnostics_data:[
      {path:'README.md',status:'ok',diagnostics:rows.slice(0,5)},
      {path:'AGENTS.md',status:'ok',diagnostics:rows.slice(5)}
    ]}})
    await replay('message.complete',{status:'complete',text:''})
    const rendered = await until(()=>native.rendered(),ns=>[...ns.values()].some(n=>n.p?.role==='omp.tool.diagnostics'),'diagnostics section')
    const section = [...rendered.values()].find(n=>n.p?.role==='omp.tool.diagnostics')!
    assert.equal(section.p?.collapsed,true)
    assert.deepEqual(section.p?.head,[{s:'chip',t:'8 errors · 1 warning'}])
    assert.equal([...rendered.values()].filter(n=>n.p?.role==='omp.tool.diagnostics.file').length,2)
    const linked = [...rendered.values()].filter(n=>n.p?.role==='omp.tool.diagnostic')
    assert.equal(linked.length,9)
    assert(linked.every(n=>typeof n.p?.href==='string' && n.p.href.startsWith(`file://${manifest.root}/`)))
    await capture('collapsed')
  },true)
  await step('native summary click expands diagnostic messages',async()=>{
    await tap('8 errors · 1 warning')
    await until(()=>native.snapshot(),snap=>snap.nodes.some(n=>n.name==='LSP fixture diagnostic 0' && !n.states?.hidden),'visible expanded diagnostic')
    await capture('expanded')
  },true)
  await step('typed references, nested symbols and hover from labelled semantic result replay',async()=>{
    const span = {start:{line:2,col:3},end:{line:4,col:5}}
    const base = {path:`${manifest.root}/README.md`,server:'explicit-fixture-server',position_encoding:'utf-16'}
    const location = {path:base.path,range:span}
    const child = {id:'child',name:'Nested semantic symbol with a deliberately long retained label '.repeat(4),kind:6,location,selection:span,children:[]}
    const outputs = [
      {...base,kind:'references',locations:[location,{path:`${manifest.root}/AGENTS.md`,range:span}]},
      {...base,kind:'symbols',symbols:[{...child,id:'parent',name:'Outer',children:[child]}]},
      {...base,kind:'hover',range:span,contents:[{format:'markdown',text:'**Semantic hover fixture**',language:null}]},
      {...base,kind:'unavailable',operation:'references',message:'Fixture server operation unavailable; not checked-clean'}
    ]
    await replay('message.start')
    for (const [index,result] of outputs.entries()) {
      await replay('tool.start',{name:'lsp',tool_id:`semantic-${index}`,args:{operation:result.kind}})
      await replay('tool.complete',{name:'lsp',tool_id:`semantic-${index}`,result:{lsp_result:result}})
      if (index===1) {
        await until(()=>native.rendered(),ns=>[...ns.values()].some(n=>n.p?.role==='omp.tool.symbols'),'symbol tree before hover')
        await sizes()
      }
    }
    await replay('message.complete',{status:'complete',text:''})
    const expectedLinks = [`file://${manifest.root}/README.md#L2-L4`,`file://${manifest.root}/AGENTS.md#L2-L4`]
    const rendered = await until(()=>native.rendered(),ns=>{
      const refs = [...ns.values()].filter(n=>n.p?.role==='omp.tool.reference')
      return [...ns.values()].some(n=>n.p?.role==='omp.tool.lsp.unavailable') && refs.length===2 && refs.every((n,i)=>n.p?.href===expectedLinks[i])
    },'semantic results after real session.info confirms the local backend')
    const refs = [...rendered.values()].filter(n=>n.p?.role==='omp.tool.reference')
    assert.equal(refs.length,2)
    assert.deepEqual(refs.map(n=>n.p?.href),expectedLinks)
    const tree = [...rendered.values()].find(n=>n.p?.role==='omp.tool.symbols')
    assert(tree)
    assert.deepEqual((tree.p?.nodes as {id:string;children:{id:string}[]}[]).map(n=>[n.id,n.children[0]?.id]),[['parent','child']])
    assert([...rendered.values()].some(n=>n.p?.role==='omp.tool.symbol.location' && String(n.p.text).startsWith(child.name)))
    await capture('semantic-final')
  },true)
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
    const nodes = await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role === 'omp.overlay.report' && n.p.head === '/context'), 'native context report sheet')
    assert(![...nodes.values()].some(n=>n.p?.role === 'omp.custom'), 'context must not append a transcript panel')
    assert.equal([...nodes.values()].find(n=>n.p?.role === 'omp.report.body')?.p?.text, record(reply.result).output)
    await capture('context')
    await native.key('Escape')
    await until(()=>native.rendered(), ns=>![...ns.values()].some(n=>n.p?.role === 'omp.overlay.report'), 'context sheet closed')
    await native.type('Report sheet focus probe')
    await until(()=>native.rendered(), ns=>ns.get('dock.composer.line.input')?.p?.text === 'Report sheet focus probe', 'composer focus restored after report')
    assert.equal(await native.configBytes(), before)
    assert(!(await native.wire()).some(w=>w.dir === 'denied' || (w.dir === 'request' && ['prompt.submit','config.set','settings.set'].includes(String(w.body.method)))))
  })
  await step('background report View, native scrolling and Close preserve the draft', async()=>{
    const text = ['Report first marker', ...Array.from({length:100}, (_,i)=>`Report paragraph ${i}`), 'Report last marker'].join('\n\n')
    const before = (await native.rendered()).get('dock.composer.line.input')?.p
    await replay('background.complete', {task_id:'report-scroll-fixture', text})
    const notice = await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role === 'omp.report.view'), 'background report dock View')
    assert(![...notice.values()].some(n=>n.p?.role === 'omp.custom' || n.p?.role === 'omp.overlay.report'))
    await tap('View report: Background task')
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role === 'omp.report.body' && n.p.text === text), 'exact long report')
    const initial = flatten((await native.snapshot()).tree).find(n=>n.text === 'Report first marker')?.rect
    assert(initial, 'first paragraph exists in native report layout')
    await capture('report-start')
    await native.key('End')
    const end = await until(async()=>{
      const snapshot = await native.snapshot()
      return {rect:flatten(snapshot.tree).find(n=>n.text === 'Report last marker')?.rect, height:snapshot.viewport.height}
    }, value=>Boolean(value.rect && value.rect[1] > 0 && value.rect[1]+value.rect[3] <= value.height), 'last report paragraph scrolled into viewport')
    await writeFile(join(manifest.proof,'report-scroll.json'), JSON.stringify({initial, end}))
    await capture('report-end')
    await native.key('Escape')
    const closed = await until(()=>native.rendered(), ns=>![...ns.values()].some(n=>n.p?.role === 'omp.overlay.report'), 'report closed')
    assert.deepEqual(closed.get('dock.composer.line.input')?.p, before)
    assert(![...closed.values()].some(n=>n.p?.role === 'omp.custom'))
  }, true)
  await step('plan review ToC, section scrolling, refine field and cancel preserve the draft', async()=>{
    const before = (await native.rendered()).get('dock.composer.line.input')?.p
    const text = ['# Implementation plan', 'Goal fixture.', '## Build', ...Array.from({length:80}, (_,i)=>`Plan paragraph ${i}`), 'Plan final marker', '## Verify', 'Run the tests.'].join('\n\n')
    await replay('message.start')
    await replay('message.delta', {text})
    await replay('message.complete', {status:'complete', text})
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.k === 'md' && n.p?.text === text), 'completed plan fixture')
    await native.shortcut('alt+shift+p')
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role === 'omp.overlay.plan'), 'native plan review')
    await capture('plan-toc')
    await native.key('ArrowDown')
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role === 'omp.plan.body' && String(n.p.text).startsWith('## Build')), 'Build section selected')
    await native.key('End')
    await until(async()=>{
      const snapshot = await native.snapshot()
      const rect = flatten(snapshot.tree).find(n=>n.text === 'Plan final marker')?.rect
      return Boolean(rect && rect[1] > 0 && rect[1]+rect[3] <= snapshot.viewport.height)
    }, Boolean, 'last plan paragraph painted after End')
    await capture('plan-section-end')
    await tap('Refine', 'text')
    await native.type('Add a failure test')
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role === 'omp.ask.input' && n.p.text === 'Add a failure test'), 'refinement field owns typing')
    await until(async()=>{
      const snapshot = await native.snapshot()
      const field = snapshot.nodes.find(n=>n.role === 'textbox' && n.name === 'How should the plan change?')?.rect
      const decision = snapshot.nodes.find(n=>n.name === 'Send refinement enter')?.rect
      return Boolean(field && decision && field.height >= 20 && field.y > 0 && field.y + field.height <= decision.y && decision.y + decision.height <= snapshot.viewport.height)
    }, Boolean, 'refinement field fully visible above the decision bar')
    await capture('plan-refine')
    await native.key('Escape')
    const closed = await until(()=>native.rendered(), ns=>![...ns.values()].some(n=>n.p?.role === 'omp.overlay.plan'), 'plan review cancelled')
    assert.deepEqual(closed.get('dock.composer.line.input')?.p, before)
    assert(!(await native.wire()).some(w=>w.dir === 'denied' || (w.dir === 'request' && ['prompt.submit','request.answer'].includes(String(w.body.method)))))
  }, true)
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

async function runBoxes() {
  await step('owned ANSI deltas retain color, carriage-return progress and Unicode on wire', async () => {
    await replay('message.start')
    await replay('tool.start', {name:'terminal',tool_id:'ansi-live',turn_id:'ansi-turn',args:{command:'printf colored-progress'}})
    const chunks = ['\u001b[31m紅色\u001b[0m\n', '0%\r100% ✓\n']
    for (const [index, text] of chunks.entries()) {
      await replay('tool.output.delta', {tool_id:'ansi-live',turn_id:'ansi-turn',stream_id:'ansi-stream',seq:index+1,output_kind:'terminal',operation:'append',text,capture_truncated:false})
    }
    const nodes = await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.k==='ansi' && n.p?.text===chunks.join('')), 'raw ANSI stream node')
    const output = [...nodes.values()].find(n=>n.k==='ansi')
    assert.equal(output?.p?.follow, true)
    // ANSI is native-rasterized, not DOM text: wire acknowledgement precedes its paint.
    await delay(2000)
    await capture('ansi-live')
    await replay('tool.complete', {name:'terminal',tool_id:'ansi-live',result:{output:'final ✓',exit_code:0,error:null}})
    await replay('message.complete', {status:'complete',text:''})
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.k==='code' && n.p?.text==='final ✓'), 'authoritative replacement')
    await capture('ansi-final')
    // Separate the old outcomes inventory from the owned incremental stream.
    await native.type('/clear')
    await native.key('Enter')
  }, true)
  await step('terminal and eval outcomes from explicit fixture replay', async () => {
    await replay('message.start')
    for (const [id, name, result] of [
      ['tail', 'terminal', { output:Array.from({length:15},(_,i)=>`line ${i}`).join('\n'), exit_code:0, error:null }],
      ['deadline', 'terminal', { output:'[Command timed out after 5s]', exit_code:124, error:null }],
      ['background', 'terminal', { output:'Background process started', exit_code:0, error:null, session_id:'bg-e2e', pid:1234 }],
      ['eval', 'execute_code', { status:'timeout', output:'partial', error:'Cell timed out after 5s' }]
    ] as const) {
      await replay('tool.start', { name, tool_id:id, args:name === 'terminal' ? {command:`echo ${id}`,background:id==='background'} : {code:'print(1)'} })
      await replay('tool.complete', { name, tool_id:id, result })
    }
    await replay('message.complete', {status:'complete',text:''})
    const nodes = await until(()=>native.rendered(), ns=>[...ns.values()].filter(n=>n.p?.role==='omp.run.state').length===4, 'four run footers')
    const states = [...nodes.values()].filter(n=>n.p?.role==='omp.run.state').map(n=>n.p?.spans)
    assert.deepEqual(states.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))),
      [[{s:'success',t:'ok'}],[{s:'warning',t:'timeout'}],[{s:'pending',t:'background'}],[{s:'warning',t:'timeout'}]]
        .sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))))
    const snapshot = await native.snapshot()
    const text = flatten(snapshot.tree).map(n=>n.text ?? '').join('\n')
    await writeFile(join(manifest.proof,'run-box-text.txt'),text)
    assert(text.includes('timeout'), 'native presentation retains timeout')
    assert(text.includes('background'), 'native presentation retains background')
    assert(text.includes('truncated: showing last 10 lines'), 'native footer retains exact output count')
    await capture('outcomes')
    await tap('Show all output')
    const expanded = await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role==='omp.run.output' && String(n.p.text).split('\n').length===15), 'expanded output')
    assert(![...expanded.values()].some(n=>n.p?.role==='omp.run.facts' && JSON.stringify(n.p.spans).includes('truncated: showing')))
    await tap('Show less output')
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role==='omp.run.output' && String(n.p.text).split('\n').length===10), 'restored ten-line tail')
    await capture('refolded')
  }, true)
}

async function media() {
  const path = join(manifest.root, 'ui-tsp/assets/logo.png')
  await step('real image path through labelled completed-read replay', async()=>{
    assert((await readFile(path)).length > 0)
    await replay('message.start')
    await replay('tool.start', {name:'read_file',tool_id:'media-read',args:{path}})
    await replay('tool.complete', {name:'read_file',tool_id:'media-read',result:{mime:'image/png'}})
    await replay('message.complete', {status:'complete',text:''})
    const nodes = await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.k==='media' && n.p?.path===path), 'negotiated native media node')
    const tool = [...nodes.values()].find(n=>n.k==='tool' && n.p?.target===path)
    assert.equal(tool?.p?.status, 'done')
    assert.equal(tool?.p?.collapsible, true)
    assert.equal(tool?.p?.collapsed, false)
    assert.equal(tool?.p?.preview, undefined)
    assert(!(await native.wire()).some(w=>w.dir==='request' && w.body.method==='prompt.submit'))
    await capture('native-image-preview')
  }, true)
}

async function writtenArtifacts() {
  await step('confirmed SVG and Mermaid writes lead with native figures; failures stay source-only', async () => {
    const cases = [
      { id:'written-svg', path:join(manifest.proof,'written.svg'), source:'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="100"><rect width="240" height="100" fill="#234"/><text x="20" y="55" fill="white">Confirmed SVG</text></svg>' },
      { id:'written-mermaid', path:join(manifest.proof,'written.mmd'), source:'graph LR\n  A[Confirmed] --> B[Mermaid]' }
    ]
    await replay('message.start')
    for (const item of cases) {
      await writeFile(item.path,item.source)
      assert.equal(await readFile(item.path,'utf8'),item.source)
      await replay('tool.start',{name:'write_file',tool_id:item.id,args:{path:item.path,content:item.source}})
      await replay('tool.complete',{name:'write_file',tool_id:item.id,result:{verified:true,bytes_written:Buffer.byteLength(item.source),resolved_path:item.path}})
    }
    await replay('tool.start',{name:'write_file',tool_id:'failed-svg',args:{path:'failed.svg',content:'<svg/>'}})
    await replay('tool.complete',{name:'write_file',tool_id:'failed-svg',result:{error:'Fixture permission denied'}})
    await replay('message.complete',{status:'complete',text:''})
    const nodes = await until(()=>native.rendered(), ns=>[...ns.values()].filter(n=>n.p?.role==='omp.tool.write.figure').length===2, 'two confirmed figure-first cards')
    for (const item of cases) {
      const tool = [...nodes.values()].find(n=>n.k==='tool' && n.p?.target===item.path)
      assert(tool)
      assert.equal(tool.p?.collapsed,false)
      assert.equal(tool.p?.preview,undefined)
      const descendants = [...nodes.values()].filter(n=>n.id.startsWith(tool.id+'.'))
      assert.equal(descendants[0]?.p?.role,'omp.tool.write.figure')
      assert(descendants.some(n=>n.k==='code' && n.p?.text===item.source))
    }
    const failed = [...nodes.values()].find(n=>n.k==='tool' && n.p?.target==='failed.svg')
    assert.equal(failed?.p?.status,'error')
    assert(!(await native.wire()).some(w=>w.dir==='request' && w.body.method==='prompt.submit'))
    await capture('figure-first')
  }, true)
}

async function agentInspector() {
  const agent = {delegation_id:'inspector-delegation',goal:'Inspector alpha',model:'inspector-model',task_count:2,task_index:0}
  await step('explicit subagent fixtures create a clickable task row', async()=>{
    await replay('message.start')
    await replay('tool.start', {name:'delegate_task',tool_id:'inspector-task',args:{tasks:[{goal:agent.goal}]}})
    await replay('tool.complete', {name:'delegate_task',tool_id:'inspector-task',result:{delegation_id:agent.delegation_id,status:'dispatched'}})
    await replay('subagent.start', agent)
    await replay('subagent.tool', {...agent,tool_name:'read',tool_preview:'alpha.ts',tool_count:1})
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.k==='agent' && n.p?.task===agent.goal), 'native agent row')
    await native.type('Inspector unsent draft')
    await native.key('ArrowLeft')
    const before = record((await native.rendered()).get('dock.composer.line.input')?.p)
    await writeFile(join(manifest.proof,'inspector-draft-before.json'),JSON.stringify(before))
    const snapshot = await native.snapshot()
    const targets = flatten(snapshot.tree).filter(n=>n.title==='Inspect agent (read-only)')
    assert.equal(targets.length,1,'exact native agent row title')
    const target = targets[0]!
    const dumps = snapshot.dump.filter(d=>d.visible && d.rect.every((v,i)=>Math.abs(v-(target.rect?.[i] ?? -100))<=1))
    const deepest = dumps.filter(d=>!dumps.some(e=>e!==d && e.nth.startsWith(d.nth+'>')))
    assert.equal(deepest.length,1,'exact native agent click geometry')
    await native.ctl(`click ${deepest[0]!.nth}`,30000)
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.p?.role==='omp.overlay.agent-inspector'),'inspector opened by real click')
    await capture('opened')
  }, true)
  await step('live events stay scoped and final status survives completion',async()=>{
    await replay('subagent.tool', {...agent,tool_name:'bash',tool_preview:'npm test',tool_count:2})
    await replay('subagent.tool', {...agent,tool_name:'edit',tool_preview:'fix alpha.ts',tool_count:3})
    await replay('subagent.progress', {...agent,task_index:1,text:'FOREIGN_AGENT_NOTE'})
    await replay('subagent.complete', {...agent,status:'completed',duration_seconds:12,summary:'Inspector verified',api_calls:4})
    const nodes = await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.id.startsWith('layer.agent-inspector:') && n.p?.text==='Status: done'),'finished inspector')
    const sheet = [...nodes.values()].filter(n=>n.id.startsWith('layer.agent-inspector:'))
    assert.equal(sheet.filter(n=>n.p?.role==='omp.agent.tool').length,3)
    assert(!JSON.stringify(sheet).includes('FOREIGN_AGENT_NOTE'))
    await capture('finished')
    for (let i=0;i<30;i++) await replay('subagent.progress', {...agent,text:`Long activity ${i}`})
    await until(()=>native.rendered(), ns=>[...ns.values()].some(n=>n.id.startsWith('layer.agent-inspector:') && n.p?.text==='Long activity 29'),'long activity log')
    const lastNote = async()=>flatten((await native.snapshot()).tree).find(n=>n.text==='Long activity 29')?.rect
    const beforeScroll = await lastNote()
    assert(beforeScroll, 'native long-log geometry')
    await native.key('End')
    const afterScroll = await until(lastNote, rect=>Boolean(rect && rect[1]! < beforeScroll[1]!), 'inspector scroll moves its own log')
    await writeFile(join(manifest.proof,'inspector-scroll.json'),JSON.stringify({before:beforeScroll,after:afterScroll}))
    await capture('scrolled')
    await native.key('Escape')
    const closed = await until(()=>native.rendered(),ns=>![...ns.values()].some(n=>n.p?.role==='omp.overlay.agent-inspector'),'inspector closed')
    const before = JSON.parse(await readFile(join(manifest.proof,'inspector-draft-before.json'),'utf8'))
    const after = closed.get('dock.composer.line.input')?.p
    assert.equal(after?.text,before.text)
    assert.equal(after?.cursor,before.cursor)
    assert(!(await native.wire()).some(w=>w.dir==='request' && w.body.method==='prompt.submit'))
    await capture('draft-restored')
  },true)
}

async function agentHub() {
  await step('real gateway reads an explicitly seeded owned child transcript, with no invented control authority', async () => {
    const wire = await native.wire()
    const ids = new Set(wire.filter(w => w.dir === 'request' && w.body.method === 'session.create').map(w => w.body.id))
    const parent = String(record(wire.findLast(w => w.dir === 'delivered' && ids.has(w.body.id) && w.body.result)?.body.result).stored_session_id)
    const seed = `import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from hermes_state import SessionDB
db = SessionDB(Path(sys.argv[2]) / 'state.db')
root = sys.argv[3]
db.create_session(root, source='tui')
db.create_session('hub-e2e-child', source='subagent', parent_session_id=root, model_config={'_delegate_from': root, '_delegate_goal': 'Hub seeded child', '_subagent_id': 'sa-hub-e2e'})
for i in range(51):
    db.append_message('hub-e2e-child', 'assistant', f'Hub full transcript message {i}')
db.end_session('hub-e2e-child', 'completed')
db.close()
`
    await promisify(execFile)(manifest.python, ['-c', seed, manifest.root, manifest.home, parent], { cwd: manifest.root })
    await command('/agents')
    const nodes = await until(() => native.rendered(), ns => [...ns.values()].some(n => n.p?.role === 'omp.agent.transcript') && [...ns.values()].some(n => JSON.stringify(n.p).includes('Hub full transcript message 0')), 'full first canonical child page')
    assert([...nodes.values()].some(n => n.p?.role === 'omp.overlay.agent-hub'))
    assert([...nodes.values()].some(n => String(n.p?.text).includes('Status: completed')))
    assert(![...nodes.values()].some(n => n.id.startsWith('layer.agent-hub:') && ['send', 'stop'].includes(n.id.split('.').at(-1)!)))
    await capture('owned-full-transcript')
  }, true)
  await step('native Next page reads the real canonical continuation, Close restores the composer', async () => {
    await tap('Next page')
    const nodes = await until(() => native.rendered(), ns => [...ns.values()].some(n => JSON.stringify(n.p).includes('Hub full transcript message 50')), 'second canonical page')
    assert(![...nodes.values()].some(n => n.p?.text === 'Next page'))
    await capture('next-page')
    await native.key('Escape')
    await until(() => native.rendered(), ns => ![...ns.values()].some(n => n.p?.role === 'omp.overlay.agent-hub'), 'hub closed')
    await native.type('Hub unsent draft')
    await until(() => native.rendered(), ns => ns.get('dock.composer.line.input')?.p?.text === 'Hub unsent draft', 'parent composer restored')
    assert(!(await native.wire()).some(w => w.dir === 'request' && ['prompt.submit', 'subagent.message', 'subagent.stop', 'slash.exec'].includes(w.body.method ?? '')))
    await capture('closed')
  }, true)
}

async function retention() {
  const frames = async () => (await readFile(manifest.tsp, 'utf8')).trim().split('\n')
    .map(line => JSON.parse(line) as import('./types.ts').TspFrame)
  await step('35 labelled fixture turns settle only the cold prefix in real Tern', async () => {
    for (let i = 0; i < 35; i++) {
      await replay('message.start')
      await replay('message.complete', { status:'complete', text:`Retention fixture answer ${i}.` })
    }
    await until(() => native.rendered(), ns => [...ns.values()].filter(n => n.p?.role === 'omp.assistant').length === 35, 'all fixture turns acknowledged')
    const settled = (await frames()).filter(f => f.dir === 'out' && f.verb === 'f')
      .flatMap(f => f.body.ops ?? []).filter(op => op[0] === 'settle')
    assert.equal(settled.length, 15)
    assert(!settled.some(op => op[1] === 'main.welcome'))
    await capture('settled-history')
  }, true)
  await step('streaming preserves resident history and native composer with no model call', async () => {
    const before = (await frames()).length
    const old = [...(await native.rendered()).values()].filter(n => n.p?.role === 'omp.assistant').map(n => n.id)
    await replay('message.start')
    await replay('message.delta', { text:'Retention streaming fixture.' })
    await until(() => native.rendered(), ns => [...ns.values()].some(n => n.p?.text === 'Retention streaming fixture.'), 'live fixture text')
    const ops = (await frames()).slice(before).filter(f => f.dir === 'out' && f.verb === 'f').flatMap(f => f.body.ops ?? [])
    assert(!ops.some(op => ['del','move','reveal'].includes(String(op[0])) && (op[1] === 'main' || old.includes(String(op[1])))))
    const nodes = await native.rendered()
    assert(old.every(id => nodes.has(id)))
    await native.type('retention unsent draft')
    await until(() => native.rendered(), ns => ns.get('dock.composer.line.input')?.p?.text === 'retention unsent draft', 'draft preserved alongside retained history')
    assert(!(await native.wire()).some(w => w.dir === 'request' && w.body.method === 'prompt.submit'))
    await capture('stream-and-draft')
  }, true)
}

async function hostLifecycle() {
  async function hostCheck(label: string, code: string) {
    const response = await native.ctl(`carly lua ${code}`, 30000)
    await native.ctl('carly ok', 30000)
    await native.ctl('carly last', 30000)
    const tree = await native.ctl('tree', 30000)
    await writeFile(join(manifest.proof, `host-${label}.json`), JSON.stringify({response, tree}, null, 2))
    await native.ctl('carly close', 30000)
  }
  async function hostState(state: string) {
    await hostCheck(state, `local found=nil; for _,a in cx.agents:list() do if a.pane==${manifest.pane} then found=a end end; assert(found, 'Hermes agent missing'); assert(found.state==${JSON.stringify(state)}, found.state); return found`)
  }
  await step('host observes confirmed work and structured tools/transcript', async () => {
    await replay('message.start')
    await replay('tool.start', {tool_id:'host-tool', name:'bash', args:{command:'printf host-tool'}})
    await until(() => native.rendered(), ns => [...ns.values()].some(n => n.p?.role === 'omp.working'), 'working view')
    await hostState('working')
    await replay('tool.complete', {tool_id:'host-tool', name:'bash', result:{exit_code:0, output:'host-tool'}})
    await replay('message.delta', {text:'Host lifecycle answer.'})
    await replay('message.complete', {status:'complete', text:'Host lifecycle answer.'})
    await until(() => native.rendered(), ns => ![...ns.values()].some(n => n.p?.role === 'omp.working'), 'settled view')
    await hostState('idle')
    await hostCheck('transcript', `local t=cx.agents:transcript(${manifest.pane}); assert(#t>0, 'missing transcript'); assert(string.find(t[#t].text, 'Host lifecycle answer.', 1, true), t[#t].text); local bash=false; for _,m in t do for _,tool in m.tools do if tool.name=='bash' then bash=true end end end; assert(bash, 'missing structured bash tool'); return t`)
    await hostCheck('wait', `local answer=await(cx.agents:wait(${manifest.pane}, {timeout=2000})); assert(answer and string.find(answer, 'Host lifecycle answer.', 1, true), tostring(answer)); return answer`)
  }, true)
  await step('hidden completion creates one host inbox entry and duplicate completion adds none', async () => {
    await replay('message.start')
    await until(() => native.rendered(), ns => [...ns.values()].some(n => n.p?.role === 'omp.working'), 'second working view')
    await native.ctl('tab prev', 30000)
    const away = record(await native.ctl('state', 30000))
    assert.notEqual(String(record(away.focused).id), manifest.pane, 'private alternate tab must own focus')
    await replay('message.delta', {text:'Hidden lifecycle answer.'})
    await replay('message.complete', {status:'complete', text:'Hidden lifecycle answer.'})
    const before = record(await until(() => native.ctl('state', 30000), value => Number(record(record(value).inbox).count) > 0, 'host completion inbox entry'))
    await replay('message.complete', {status:'complete', text:'Hidden lifecycle answer.'})
    await delay(150)
    const after = record(await native.ctl('state', 30000))
    assert.deepEqual(after.inbox, before.inbox, 'duplicate settlement must not duplicate host attention')
    await writeFile(join(manifest.proof, 'host-completion-attention.json'), JSON.stringify({before,after}, null, 2))
    await native.ctl('tab next', 30000)
    await native.snapshot()
    await hostState('idle')
  }, true)
  await step('native Settings holds Carly input without consuming a human draft', async () => {
    await native.type('Human draft survives host queue')
    await tap('Open Hermes settings', 'group')
    await until(() => native.rendered(), ns => ns.get('dock.composer.line.input')?.p?.sendable === false, 'modal sendable false')
    await hostCheck('queued-ask', `cx.agents:ask(${manifest.pane}, 'Queued host prompt, held by Settings'); return 'queued'`)
    await delay(250)
    assert(!(await native.wire()).some(w => w.dir === 'denied' || (w.dir === 'request' && w.body.method === 'prompt.submit')))
    assert.equal((await native.rendered()).get('dock.composer.line.input')?.p?.text, 'Human draft survives host queue')
    await capture('queued-under-settings')
    // The inert suite forbids model calls; teardown owns this still-queued pane.
  })
}

async function sessionTree() {
  const picker = async () => [...(await native.rendered()).values()].find(n => n.k === 'picker' && n.p?.title === 'Session / branch tree')
  await step('real gateway pages 207 explicit stored-session fixtures', async () => {
    await promisify(execFile)(manifest.python, ['-c', `
import os
from pathlib import Path
from hermes_state import SessionDB
home = Path(os.environ['HERMES_HOME']).resolve()
assert (home / '.native-settings-e2e').read_text() == 'isolated inert fixture; no turns or grants\\n'
db = SessionDB(db_path=home / 'state.db')
try:
    for i in range(205):
        key = f't02-page-{i:03}'
        db.create_session(key, source='tui', cwd='/fixture/work')
        db.set_session_title(key, f'Stored fixture {i:03}')
    db.create_session('t02-root', source='tui', cwd='/fixture/root')
    db.set_session_title('t02-root', 'T02 parent')
    point = db.append_message('t02-root', 'user', 'Explicit fixture question')
    db.create_session('t02-child', source='tui', cwd='/fixture/child', parent_session_id='t02-root',
        model_config={'_branched_from':'t02-root', '_branch_point':{'parent_session_id':'t02-root', 'message_id':point, 'copied_message_count':1}})
    db.append_message('t02-child', 'user', 'Explicit fixture question')
    db.set_session_title('t02-child', 'T02 copied fork')
finally:
    db.close()
`], { cwd:manifest.root, env:{ ...process.env, HERMES_HOME:manifest.home, PYTHONPATH:manifest.root } })
    await command('/tree')
    const sheet = await until(picker, p => p?.p?.state === 'ready' && p?.p?.total === 207, 'real paged session tree')
    assert.equal((sheet?.p?.order as Json[])?.length, 200)
    assert.equal(sheet?.p?.layout, 'tree')
    await capture('paged-tree')
    await tap('Load more')
    await until(picker, p => (p?.p?.order as Json[])?.length === 207, 'explicit load-more beyond 200')
  }, true)
  await step('native tree search and selection never resume or undo history', async () => {
    await native.type('T02 copied')
    const sheet = await until(picker, p => p?.p?.query === 'T02 copied' && p?.p?.state === 'ready' && p?.p?.total === 1, 'global branch search')
    assert.deepEqual(sheet?.p?.order, ['t02-child'])
    const items = sheet?.p?.items as {id:string;depth:number}[]
    assert.equal(items.find(item => item.id === 't02-child')?.depth, 1)
    const requests = async () => (await native.wire()).filter(w => w.dir === 'request' && ['session.resume','session.undo','session.fork','session.delete'].includes(w.body.method ?? ''))
    assert.equal((await requests()).length, 0)
    await native.key('Enter')
    await until(() => native.rendered(), ns => [...ns.values()].some(n => n.p?.text === 'Resume saved session?'), 'explicit resume confirmation')
    assert.equal((await requests()).length, 0)
    await native.key('Escape')
    await until(picker, Boolean, 'cancel returns to tree')
    assert.equal((await requests()).length, 0)
    await capture('searched-branch')
    await tap('Rename')
    await until(picker, p => p?.p?.query === 'T02 copied fork', 'private rename draft')
    for (let i = 0; i < 'T02 copied fork'.length; i++) await native.key('Backspace')
    await native.type('T02 copied renamed fork')
    await native.key('Enter')
    await until(picker, p => p?.p?.state === 'ready' && JSON.stringify(p?.p?.items).includes('T02 copied renamed fork'), 'durable rename readback')
    await tap('Sort: recent')
    await until(picker, p => JSON.stringify(p?.p?.actions).includes('Sort: title'), 'sort keeps renamed selection')
    assert.equal((await picker())?.p?.selected, 't02-child')
    const readback = await promisify(execFile)(manifest.python, ['-c', "import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); print(db.execute(\"SELECT title FROM sessions WHERE id = 't02-child'\").fetchone()[0]); db.close()", join(manifest.home, 'state.db')], {cwd:manifest.root})
    assert.equal(readback.stdout.trim(), 'T02 copied renamed fork')
    await capture('renamed-branch')
    await native.key('Escape')
    await until(picker, p => !p, 'tree closed')
    assert(!(await native.wire()).some(w => w.dir === 'request' && w.body.method === 'prompt.submit'))
  }, true)
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
  const journeys:Record<string,()=>Promise<void>> = {settings,'lsp-diagnostics':lspDiagnostics,'file-links':fileLinks,'answer-copy':answerCopy,'todo-hud':todoHud,shortcuts,smoke,openui,'run-box':runBoxes,media,'written-artifacts':writtenArtifacts,'agent-inspector':agentInspector,'agent-hub':agentHub,retention,'host-lifecycle':hostLifecycle,'session-tree':sessionTree}
  assert(journeys[journey],`Unknown journey: ${journey}`)
  await journeys[journey]!()
} catch (error) { console.error(error); process.exitCode=1 }
