#!/usr/bin/env python3
"""F3 real-render receipts; deterministic fixture, isolated tern serve only."""
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
node_command = shutil.which('node')
assert node_command is not None
node = Path(node_command).absolute()
r = Runner(SimpleNamespace(worktree=a.worktree, receipts=a.receipts, node=node, python=Path(sys.executable)))
lane = r.out/'tern-serve-f3'
checks = []

def flat(items):
    return [n for item in items for n in [item, *flat(item.get('children', []))]]

def tree():
    return flat(r.ctl(lane, 'tree')['tree'])

def capture(label):
    time.sleep(.5)  # external PTY commits are asynchronous to ctl wait
    nodes = tree()
    (lane/f'{label}.tree.json').write_text(json.dumps(nodes, indent=2))
    (lane/f'{label}.a11y.json').write_text(json.dumps(r.ctl(lane, 'a11y'), indent=2))
    r.ctl(lane, 'shot '+label)
    return nodes

def click(label):
    nodes = tree()
    n = next(n for n in nodes if n.get('text') == label and n['rect'][2] > 0)
    x,y,w,h = n['rect']
    r.ctl(lane, f'click {x+w/2} {y+h/2}', True)
    time.sleep(.3)

def mode(value):
    modefile.write_text(value)
    time.sleep(.6)

def check(name, ok, **details):
    checks.append(dict(name=name, passed=bool(ok), **details))

try:
    r.command([node, r.root/'ui-tsp/e2e/f3.build.mjs', *(['--baseline'] if a.baseline else [])], r.root, r.base_env, r.out/'build.log')
    assert gate_open(r.isolation(lane, 'tern-serve'))
    home = lane/'proof/hermes-home'
    home.mkdir(parents=True)
    modefile = lane/'mode.txt'
    modefile.write_text('idle')
    cmd = f'HERMES_HOME={shlex_quote(str(home))} HERMES_TUI_SPLASH=0 {shlex_quote(str(node))} {shlex_quote(str(r.root/"ui-tsp/dist/f3.fixture.js"))} {shlex_quote(str(modefile))}'
    r.ctl(lane, 'run '+json.dumps(cmd), True)
    r.ctl(lane, 'plugins expect F3_VISIBLE_ANSWER')
    r.ctl(lane, 'font 15', True)
    for cols,rows in [(80,28),(100,30),(160,44)]:
        width,height = cols*9+24,rows*19+100
        for _ in range(70):
            r.ctl(lane, f'resize {width} {height}')
            time.sleep(.1)
            state = r.ctl(lane, 'state')
            pane = next(p for p in state['panes'] if p['id'] == state['focused']['id'])
            dc,dr = cols-pane['cols'],rows-pane['rows']
            if not dc and not dr: break
            width += dc*8 if abs(dc)>1 else dc
            height += dr*17 if abs(dr)>1 else dr
        assert (pane['cols'],pane['rows']) == (cols,rows), pane
        label = f'{cols}x{rows}'
        mode('help')
        before = capture(label+'-help-start')
        r.ctl(lane, 'key end', True)
        after = capture(label+'-help-end')
        marker_before = next(n['rect'][1] for n in before if n.get('text') == 'Final commands')
        marker_after = next(n['rect'][1] for n in after if n.get('text') == 'Final commands')
        check(label+': help end scrolls to last command', marker_after < marker_before and marker_after < height-30, before=marker_before, after=marker_after)
        mode('plan')
        click('Edit plan')
        nodes = capture(label+'-plan-edit')
        editor = next((n for n in nodes if 'sf-editor' in n.get('class','').split() and 'focused' in n.get('class','').split()), None)
        check(label+': multiline plan editor', editor is not None and editor['rect'][3] >= 80)
        click('Back to plan')
        click('Refine')
        nodes = capture(label+'-refine')
        check(label+': clean refine draft', not any('# Goal' in n.get('text','') for n in nodes))
        mode('settings')
        capture(label+'-settings')
        ax = r.ctl(lane, 'a11y')
        (lane/f'{label}-settings-names.json').write_text(json.dumps(ax, indent=2))
        names = [n.get('name','') for n in flat([ax]) if n.get('role') == 'Button']
        check(label+': no badge-only Settings names', not any(name.isdigit() for name in names), names=names)
        mode('idle')
        r.ctl(lane, 'key tab', True)
        nodes = capture(label+'-keyboard')
        check(label+': keyboard action traversal', any('Keyboard actions' in n.get('text','') for n in nodes))
        r.ctl(lane, 'key escape', True)
        mode('denial')
        r.ctl(lane, 'type '+json.dumps('F3_STEERING_MESSAGE'), True)
        r.ctl(lane, 'key enter', True)
        nodes = capture(label+'-deny-steer')
        steering = next(n for n in nodes if n.get('text') == 'F3_STEERING_MESSAGE')
        answer = next(n for n in nodes if 'F3_DENIED_SAFELY' in n.get('text', ''))
        check(label+': settled denial chronology', steering['rect'][1] < answer['rect'][1], steering=steering['rect'], answer=answer['rect'])
        mode('images')
        import base64
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVmQAAAAASUVORK5CYII=')
        paths = [lane/'first image.png', lane/'second image.png']
        for path in paths: path.write_bytes(png)
        field = next(n for n in tree() if 'sf-editor' in n.get('class','').split())
        x,y,w,h = field['rect']
        r.ctl(lane, f'drop {x+w/2} {y+h/2} file '+json.dumps(str(paths[0]))+' file '+json.dumps(str(paths[1])), True)
        nodes = capture(label+'-two-images')
        chips = [n.get('text','') for n in nodes if 'image.png' in n.get('text','')]
        check(label+': two attached image chips', any('first image.png' in t for t in chips) and any('second image.png' in t for t in chips) and sum('68 B · attached' in t for t in chips) == 2, text=chips)
        mode('idle')
    failed = [c['name'] for c in checks if not c['passed']]
    status = 'expected-red' if a.baseline and failed else 'fail' if failed else 'pass'
finally:
    if (lane/'isolation.json').exists():
        shots = Path(json.loads((lane/'isolation.json').read_text())['shots'])
        if shots.exists(): shutil.copytree(shots, lane/'shots', dirs_exist_ok=True)
    if hasattr(r, 'children'): r.stop(lane)
    result = dict(status=locals().get('status','error'), checks=checks, measuredSizes=[[80,28],[100,30],[160,44]], evidenceClass='tern-serve+fixture')
    (r.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(r.out), **result),indent=2))
if not a.baseline: assert not failed, failed
