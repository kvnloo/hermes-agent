#!/usr/bin/env python3
"""Rendered dock geometry + real App dispatch, presentation fixtures, isolated serve."""
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
lane = r.out/'tern-serve-dock-prompts'
checks = []
measurements = []

def flat(items):
    return [n for item in items for n in [item, *flat(item.get('children', []))]]

def check(name, passed, **details):
    checks.append(dict(name=name, passed=bool(passed), **details))

def capture(label):
    time.sleep(.5)  # Native raster commits after the semantic tree; ctl wait alone is insufficient.
    tree = r.ctl(lane, 'tree')
    (lane/f'{label}.tree.json').write_text(json.dumps(tree, indent=2))
    (lane/f'{label}.dump.json').write_text(json.dumps(r.ctl(lane, 'dump'), indent=2))
    ax = r.ctl(lane, 'a11y')
    (lane/f'{label}.a11y.json').write_text(json.dumps(ax, indent=2))
    lists = [n for n in flat([ax]) if n.get('role') == 'ListBox']
    if label.startswith(('clarify-', 'dictation-')):
        check(label+': accessible question-associated list', any(n.get('name') == 'Answer choices: Which deployment target should receive this release?' for n in lists))
    for listing in lists:
        selected = [n for n in flat([listing]) if n.get('role') == 'ListBoxOption' and 'selected' in n.get('states', [])]
        _, y, _, h = listing['bounds']
        # AX option bounds include the native one-pixel selection border.
        check(label+': selected option fully inside scrollport', bool(selected) and all(n['bounds'][1] >= y-1.1 and n['bounds'][1]+n['bounds'][3] <= y+h+1.1 for n in selected), selected=selected, viewport=listing['bounds'])
    r.ctl(lane, 'shot '+label)
    return flat(tree['tree'])

def resize(cols, rows):
    width, height = cols*9+24, rows*20+90
    for _ in range(60):
        r.ctl(lane, f'resize {width} {height}')
        time.sleep(.05)
        state = r.ctl(lane, 'state')
        pane = next(p for p in state['panes'] if p['id'] == state['focused']['id'])
        dc, dr = cols-pane['cols'], rows-pane['rows']
        if dc == dr == 0:
            measurements.append(dict(target=[cols, rows], actual=pane, viewport=[width, height]))
            return height
        if dc: width += dc*9 if abs(dc)>1 else (1 if dc>0 else -1)
        if dr: height += dr*20 if abs(dr)>1 else (1 if dr>0 else -1)
    raise AssertionError(pane)

def visible(n, height):
    x,y,w,h = n['rect']
    return y >= 40 and y+h <= height and h > 0 and w > 0

result = dict(status='fail', baseline=a.baseline, checks=checks, measurements=measurements,
              evidenceClass='tern-serve+presentation-fixture; fake recorder, no hardware/model')
try:
    r.command([r.node, r.root/'ui-tsp/e2e/dock-prompts.build.mjs', *(['--baseline'] if a.baseline else [])], r.root, r.base_env, r.out/'build.log')
    assert gate_open(r.isolation(lane, 'tern-serve'))
    home = lane/'proof/hermes-home'
    home.mkdir(parents=True)
    mode = lane/'mode.txt'; mode.write_text('approval')
    log = lane/'fixture.jsonl'
    command = f"HERMES_HOME={shlex_quote(str(home))} HERMES_TUI_SPLASH=0 {shlex_quote(r.node)} {shlex_quote(str(r.root/'ui-tsp/dist/dock-prompts.fixture.js'))} {shlex_quote(str(mode))} {shlex_quote(str(log))}"
    r.ctl(lane, 'run '+json.dumps(command), True)
    r.ctl(lane, 'plugins expect DOCK_PROMPTS_FIXTURE')
    r.ctl(lane, 'font 15', True)
    for scenario in ['approval', 'clarify', 'dictation']:
        mode.write_text(scenario)
        time.sleep(.5)
        for cols,rows in [(80,28),(100,30),(160,44)]:
            height = resize(cols,rows)
            label = f'{scenario}-{cols}x{rows}'
            nodes = capture(label)
            if scenario == 'approval':
                command = [n for n in nodes if 'sf-code' in n.get('class','').split()]
                check(label+': full command stays in viewport', bool(command) and all(visible(n,height) for n in command), nodes=command)
                reason = [n for n in nodes if 'Recursive removal' in n.get('text','')]
                check(label+': warning stays in viewport', bool(reason) and all(visible(n,height) for n in reason), nodes=reason)
            else:
                question = [n for n in nodes if n.get('text') == 'Which deployment target should receive this release?']
                check(label+': question stays in viewport', bool(question) and all(visible(n,height) for n in question), nodes=question)
                check(label+': no approval denial hint', not any('Enter deny and steer' in n.get('text','') for n in nodes))
            vim = [n for n in nodes if n.get('text') in ['INSERT','NORMAL']]
            check(label+': Vim mode is atomic', bool(vim) and all(n['rect'][3] <= 24 for n in vim), nodes=vim)
            if scenario in ['approval', 'clarify']:
                r.ctl(lane, 'key up', True)
                last = capture(label+'-last')
                pinned = ([n for n in last if 'sf-code' in n.get('class','').split()] if scenario == 'approval' else
                          [n for n in last if n.get('text') == 'Which deployment target should receive this release?'])
                check(label+': command/question pinned while options scroll', bool(pinned) and all(visible(n,height) for n in pinned))
                r.ctl(lane, 'key down', True)
        if scenario == 'dictation':
            r.ctl(lane, 'key escape', True)
            capture('dictation-first-escape')
            events = [json.loads(line) for line in log.read_text().splitlines()]
            stops = [e for e in events if e.get('method') == 'voice.dictate.stop' and e['params']['cancel'] is True]
            answers = [e for e in events if e.get('answer') == 'dictation']
            check('first Esc cancels capture before answering clarification', bool(stops) and not answers, events=events)
    mode.write_text('vim')
    time.sleep(.3)
    r.ctl(lane, 'key escape', True)
    for cols,rows in [(80,28),(100,30),(160,44)]:
        resize(cols,rows)
        nodes = capture(f'vim-normal-{cols}x{rows}')
        modes = [n for n in nodes if n.get('text') == 'NORMAL']
        check(f'{cols}: NORMAL mode is atomic', bool(modes) and all(n['rect'][3] <= 24 for n in modes))
    failed = [c['name'] for c in checks if not c['passed']]
    result.update(failed=failed, status='expected-red' if a.baseline and failed else 'fail' if failed else 'pass')
finally:
    if (lane/'isolation.json').exists():
        shots = Path(json.loads((lane/'isolation.json').read_text())['shots'])
        if shots.exists(): shutil.copytree(shots, lane/'shots', dirs_exist_ok=True)
    if hasattr(r,'children'): r.stop(lane)
    (r.out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(receipt=str(r.out),status=result['status'],failed=result.get('failed',[])),indent=2))
if not a.baseline: assert result['status'] == 'pass', result.get('failed')
