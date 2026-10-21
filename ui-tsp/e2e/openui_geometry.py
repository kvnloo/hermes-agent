#!/usr/bin/env python3
"""Real Tern-serve Luau geometry/capture regression; not ordinary-window evidence."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace
from lane import Runner, gate_open

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('worktree', type=Path)
p.add_argument('--document', type=Path)
p.add_argument('--receipts', type=Path, required=True)
p.add_argument('--capture', action='store_true')
p.add_argument('--baseline', action='store_true')
a = p.parse_args()
node_command = shutil.which('node')
assert node_command is not None
node = Path(node_command).absolute()


class OpenUIRunner(Runner):
    def process(self, argv, lane, name):
        if name == 'tern':
            self.document = a.document
            if self.document is None:
                children = [dict(id=f'n{i}', label=f'dense-{i}.ts', code=max(0, 1000000//(i+1)**3-1), churn=i%3, children=[]) for i in range(113)]
                children[0]['children'] = [dict(id='leaf', label='leaf.ts', code=children[0]['code'], churn=0, children=[])]
                self.document = lane/'dense.json'
                self.document.write_text(json.dumps(dict(version=1, title='Synthetic dense 113-cell regression', root=dict(
                    id='repo', label='repo', children=children, code=sum(n['code'] for n in children), churn=sum(n['churn'] for n in children)))))
            preview = self.root/'ui-tsp/experiments/openui-preview'
            self.command(['tern', 'plugin', 'link', preview/'tern'], lane, self.env, lane/'plugin-link.log')
            prepared = self.command([node, preview/'cli.mjs', 'prepare', self.root/'ui-tsp/experiments/openui-generation/fixtures/explorer.openui',
                self.document, 'geometry:isolated', lane/'bundles', '--json'], lane, self.env, lane/'prepare.log')
            self.notice = json.loads(prepared.stdout)
            # Headless Tern uses its explicit fixture-plugin loader, not the
            # ordinary daemon/window route. It runs these exact Luau sources.
            self.env['STENCIL_FIXTURE_ROOT'] = str(lane/'crates/tern')
            (lane/'crates/tern/goldens').mkdir(parents=True)
        return super().process(argv, lane, name)


r = OpenUIRunner(SimpleNamespace(worktree=a.worktree, receipts=a.receipts, node=node, python=Path(sys.executable)))
lane = r.out/'tern-serve-openui'
result = dict(evidenceClass='tern-serve+real-Luau+fixture-plugin-root', status='fail', measurements=[])
try:
    state = r.isolation(lane, 'tern-serve')
    assert gate_open(state), 'isolated account gate blocks this test'
    r.command(['tern', 'plugin', 'list'], lane, r.env, lane/'plugin-list.log')
    document = json.loads(r.document.read_text())
    fixture_root = lane/'crates/plugins/fixtures'
    fixture_root.mkdir(parents=True)
    plugin = r.root/'ui-tsp/experiments/openui-preview/tern'
    if a.baseline:
        baseline_plugin = lane/'baseline-plugin'
        shutil.copytree(plugin, baseline_plugin)
        source = r.command(['git', 'show', '724b2aaec5:ui-tsp/experiments/openui-preview/tern/host.luau'],
            r.root, r.base_env, lane/'baseline-source.log')
        (baseline_plugin/'host.luau').write_text(source.stdout)
        plugin = baseline_plugin
    (fixture_root/'hermes-openui').symlink_to(plugin, target_is_directory=True)
    r.ctl(lane, 'plugins fixtures')
    r.ctl(lane, 'file open '+json.dumps(r.notice['path']), True)
    r.ctl(lane, 'plugins expect '+json.dumps(document['title'][:64]))
    surface = ".tn-pane.on [data-surface='plugin.hermes-openui.reply']"
    r.ctl(lane, 'zoom', True)
    expected = min(128, len(document['root']['children']))
    for width, height in [(720, 800), (1280, 900), (1800, 1100)]:
        r.ctl(lane, f'size {width} {height}', True)
        for mode, key in [('code', '1'), ('churn', '2')]:
            r.ctl(lane, 'key '+key, True)
            r.ctl(lane, 'wait 100')
            maps = r.ctl(lane, f'dump {surface} .nv-map')['elements']
            cells = r.ctl(lane, f'dump {surface} .nv-cell')['elements']
            assert len(maps) == 1 and len(cells) == expected, (len(maps), len(cells), expected)
            x,y,w,h = maps[0]['rect']
            outside = [c for c in cells if c['rect'][0] < x-.1 or c['rect'][1] < y-.1 or
                c['rect'][0]+c['rect'][2] > x+w+.1 or c['rect'][1]+c['rect'][3] > y+h+.1]
            result['measurements'].append(dict(viewport=[width,height],mode=mode,cells=len(cells),outside=len(outside),map=maps[0]['rect']))
            r.ctl(lane, f'shot dense-{width}-{mode}')
            assert not outside, f'{len(outside)}/{len(cells)} cells overflow the map'
    # The root can be contained even when a drilled singleton has zero height.
    if not a.document:
        for cols, rows in [(80, 28), (100, 30), (160, 44)]:
            width, height = cols * 9 + 24, rows * 19 + 100
            for _ in range(70):
                r.ctl(lane, f'resize {width} {height}')
                state = r.ctl(lane, 'state')
                pane = next(p for p in state['panes'] if p['id'] == state['focused']['id'])
                dc, dr = cols - pane['cols'], rows - pane['rows']
                if not dc and not dr:
                    break
                width += dc * 8 if abs(dc) > 1 else dc
                height += dr * 17 if abs(dr) > 1 else dr
            assert (pane['cols'], pane['rows']) == (cols, rows), pane
            r.ctl(lane, 'click '+json.dumps(surface+' [data-role="hermes.openui.code"]'), True)
            time.sleep(.5)
            r.ctl(lane, 'click '+json.dumps(surface+' [data-role="hermes.openui.child.n0"]'), True)
            time.sleep(.5)
            cells = r.ctl(lane, f'dump {surface} .nv-cell')['elements']
            r.ctl(lane, f'shot singleton-{cols}x{rows}')
            result['measurements'].append(dict(size=[cols, rows], singleton=cells))
            assert len(cells) == 1 and cells[0]['rect'][2] > 0 and cells[0]['rect'][3] > 0, cells
            r.ctl(lane, 'click '+json.dumps(surface+' [data-role="hermes.openui.back"]'), True)
            time.sleep(.5)
    if a.capture:
        r.ctl(lane, 'key 1', True)
        r.ctl(lane, 'wait 100')
        preview = r.root/'ui-tsp/experiments/openui-preview'
        r.command([node, preview/'cli.mjs', 'capture', r.notice['path'], str(r.port), json.loads((lane/'isolation.json').read_text())['shots'],
            '--allow-control-input'], lane, r.env, lane/'capture.log', timeout=150)
        result['capture'] = 'captured-not-inspected; four PNG headers/hashes; no approval'
    result['status'] = 'pass'
except Exception as e:
    result['error'] = str(e)
    try:
        (lane/'failure-tree.json').write_text(json.dumps(r.ctl(lane, 'tree'), indent=2))
        (lane/'failure-state.json').write_text(json.dumps(r.ctl(lane, 'state'), indent=2))
    except Exception as diagnostic:
        result['diagnostic_error'] = str(diagnostic)
    raise
finally:
    if (lane/'isolation.json').exists():
        shots = Path(json.loads((lane/'isolation.json').read_text())['shots'])
        if shots.exists():
            shutil.copytree(shots, lane/'shots', dirs_exist_ok=True)
    if hasattr(r, 'children'):
        r.stop(lane)
    (r.out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(r.out),**result),indent=2))
