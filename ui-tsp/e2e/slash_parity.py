#!/usr/bin/env python3
"""Real App dispatch/render regression, deterministic gateway fixtures, isolated tern serve."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace
from lane import Runner, gate_open, shlex_quote

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('worktree', type=Path)
p.add_argument('--receipts', type=Path, required=True)
p.add_argument('--baseline', action='store_true')
a = p.parse_args()
r = Runner(SimpleNamespace(worktree=a.worktree, receipts=a.receipts, node=Path(shutil.which('node')), python=Path(sys.executable)))
lane = r.out/'tern-serve-slash-parity'
result = dict(evidenceClass='tern-serve+deterministic-gateway-fixture', baseline=a.baseline, captures=[], checks=[])
def flat(items):
    return [n for item in items for n in [item, *flat(item.get('children', []))]]
def capture(label):
    tree = r.ctl(lane, 'tree')
    (lane/f'{label}.tree.json').write_text(json.dumps(tree, indent=2))
    shot = r.ctl(lane, 'shot '+label)
    result['captures'].append(dict(label=label, shot=shot))
    return flat(tree['tree'])
def check(name, passed):
    result['checks'].append(dict(name=name, passed=bool(passed)))
def command(text):
    mode.write_text(text)
    time.sleep(.55)
    r.ctl(lane, 'wait 200')
try:
    r.command([r.node, r.root/'ui-tsp/e2e/slash-parity.build.mjs'], r.root, r.base_env, r.out/'build.log')
    assert gate_open(r.isolation(lane, 'tern-serve'))
    mode = lane/'command.txt'
    mode.write_text('')
    home = lane/'proof/hermes-home'
    home.mkdir(parents=True)
    launch = f'HERMES_HOME={shlex_quote(str(home))} HERMES_TUI_SPLASH=0 {shlex_quote(r.node)} {shlex_quote(str(r.root/"ui-tsp/dist/slash-parity.fixture.js"))} {shlex_quote(str(mode))}'
    r.ctl(lane, 'run '+json.dumps(launch), True)
    r.ctl(lane, 'plugins expect SLASH_FIXTURE_READY')
    r.ctl(lane, 'font 15', True)
    for cols, rows in [(80,28),(100,30),(160,44)]:
        width, height = cols*9+24, rows*20+100
        for _ in range(70):
            r.ctl(lane, f'resize {width} {height}')
            time.sleep(.08)
            state = r.ctl(lane, 'state')
            pane = next(p for p in state['panes'] if p['id']==state['focused']['id'])
            if (pane['cols'],pane['rows'])==(cols,rows): break
            dc,dr = cols-pane['cols'],rows-pane['rows']
            if dc: width += dc*9 if abs(dc)>1 else (1 if dc>0 else -1)
            if dr: height += dr*20 if abs(dr)>1 else (1 if dr>0 else -1)
        assert (pane['cols'],pane['rows'])==(cols,rows), pane
        result.setdefault('geometry',[]).append(pane)
        for name in ['skills','usage','context','mcp list','complete:/jobs','complete:/editor']:
            command(name if name.startswith('complete:') else '/'+name)
            label=f'{cols}x{rows}-'+name.replace(' ','-').replace(':/','-')
            nodes=capture(label)
            texts=[n.get('text','') for n in nodes]
            if name=='mcp list':
                check(label+': literal qualifier', any('values withheld' in t and '(' in t and ')' in t for t in texts))
            if name.startswith('complete:'):
                check(label+': exact completion', any(name.split('/')[-1]==t or t.startswith(name.split('/')[-1]+' ') for t in texts))
            if name in ['usage','context','skills']:
                check(label+': plain preformatted rendering', any('sf-t-mono' in n.get('class','').split() and n['rect'][3] >= (120 if name != 'context' else 60) for n in nodes))
        command('/clear')
        capture(f'{cols}x{rows}-clear')
        command('/context')
        nodes=capture(f'{cols}x{rows}-context-after-clear')
        check(f'{cols}: clear creates empty session', any('Conversation is empty' in n.get('text','') for n in nodes))
    command('complete:/q')
    capture('q-completion-before')
    command('/q list')
    nodes=capture('q-list-after')
    check('q list does not quit', any('No queued prompts.' in n.get('text','') for n in nodes))
finally:
    if (lane/'isolation.json').exists():
        shots=Path(json.loads((lane/'isolation.json').read_text())['shots'])
        if shots.exists(): shutil.copytree(shots,lane/'shots',dirs_exist_ok=True)
    if hasattr(r,'children'): r.stop(lane)
    result['status']='expected-red' if a.baseline else 'pass' if all(c['passed'] for c in result['checks']) else 'fail'
    (r.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(r.out),**result),indent=2))
if not a.baseline: assert result['status']=='pass'
