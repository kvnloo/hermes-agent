#!/usr/bin/env python3
"""F4 rendered receipts with real App dispatch and an isolated presentation fixture."""
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
r = Runner(SimpleNamespace(worktree=a.worktree, receipts=a.receipts,
                           node=Path(shutil.which('node')), python=Path(sys.executable)))
lane = r.out / 'f4-serve'


def flat(items):
    return [n for item in items for n in [item, *flat(item.get('children', []))]]


def capture(label):
    tree = r.ctl(lane, 'tree')
    (lane / f'{label}-tree.json').write_text(json.dumps(tree, indent=2))
    (lane / f'{label}-dump.json').write_text(json.dumps(r.ctl(lane, 'dump'), indent=2))
    r.ctl(lane, 'shot f4-' + label)
    return flat(tree['tree'])


try:
    r.command([r.node, r.root / 'ui-tsp/e2e/f4.build.mjs', *(['--baseline'] if a.baseline else [])],
              r.root, r.base_env, r.out / 'build.log')
    assert gate_open(r.isolation(lane, 'tern-serve'))
    home = lane / 'proof/hermes-home'
    home.mkdir(parents=True)
    command = f'HERMES_HOME={shlex_quote(str(home))} HERMES_TUI_SPLASH=0 {shlex_quote(r.node)} {shlex_quote(str(r.root / "ui-tsp/dist/f4.fixture.js"))}'
    r.ctl(lane, 'run ' + json.dumps(command), True)
    r.ctl(lane, 'plugins expect WEB_CONTROL')
    r.ctl(lane, 'font 15', True)
    for cols, rows in [(80, 28), (100, 30), (160, 44)]:
        width, height = cols * 9 + 24, rows * 19 + 40
        for _ in range(40):
            r.ctl(lane, f'resize {width} {height}')
            time.sleep(.1)
            state = r.ctl(lane, 'state')
            pane = next(p for p in state['panes'] if p['id'] == state['focused']['id'])
            if pane['cols'] == cols and pane['rows'] == rows:
                break
            width += (cols - pane['cols']) * 9
            height += (rows - pane['rows']) * 19
        assert pane['cols'] == cols and pane['rows'] == rows, pane
        r.ctl(lane, 'wait 200')
        links = capture(f'{cols}x{rows}-links')
        anchors = [n.get('text') for n in links if n.get('tag') == 'a']
        # G02-001 remains deferred to the native renderer, not falsely green.
        assert 'WEB_CONTROL' in anchors and 'RELATIVE_README' not in anchors and 'FILE_README' not in anchors
        r.ctl(lane, 'key alt+up', True)
        dequeued = capture(f'{cols}x{rows}-dequeue')
        recalled = any(n.get('text') == 'F4_ALREADY_SENT' and 'sf-ed-text' in n.get('class', '') for n in dequeued)
        assert recalled == a.baseline, (cols, recalled, a.baseline)
        r.ctl(lane, 'key alt+,', True)
        time.sleep(.3)
        settings = capture(f'{cols}x{rows}-settings-on')
        switch = next(n for n in settings if n.get('role') == 'switch')
        x, y, w, h = switch['rect']
        r.ctl(lane, f'click {x+w/2} {y+h/2}', True)
        time.sleep(.3)
        capture(f'{cols}x{rows}-settings-off')
        r.ctl(lane, 'key escape', True)
        first = capture(f'{cols}x{rows}-reasoning-hidden')
        time.sleep(2.2)
        second = capture(f'{cols}x{rows}-reasoning-later')
        def reasoning(nodes):
            return [n['text'] for n in nodes if n.get('text', '').startswith('F4 reasoning')]
        unchanged = reasoning(first) == reasoning(second)
        assert unchanged != a.baseline, (cols, unchanged, a.baseline)
        r.ctl(lane, 'key alt+,', True)
        time.sleep(.2)
        settings = r.ctl(lane, 'tree')
        switch = next(n for n in flat(settings['tree']) if n.get('role') == 'switch')
        x, y, w, h = switch['rect']
        r.ctl(lane, f'click {x+w/2} {y+h/2}', True)
        r.ctl(lane, 'key escape', True)
finally:
    if hasattr(r, 'env'):
        r.stop(lane)
print(r.out)
