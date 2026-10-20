#!/usr/bin/env python3
"""Opt-in real free-model journey in an owned tern serve; never native/mobile-device certification."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import sys
import time
from types import SimpleNamespace

from lane import Runner, gate_open


def flat(items):
    return [n for item in items for n in [item, *flat(item.get('children', []))]]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('worktree', type=Path)
    p.add_argument('--receipts', type=Path, required=True)
    p.add_argument('--python', type=Path, required=True)
    p.add_argument('--env-file', type=Path, required=True, help='Authorized dotenv symlink target; never copied/logged')
    p.add_argument('--model', default='nvidia/nemotron-3.5-super-vl:free')
    p.add_argument('--allow-free-model-turns', action='store_true', required=True)
    a = p.parse_args()
    if not a.model.endswith(':free'):
        p.error('Only explicitly free OpenRouter models are permitted')
    if not a.env_file.is_file():
        p.error('Authorized dotenv target is missing')
    node = shutil.which('node')
    if not node:
        p.error('Node is required on PATH')
    r = Runner(SimpleNamespace(worktree=a.worktree, receipts=a.receipts, node=Path(node), python=a.python))
    # Runner defaults describe the inert lane. This lane explicitly authorizes real free turns.
    source = json.loads((r.out/'source.json').read_text())
    source.update(model_calls_allowed=True, provider='openrouter', model=a.model)
    (r.out/'source.json').write_text(json.dumps(source, indent=2)+'\n')
    lane = r.out/'tern-serve-real-turn'
    checks, captures = [], []
    result = dict(status='fail', evidenceClass='tern-serve+real-free-model', checks=checks, captures=captures)

    def check(name, passed, **details):
        checks.append(dict(name=name, passed=bool(passed), **details))
        if not passed:
            raise AssertionError(name)

    def tree():
        return flat(r.ctl(lane, 'tree')['tree'])

    def wait_for(predicate, label, seconds=60):
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(.2)
        raise TimeoutError(label)

    def has_class(n, value):
        return value in n.get('class', '').split()

    def shot(label):
        nodes = tree()
        (lane/(label+'-tree.json')).write_text(json.dumps(nodes, indent=2))
        state = r.ctl(lane, 'state')
        value = r.ctl(lane, 'shot '+label)
        captures.append(dict(label=label, state=state, shot=value))
        return nodes

    def messages():
        db = home/'state.db'
        if not db.exists():
            return []
        with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as c:
            return c.execute('select role,content,tool_calls from messages order by id').fetchall()

    def submit(text):
        assert '\n' not in text, 'Tern type newlines can submit extra turns'
        r.ctl(lane, 'type '+json.dumps(text, ensure_ascii=False), True)
        wait_for(lambda: any(text in n.get('text', '') for n in tree()), 'native composer draft admission')
        r.ctl(lane, 'key enter', True)

    try:
        r.command([node, r.root/'ui-tsp/scripts/build.mjs'], r.root, r.base_env, r.out/'build.log', timeout=120)
        check('owned serve account gate permits input', gate_open(r.isolation(lane, 'tern-serve')))
        home = lane/'proof/hermes-home'
        home.mkdir(parents=True)
        (home/'.env').symlink_to(a.env_file.resolve())
        # New disposable settings, not a copied owner profile with paid auxiliary/delegation defaults.
        config = dict(model=dict(default=a.model, provider='openrouter', max_tokens=512),
                      agent=dict(max_turns=5, reasoning_effort='none', disabled_toolsets=['delegation', 'cronjob']),
                      platform_toolsets=dict(cli=['terminal'], tui=['terminal']),
                      terminal=dict(backend='local', cwd=str(lane)),
                      delegation=dict(provider='openrouter', model=a.model, max_concurrent_children=1),
                      auxiliary=dict(free_only=True, openrouter_model=a.model, transient_retries=0,
                                     title_generation=dict(enabled=False, model_upgrade_enabled=False),
                                     background_review=dict(enabled=False),
                                     **{name: dict(provider='openrouter', model=a.model) for name in
                                        ['vision', 'compression', 'skills_hub', 'approval', 'review', 'mcp',
                                         'memory_query_rewrite', 'tts_audio_tags', 'triage_specifier',
                                         'kanban_decomposer', 'profile_describer', 'goal_judge', 'curator',
                                         'monitor', 'moa_reference', 'moa_aggregator']}),
                      fallback_model=None, fallback_models=[], compression=dict(enabled=False),
                      display=dict(skin='mono', show_reasoning=False), plugins=dict(enabled=[]), mcp_servers={},
                      auth=dict(adopt_external_logins=False), approvals=dict(mode='off'),
                      telemetry=dict(shared_metrics=dict(enabled=False, send=False)))
        # JSON is a valid YAML document and avoids adding a harness YAML dependency.
        (home/'config.yaml').write_text(json.dumps(config, indent=2)+'\n')
        env = dict(r.base_env, HOME=str(r.scratch/'private-home'), HERMES_HOME=str(home),
                   HERMES_PYTHON=str(a.python.absolute()), PYTHONPATH=str(r.root),
                   HERMES_PYTHON_SRC_ROOT=str(r.root), HERMES_TUI_CWD=str(lane), HERMES_TUI_SPLASH='0',
                   HERMES_TUI_TOOLSETS='terminal', HERMES_TERN='1',
                   TERN_CONFIG_DIR=r.env['TERN_CONFIG_DIR'], TERN_DAEMON_SOCKET=r.env['TERN_DAEMON_SOCKET'],
                   XDG_RUNTIME_DIR=r.env['XDG_RUNTIME_DIR'])
        # Interactive shell initialization is deliberately excluded from the actual app environment.
        command = 'env -i '+shlex.join([f'{k}={v}' for k,v in env.items()])+ ' '+shlex.join([node, str(r.root/'ui-tsp/dist/entry.js')])
        r.ctl(lane, 'run '+json.dumps(command), True)
        wait_for(lambda: any('Ask Hermes' in n.get('text', '') for n in tree()), 'real frontend ready')
        with sqlite3.connect(f'file:{home / "state.db"}?mode=ro', uri=True) as c:
            sessions = c.execute('select id,model from sessions').fetchall()
        check('private canonical session uses exact free model', len(sessions) == 1 and sessions[0][1] == a.model, sessions=sessions)
        nonce = 'TERN_JOURNEY_'+str(int(time.time()))
        submit(f'Use terminal exactly once to run python3 -c "import time; time.sleep(20); print(\'{nonce}\')" with timeout 30. Then reply exactly {nonce}_DONE. No other tools.')
        wait_for(lambda: any(has_class(n, 'sf-spinner') for n in tree()), 'real busy spinner', seconds=120)
        for label, width, height in [('phone-390',390,844), ('phone-412',412,915), ('80',744,900), ('100',924,900), ('160',1464,1000)]:
            r.ctl(lane, f'resize {width} {height}')
            time.sleep(.25)
            nodes = shot(label+'-busy')
            spinner = next((n for n in nodes if has_class(n, 'sf-spinner')), None)
            check(label+': real busy spinner has visible geometry', spinner is not None and all(v > 0 for v in spinner['rect'][2:]),
                  spinner=spinner.get('rect') if spinner else None)
        wait_for(lambda: any(role == 'tool' and nonce in (text or '') for role,text,_ in messages()), 'real terminal result', seconds=150)
        wait_for(lambda: any(role == 'assistant' and nonce+'_DONE' in (text or '') for role,text,_ in messages()), 'canonical assistant settlement', seconds=150)
        wait_for(lambda: not any(has_class(n, 'sf-spinner') for n in tree()), 'busy indicator settles')
        nodes = shot('settled')
        check('real answer painted', any(nonce+'_DONE' in n.get('text','') for n in nodes))
        submit(f'Reply exactly {nonce}_FOLLOWUP without tools.')
        wait_for(lambda: any(role == 'assistant' and nonce+'_FOLLOWUP' in (text or '') for role,text,_ in messages()), 'follow-up settled', seconds=150)
        wait_for(lambda: not any(has_class(n, 'sf-spinner') for n in tree()), 'follow-up idle')
        shot('followup-settled')
        rows = messages()
        (lane/'canonical-messages.json').write_text(json.dumps(rows, indent=2)+'\n')
        check('exactly two submitted user turns persisted', sum(role == 'user' for role,_,_ in rows) == 2)
        check('actual tool call persisted', any(role == 'assistant' and calls for role,_,calls in rows))
        r.ctl(lane, 'type '+json.dumps('/exit'), True)
        r.ctl(lane, 'key enter', True)
        wait_for(lambda: not r.ctl(lane, 'state')['focused'].get('running'), 'clean shell exit')
        result['status'] = 'pass'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        if (lane/'isolation.json').exists():
            shots = Path(json.loads((lane/'isolation.json').read_text())['shots'])
            if shots.exists():
                shutil.copytree(shots, lane/'shots', dirs_exist_ok=True)
        if hasattr(r, 'children'):
            r.stop(lane)
        (r.out/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(dict(receipt=str(r.out), **result), indent=2))


if __name__ == '__main__':
    main()
