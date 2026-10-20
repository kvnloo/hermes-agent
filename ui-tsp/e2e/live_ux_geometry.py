#!/usr/bin/env python3
"""Rendered text/geometry regressions in isolated tern serve; fixture data, no model/audio calls."""
import argparse
import json
from pathlib import Path
import shutil
import signal
import sys
import time
from types import SimpleNamespace
from lane import Runner, gate_open, shlex_quote

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('worktree', type=Path)
p.add_argument('--receipts', type=Path, required=True)
p.add_argument('--baseline', action='store_true', help='Build base view sources verbatim and retain expected red assertions')
p.add_argument('--baseline-ref', help='Exact Git revision for the negative control (requires --baseline)')
a = p.parse_args()
if a.baseline_ref and not a.baseline:
    p.error('--baseline-ref requires --baseline')
node_command = shutil.which('node')
assert node_command is not None
node = Path(node_command).absolute()
r = Runner(SimpleNamespace(worktree=a.worktree, receipts=a.receipts, node=node, python=Path(sys.executable)))
lane = r.out/'tern-serve-live-ux'
measurements = []
checks = []
result = dict(evidenceClass='tern-serve+presentation-fixture', status='fail', baseline=a.baseline,
              measurements=measurements, checks=checks)


def flat(items):
    return [n for item in items for n in [item, *flat(item.get('children', []))]]


def has_class(node, name):
    return name in node.get('class', '').split()


def check(name, passed, **details):
    checks.append(dict(name=name, passed=bool(passed), **details))


def capture(label):
    tree = r.ctl(lane, 'tree')
    (lane/f'{label}-tree.json').write_text(json.dumps(tree, indent=2))
    (lane/f'{label}-dump.json').write_text(json.dumps(r.ctl(lane, 'dump'), indent=2))
    shot = r.ctl(lane, 'shot live-ux-'+label)
    return flat(tree['tree']), shot


def dock_checks(nodes, label):
    text = [n['text'] for n in nodes if n.get('text')]
    check(label+': voice opt-in/off has no dock UI', not any('Live voice' in t for t in text))
    check(label+': unsupported hold hint absent', not any('Hold-to-talk unavailable' in t for t in text))
    check(label+': command painted exactly once', sum('LIVE_UX_SINGLE_COMMAND' in t for t in text) == 1)
    check(label+': no empty Thought disclosure', not any(t.startswith(('Thought', 'Thinking')) for t in text))
    dock = next(n for n in nodes if has_class(n, 'sf-dock'))
    placeholder = next(n for n in flat([dock]) if has_class(n, 'sf-ed-ph'))
    bottom = placeholder['rect'][1] + placeholder['rect'][3]
    hints = [n for n in flat([dock]) if n.get('text') and n['rect'][1] >= bottom-1 and
             not has_class(n, 'sf-caption-name')]
    x, y, w, h = dock['rect']
    outside = [n for n in hints if n['rect'][0] < x-.5 or n['rect'][0]+n['rect'][2] > x+w+.5 or
               n['rect'][1]+n['rect'][3] > y+h+.5]
    wrapped = [n for n in hints if n['rect'][3] > 24 and not has_class(n, 'kbd') and n['text'] != 'Stop']
    overlap = []
    for i, left in enumerate(hints):
        lx, ly, lw, lh = left['rect']
        for right in hints[i+1:]:
            rx, ry, rw, rh = right['rect']
            if min(lx+lw, rx+rw)-max(lx, rx) > .5 and min(ly+lh, ry+rh)-max(ly, ry) > .5:
                overlap.append([left['text'], right['text']])
    check(label+': footer inside dock without wrapping/overlap', not outside and not wrapped and not overlap,
          outside=[n['text'] for n in outside], wrapped=[n['text'] for n in wrapped], overlap=overlap,
          visibleHints=[dict(text=n['text'], rect=n['rect']) for n in hints])
    check(label+': Context below placeholder and Settings intact', any(n['text'] == 'Context' for n in hints)
          and any(n['text'] == 'Settings' for n in hints))
    return [n['text'] for n in hints]


def working_checks(nodes, label):
    """omp's working row: painted spinner, then elapsed, then the shimmering intent, left to right."""
    shimmer = next((n for n in nodes if has_class(n, 'sf-shimmer')), None)
    row = next((n for n in nodes if any(c is shimmer for c in n.get('children', []))), None) if shimmer else None
    kids = flat(row.get('children', [])) if row else []
    spinner = next((n for n in kids if has_class(n, 'sf-spinner')), None)
    elapsed = next((n for n in kids if has_class(n, 'sf-elapsed')), None)
    ordered = (shimmer is not None and spinner is not None and elapsed is not None
               and spinner['rect'][2] > 0 and spinner['rect'][3] > 0
               and spinner['rect'][0] < elapsed['rect'][0] < shimmer['rect'][0])
    check(label+': working row paints omp spinner, elapsed, intent in order', ordered,
          classes=[n.get('class', '') for n in kids][:12])
    dock = next((n for n in nodes if has_class(n, 'sf-dock')), None)
    # Tern projects omp.working.stop into the composer's native Stop button.
    # It is a dock sibling, not a child of the spinner/elapsed/intent row.
    stop = next((n for n in flat([dock]) if n.get('tag') == 'button'
                 and n.get('title', '').startswith('Stop')), None) if dock else None
    def inside(node):
        if node is None or dock is None:
            return False
        x, y, w, h = node['rect']
        dx, dy, dw, dh = dock['rect']
        return w > 0 and h > 0 and x >= dx-.5 and y >= dy-.5 and x+w <= dx+dw+.5 and y+h <= dy+dh+.5
    check(label+': spinner and Stop inside visible dock', inside(spinner) and inside(stop),
          spinner=spinner.get('rect') if spinner else None, stop=stop.get('rect') if stop else None,
          dock=dock.get('rect') if dock else None)


def interrupted(signum, frame):
    raise InterruptedError(f'render gate interrupted by signal {signum}')


signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)

try:
    r.command([node, r.root/'ui-tsp/e2e/live-ux.build.mjs', *(['--baseline'] if a.baseline else []),
               *(['--baseline-ref', a.baseline_ref] if a.baseline_ref else [])],
              r.root, r.base_env, r.out/'build-fixture.log')
    assert gate_open(r.isolation(lane, 'tern-serve'))
    home = lane/'proof/hermes-home'
    home.mkdir(parents=True)
    mode_file = lane/'mode.txt'
    mode_file.write_text('idle')
    command = f"HERMES_HOME={shlex_quote(str(home))} HERMES_TUI_SPLASH=0 {shlex_quote(str(node))} {shlex_quote(str(r.root/'ui-tsp/dist/live-ux.fixture.js'))} {shlex_quote(str(mode_file))}"
    r.ctl(lane, 'run '+json.dumps(command), True)
    r.ctl(lane, 'plugins expect LIVE_UX_VISIBLE_ANSWER')
    r.ctl(lane, 'font 15', True)
    # Pixel-sized phone simulations are not physical mobile-client certification.
    viewports = [('phone-390', None, 390, 844), ('phone-412', None, 412, 915),
                 *[(str(cols), cols, cols*9+24, 900) for cols in [80, 100, 180]]]
    for label, cols, width, height in viewports:
        measured = None
        for attempt in range(40):
            r.ctl(lane, f'resize {width} {height}')
            time.sleep(.1)
            state = r.ctl(lane, 'state')
            measured = next(p for p in state['panes'] if p['id'] == state['focused']['id'])
            if cols is None or measured['cols'] == cols: break
            width += (cols-measured['cols'])*9 if abs(cols-measured['cols']) > 1 else (1 if cols > measured['cols'] else -1)
        assert measured is not None and (cols is None or measured['cols'] == cols), measured
        r.ctl(lane, 'wait 200')
        row = dict(label=label, cols=measured['cols'], actual=measured, viewport=[width,height])
        measurements.append(row)
        nodes, row['dockShot'] = capture(f'{label}-dock')
        row['visibleHints'] = dock_checks(nodes, f'{label}-idle')
        mode_file.write_text('busy')
        time.sleep(.3)
        r.ctl(lane, 'wait 200')
        nodes, row['busyShot'] = capture(f'{label}-busy')
        dock_checks(nodes, f'{label}-busy')
        working_checks(nodes, f'{label}-busy')
        mode_file.write_text('idle')
        time.sleep(.3)
        r.ctl(lane, 'key alt+m', True)
        time.sleep(.3)
        r.ctl(lane, 'wait 200')
        nodes, row['pickerShot'] = capture(f'{label}-picker')
        compact = next((n for n in nodes if has_class(n, 'pk-scopebtn')), None)
        if compact:
            # Exact owned fixture button, resolved from the just-read native tree.
            x, y, w, h = compact['rect']
            r.ctl(lane, f'click {x+w/2} {y+h/2}', True)
            r.ctl(lane, 'wait 200')
            nodes, row['scopesShot'] = capture(f'{label}-scopes')
        headings = [n['text'] for n in nodes if n.get('text') in ['Providers', 'Locked providers']]
        labels = [n['text'] for n in nodes if n.get('text') in ['Ready A','Ready B','Ready C','Locked A','Locked B']]
        # Provider preview/list may repeat Ready A: scope labels are native lbl nodes.
        scope_labels = ([n['text'].rsplit(' ', 1)[0] for n in nodes if has_class(n, 'mi') and n.get('text', '').startswith(('Ready ', 'Locked '))]
                        if compact else [n['text'] for n in nodes if has_class(n, 'lbl') and n.get('text') in labels])
        check(f'{label}: provider headings appear once each (compact menu has no headings)',
              headings == ([] if compact else ['Providers', 'Locked providers']), headings=headings)
        check(f'{label}: authenticated first, stable in both groups', scope_labels == ['Ready A','Ready B','Ready C','Locked A','Locked B'], labels=scope_labels)
        if compact: r.ctl(lane, 'key escape', True)
        r.ctl(lane, 'key escape', True)
    narrow = next(m for m in measurements if m['label'] == '80')
    check('priority degradation: Settings/model retained while low-priority help drops at 80',
          'f1 help' not in narrow['visibleHints'] and 'Settings' in narrow['visibleHints']
          and 'nvidia/nemotron-3.5-super-v1:free' in narrow['visibleHints'])
    check('priority degradation: cost drops at 80, returns when measured room permits',
          '$0.12' not in narrow['visibleHints'] and '$0.12' in measurements[-1]['visibleHints'])
    failed = [c['name'] for c in checks if not c['passed']]
    result['failed'] = failed
    result['status'] = 'expected-red' if a.baseline and failed else 'fail' if failed else 'pass'
    if not a.baseline: assert not failed, failed
finally:
    if (lane/'isolation.json').exists():
        shots = Path(json.loads((lane/'isolation.json').read_text())['shots'])
        if shots.exists(): shutil.copytree(shots, lane/'shots', dirs_exist_ok=True)
    if hasattr(r, 'children'): r.stop(lane)
    (r.out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(receipt=str(r.out), **result), indent=2))
