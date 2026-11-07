"""#342 steps 1-2: the sandbox policy, the bwrap argv built from it, and the real boundary it builds.

Every check runs against a scratch fixture home; the boundary suite only reads (``[ -w ]``,
``findmnt``, ``test -e``) and never write-probes a file (the 2026-11-05 auth.json lesson).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gateway import worker_sandbox as ws


def _fixture(tmp_path):
    root = tmp_path / 'hh'
    for name in ('a', 'b'):
        prof = root / 'profiles' / name
        (prof / 'skills' / 's1').mkdir(parents=True)
        (prof / 'skills' / 's1' / 'SKILL.md').write_text('x')
        (prof / 'state.db').write_bytes(b'SQLite format 3\0')
        (prof / '.env').write_text('FAKE=1\n')
        (prof / 'auth.json').write_text('{"fixture": true}')
        (prof / 'config.yaml').write_text('model: {default: m}\n')
    (root / 'state.db').write_bytes(b'SQLite format 3\0')
    (root / 'skills').mkdir()
    (root / 'auth.json').write_text('{"fixture": true}')
    secret = tmp_path / 'bws-secrets'
    secret.mkdir()
    (secret / 'scope.env').write_text('TOKEN=fixture\n')
    shared = tmp_path / 'ops'
    shared.mkdir()
    return root, root / 'profiles' / 'a', secret, shared


def _enable(home, body):
    (home / 'sandbox.yaml').write_text('enabled: true\n' + body)


# --- step 1: policy parse and argv -------------------------------------------------------------

def test_policy_absent_or_disabled_is_off(tmp_path):
    _, home, _, _ = _fixture(tmp_path)
    assert ws.load_policy(home) is None
    (home / 'sandbox.yaml').write_text('enabled: false\nhidden: [/x]\n')
    assert ws.load_policy(home) is None
    assert ws.wrap_worker(ws.load_policy(home), ['py'], {'A': '1'}, home) == (['py'], {'A': '1'})


def test_policy_shapes_and_refusals(tmp_path, monkeypatch):
    _, home, secret, shared = _fixture(tmp_path)
    monkeypatch.setenv('SBX_OPS', str(shared))
    _enable(home, f'ro:\n  - path: /usr\nrw:\n  - path: $SBX_OPS\nhidden:\n  - {secret}\n')
    policy = ws.load_policy(home)
    assert policy.rw == (shared,) and policy.hidden == (secret,) and policy.ro == (Path('/usr'),)
    _enable(home, f'rw: [{home}/auth.json]\n')
    with pytest.raises(ws.SandboxUnavailable, match='credential file'):
        ws.load_policy(home)
    _enable(home, 'hidden: [relative/path]\n')
    with pytest.raises(ws.SandboxUnavailable, match='not absolute'):
        ws.load_policy(home)


def _argv(tmp_path, body=''):
    root, home, secret, shared = _fixture(tmp_path)
    _enable(home, body.format(secret=secret, shared=shared))
    argv = ws.build_argv(ws.load_policy(home), ['true'], root=root, required=[], cwd=home, bwrap='bwrap')
    return argv, root, home, secret, shared


def _binds(argv):
    """(flag, dest) in mount order."""
    out, i = [], 1
    while i < len(argv) and argv[i] != '--':
        flag = argv[i]
        if flag in ('--ro-bind', '--bind'):
            out.append((flag, argv[i + 2])); i += 3
        elif flag in ('--tmpfs', '--dev', '--proc', '--chdir'):
            out.append((flag, argv[i + 1])); i += 2
        else:
            out.append((flag, None)); i += 1
    return out


def test_argv_hides_other_profiles_and_keeps_credentials_read_only(tmp_path):
    argv, root, home, secret, shared = _argv(tmp_path, 'rw: [{shared}]\nhidden: [{secret}]\n')
    binds = _binds(argv)
    assert binds[0] == ('--ro-bind', '/') and ('--tmpfs', '/tmp') in binds
    assert ('--tmpfs', str(root / 'profiles')) in binds  # every other profile
    assert ('--ro-bind', str(root / 'state.db')) in binds  # default profile's data reads empty
    assert ('--tmpfs', str(secret)) in binds
    last = {dest: flag for flag, dest in binds if flag != '--chdir'}  # later mounts win
    assert last[str(home)] == '--bind' and last[str(shared)] == '--bind'
    assert last[str(home / 'auth.json')] == '--ro-bind' and last[str(home / '.env')] == '--ro-bind'
    rw = [dest for flag, dest in binds if flag == '--bind']
    assert not any(Path(d).name in ws.CREDENTIAL_NAMES for d in rw), rw
    assert {'--unshare-pid', '--die-with-parent', '--new-session'} <= set(argv)
    assert argv[-2:] == ['--', 'true']


def test_live_profile_is_bound_in_place_never_a_copy(tmp_path):
    """Invariant 1: the worker reads the live profile's config at each launch (A19 canary died on a
    frozen copy with ``fallback_providers: []``)."""
    argv, _, home, _, _ = _argv(tmp_path)
    i = argv.index('--bind')
    assert argv[i + 1] == argv[i + 2] == str(home)
    (home / 'sandbox.yaml').write_text('enabled: false\n')  # re-read per launch, not cached
    assert ws.load_policy(home) is None


def test_default_profile_home_does_not_re_expose_other_profiles(tmp_path):
    """The default profile's home is the install root: its rw bind must come before the hidden
    ``profiles`` tmpfs, or the bind re-exposes every other profile."""
    root, _, _, _ = _fixture(tmp_path)
    _enable(root, '')
    binds = _binds(ws.build_argv(ws.load_policy(root), ['true'], root=root, required=[], cwd=root, bwrap='bwrap'))
    assert binds.index(('--bind', str(root))) < binds.index(('--tmpfs', str(root / 'profiles')))
    assert ('--ro-bind', str(root / 'auth.json')) in binds[binds.index(('--bind', str(root))):]


def test_hidden_path_covering_required_or_home_is_refused(tmp_path):
    root, home, _, _ = _fixture(tmp_path)
    _enable(home, f'hidden: [{root}]\n')
    with pytest.raises(ws.SandboxUnavailable, match='covers required'):
        ws.build_argv(ws.load_policy(home), ['true'], root=root, required=[], cwd=home, bwrap='bwrap')


def test_missing_bwrap_fails_closed(tmp_path, monkeypatch):
    _, home, _, _ = _fixture(tmp_path)
    _enable(home, '')
    monkeypatch.setattr(ws.shutil, 'which', lambda name: None)
    with pytest.raises(ws.SandboxUnavailable, match='bwrap is not installed'):
        ws.wrap_worker(ws.load_policy(home), ['py'], {}, home)


def test_wrap_injects_hidden_paths_notice(tmp_path, monkeypatch):
    root, home, secret, _ = _fixture(tmp_path)
    monkeypatch.setenv('HERMES_HOME', str(root))
    _enable(home, f'hidden: [{secret}]\n')
    argv, env = ws.wrap_worker(ws.load_policy(home), ['py', '-m', 'agent.managed_worker'], {'K': 'v'}, home)
    assert argv[-3:] == ['py', '-m', 'agent.managed_worker'] and 'bwrap' in Path(argv[0]).name
    assert env['K'] == 'v' and str(secret) in env[ws.NOTICE_ENV] and 'NOT an answer' in env[ws.NOTICE_ENV]


# --- step 2: the real boundary (non-mutating checks only) --------------------------------------

needs_bwrap = pytest.mark.skipif(sys.platform != 'linux' or not shutil.which('bwrap'), reason='bwrap (Linux) only')


@pytest.fixture
def outside_tmp():
    """A fixture base outside /tmp: the boundary replaces /tmp with a tmpfs, which would make every
    'hidden' check pass vacuously."""
    import tempfile
    base = Path(tempfile.mkdtemp(prefix='sbx342-', dir='/var/tmp'))
    yield base
    shutil.rmtree(base, ignore_errors=True)


@needs_bwrap
def test_boundary_suite(outside_tmp):
    argv, root, home, secret, shared = _argv(outside_tmp, 'rw: [{shared}]\nhidden: [{secret}]\n')
    b = root / 'profiles' / 'b'

    def inside(script):
        cmd = argv[:-1] + ['sh', '-c', script]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False).stdout.strip()

    assert subprocess.run(['test', '-e', f'{b}/state.db'], check=False).returncode == 0  # present on the host
    assert inside(f'test -r {root}/auth.json && echo R') == 'R'  # control: outside /tmp is visible
    assert inside(f'test -e {b}/state.db && echo SEEN || echo GONE') == 'GONE'
    assert inside(f'ls {b}/skills 2>/dev/null | wc -l') == '0'
    assert inside(f'test -e {b}/.env && echo SEEN || echo GONE') == 'GONE'
    assert inside(f'ls {secret} | wc -l') == '0'
    assert inside(f'head -c 15 {home}/state.db') == 'SQLite format 3'
    assert inside(f'[ -w {home}/config.yaml ] && echo W || echo RO') == 'W'
    assert inside(f'[ -w {home}/auth.json ] && echo W || echo RO') == 'RO'
    assert inside(f'[ -w {home}/.env ] && echo W || echo RO') == 'RO'
    assert inside(f'findmnt -no OPTIONS --target {home}/auth.json').startswith('ro')
    assert inside(f'[ -w {shared} ] && echo W || echo RO') == 'W'
    assert inside(f'[ -w {root}/auth.json ] && echo W || echo RO') == 'RO'
    assert inside('[ -w /usr ] && echo W || echo RO') == 'RO'
    assert inside('echo $$') in ('1', '2')  # own pid namespace
    assert inside(f'cat /proc/{os.getpid()}/environ 2>/dev/null | wc -c') == '0'  # no host environ
