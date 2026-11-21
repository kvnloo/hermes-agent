#!/usr/bin/env python3
"""Run exact-head offline measurements. Setup needs GitHub/PyPI, experiments do not use providers."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

HEADS = {
    'main': 'fab9b01c915a3118cc8daa6cc1b18c15b3f982d0',
    'read': 'af16e3ab16eed2492552c325ad1777533a8b7004',
    'chain': '2c1941aac46efac3b35605d99a8628e75a91c670',
    'governance': '5b31ccb7d56ad614da63588ef876584b9f95dd3f',
    'preservation': 'e543544aca215bf7ea838444b6df58bdbbd3e38c',
    'staging': 'f678f4c7e5d994f03d8759fe0e950d3407ccca7e',
    'nosave': '96dc75192a82b6c5645a89c2eb894fba97ad2bbd',
}
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results'

def cmd(args, cwd=None, env=None, check=True):
    print('+', ' '.join(map(str, args)), flush=True)
    completed = subprocess.run(list(map(str, args)), cwd=cwd, env=env, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(completed.stdout, flush=True)
    if check and completed.returncode:
        raise RuntimeError(f'Command failed ({completed.returncode}): {args}')
    return completed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', nargs='*')
    args = parser.parse_args()
    RESULTS.mkdir(exist_ok=True)
    paths = {}
    for name, sha in HEADS.items():
        path = ROOT / 'checkouts' / name
        if not path.exists():
            path.parent.mkdir(exist_ok=True)
            cmd(['git', 'init', path])
            cmd(['git', 'fetch', '--no-tags', '--depth=1', 'https://github.com/NousResearch/hermes-agent.git', sha], path)
            cmd(['git', 'checkout', '--detach', 'FETCH_HEAD'], path)
        paths[name] = path
    venv = ROOT / 'venv'
    if not venv.exists():
        cmd([sys.executable, '-m', 'venv', venv])
        cmd([venv / 'bin/python', '-m', 'pip', 'install', '-r', ROOT / 'requirements.txt'])
    python = venv / 'bin/python'
    freeze = cmd([python, '-m', 'pip', 'freeze']).stdout
    (RESULTS / 'dependencies.txt').write_text(freeze)
    environment = {k: v for k, v in os.environ.items() if not (
        k.startswith('HERMES_') or any(s in k for s in ('TOKEN', 'SECRET', 'PASSWORD', 'API_KEY')))}
    environment.update(PYTHONDONTWRITEBYTECODE='1', DO_NOT_TRACK='1', HERMES_DISABLE_TELEMETRY='1')
    measurements = []
    jobs = [('read-main', 'read_dispatch.py', 'main'), ('read-pr141876', 'read_dispatch.py', 'read'),
            ('read-pr139606', 'read_dispatch.py', 'governance'), ('chain-pr116673', 'chain_bounds.py', 'chain'),
            ('long-main', 'long_session.py', 'main'), ('long-pr140008', 'long_session.py', 'preservation'),
            ('consent-main', 'consent.py', 'main'), ('consent-pr116834', 'consent.py', 'staging'),
            ('consent-pr116846', 'consent.py', 'nosave')]
    combination = ROOT / 'checkouts' / 'combination'
    combination_error = None
    try:
        if not combination.exists():
            cmd(['git', 'init', combination])
            cmd(['git', 'fetch', '--no-tags', '--depth=1',
                 'https://github.com/NousResearch/hermes-agent.git',
                 HEADS['main'], HEADS['staging'], HEADS['nosave']], combination)
            cmd(['git', 'checkout', '--detach', HEADS['main']], combination)
            cmd(['git', 'config', 'user.name', 'RFC Synthetic Study'], combination)
            cmd(['git', 'config', 'user.email', 'rfc-study@example.invalid'], combination)
            for name, phase in [('staging', 'target'), ('nosave', 'combined')]:
                cmd(['git', 'merge', '-s', 'ours', '--no-commit', '--allow-unrelated-histories', HEADS[name]], combination)
                cmd([python, ROOT / 'harness/consent_combination.py', '--checkout', combination,
                     '--phase', phase, '--output', RESULTS / f'combination-{phase}.json'])
                cmd(['git', 'add', 'tools/memory_tool.py', 'agent/background_review.py', 'tests'], combination)
                cmd(['git', 'commit', '-m', f'study: downstream semantic consent integration ({phase})'], combination)
        paths['combination'] = combination
        jobs.append(('consent-combination', 'consent.py', 'combination'))
    except Exception as exc:
        combination_error = str(exc)
        (RESULTS / 'combination-blocker.json').write_text(json.dumps({'blocker': str(exc)}, indent=2))
    for name, script, checkout in jobs:
        if args.only is not None and name not in args.only:
            continue
        start = time.monotonic()
        process = cmd([python, ROOT / 'harness' / script, '--checkout', paths[checkout],
                       '--output', RESULTS / (name + '.json')], env=environment, check=False)
        (RESULTS / (name + '.log')).write_text(process.stdout)
        measurements.append({'name': name, 'head': HEADS.get(checkout, 'see consent-combination.json'),
                             'returncode': process.returncode, 'seconds': time.monotonic() - start})
    (RESULTS / 'execution.json').write_text(json.dumps({'platform': platform.platform(),
        'python': sys.version, 'head_pins': HEADS, 'jobs': measurements,
        'combination_scope': 'Downstream semantic integration. Native ours merges retain both PR parents. Selected consent changes overlay pinned main, not an unmodified upstream PR head.',
        'providers_called_by_design': False}, indent=2))
    return 2 if combination_error or any(job['returncode'] for job in measurements) else 0

if __name__ == '__main__':
    raise SystemExit(main())
