"""Per-profile filesystem boundary for managed workers (kvnloo/oss-factory#342).

The shared gateway keeps routing, sessions and platforms; a managed turn's agent loop and tools run
in ``agent.managed_worker``. When ``<home>/sandbox.yaml`` says ``enabled: true`` the owner launches
that worker inside ``bwrap`` built from the profile's declared policy:

- the whole filesystem read-only, ``/tmp`` a private tmpfs;
- every other profile hidden (``<root>/profiles`` and, for a named profile, the default profile's
  data at the root), plus the policy's ``hidden`` paths (a directory becomes an empty tmpfs, a
  file reads as empty);
- the profile's own home read-write, its ``.env`` / ``auth.json`` re-bound read-only on top
  (credentials are never rw-bound: ``utils._atomic_write`` falls back to an in-place rewrite on
  EBUSY, which would edit the live file through the bind);
- the policy's ``ro`` / ``rw`` paths, and the gateway control socket the worker reports through;
- ``--unshare-pid`` (no host ``/proc/<pid>/environ``), ``--die-with-parent``, ``--new-session``.

The worker's config is the live profile itself, bound in place: never a prepared copy. The policy
is re-read at every launch. Off by default; enabled with ``bwrap`` missing refuses the turn
(``sandbox_unavailable``) instead of running it unsandboxed.
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

POLICY_FILE = 'sandbox.yaml'
NOTICE_ENV = 'HERMES_SANDBOX_NOTICE'
PID_NS_ENV = 'HERMES_WORKER_PID_NS'  # set by the owner: this worker runs in its own pid namespace
_host_pid = None
CREDENTIAL_NAMES = frozenset({'.env', 'auth.json', 'auth.lock'})
# Default-profile data that a named profile's worker must not read at the install root.
ROOT_PROFILE_DATA = ('state.db', 'state.db-wal', 'state.db-shm', 'sessions', 'memories', 'skills', 'logs',
                     'SOUL.md', 'cron', 'plugins')


class SandboxUnavailable(RuntimeError):
    """The profile asked for a boundary this host cannot build; the turn is refused, never run bare."""

    def __init__(self, detail: str):
        super().__init__(f'sandbox_unavailable: {detail}')
        self.detail = detail


@dataclass(frozen=True)
class SandboxPolicy:
    home: Path
    ro: tuple = ()
    rw: tuple = ()
    hidden: tuple = ()
    extra: dict = field(default_factory=dict)


def _paths(raw, key):
    out = []
    for item in raw.get(key) or []:
        value = item.get('path') if isinstance(item, dict) else item
        if not isinstance(value, str) or not value.strip():
            raise SandboxUnavailable(f'{POLICY_FILE}: {key} entries must be paths')
        path = Path(os.path.expanduser(os.path.expandvars(value.strip())))
        if not path.is_absolute() or '$' in str(path):
            raise SandboxUnavailable(f'{POLICY_FILE}: {key} path {value!r} is not absolute')
        out.append(Path(os.path.normpath(path)))
    return tuple(out)


def load_policy(home) -> SandboxPolicy | None:
    """The profile's policy, read now (never cached), or None when absent or not enabled."""
    home = Path(str(home))
    if not home.is_absolute():
        return None
    try:
        text = (home / POLICY_FILE).read_text(encoding='utf-8')
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise SandboxUnavailable(f'{POLICY_FILE} unreadable: {exc.strerror}') from exc
    try:
        raw = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise SandboxUnavailable(f'{POLICY_FILE} is not valid YAML') from exc
    if not isinstance(raw, dict):
        raise SandboxUnavailable(f'{POLICY_FILE} must be a mapping')
    if raw.get('enabled') is not True:
        return None
    policy = SandboxPolicy(home=home, ro=_paths(raw, 'ro'), rw=_paths(raw, 'rw'), hidden=_paths(raw, 'hidden'))
    for path in policy.rw:
        if path.name in CREDENTIAL_NAMES:
            raise SandboxUnavailable(f'{POLICY_FILE}: credential file {path} may not be bound read-write')
    return policy


def _under(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def hidden_paths(policy: SandboxPolicy, root: Path) -> list[Path]:
    home = policy.home
    hidden = [root / 'profiles']
    if home != root:
        hidden += [root / name for name in ROOT_PROFILE_DATA]
    hidden += list(policy.hidden)
    return hidden


def build_argv(policy: SandboxPolicy, inner: list, *, root: Path, required: list, cwd: Path,
               bwrap: str | None = None) -> list:
    """The ``bwrap`` argv that runs *inner* inside *policy*'s boundary. *required* are paths the
    worker cannot run without (code, interpreter, control socket); a hidden path covering one of
    them, or the profile's own home, is a policy error rather than a worker that cannot start."""
    bwrap = bwrap or shutil.which('bwrap')
    if not bwrap:
        raise SandboxUnavailable('bwrap is not installed; sandbox.enabled refuses to run the worker unsandboxed')
    home = policy.home
    hidden = hidden_paths(policy, root)
    for path in policy.hidden:
        for need in [home, *required]:
            if _under(Path(need), path):
                raise SandboxUnavailable(f'{POLICY_FILE}: hidden {path} covers required {need}')
    argv = [bwrap, '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp']
    # Parents before children, so a deeper mount wins: the default profile's home is the install
    # root, and its rw bind must not re-expose the hidden ``profiles`` beneath it.
    mounts = [(path, 'hidden') for path in hidden] + [(path, 'ro') for path in policy.ro]
    mounts += [(home, 'rw')] + [(path, 'rw') for path in policy.rw]
    for path, kind in sorted(mounts, key=lambda m: len(m[0].parts)):
        if kind == 'hidden' and path.is_dir():
            argv += ['--tmpfs', str(path)]
        elif kind == 'hidden' and path.exists():
            argv += ['--ro-bind', '/dev/null', str(path)]
        elif path.exists():
            argv += ['--ro-bind' if kind == 'ro' else '--bind', str(path), str(path)]
    for name in sorted(CREDENTIAL_NAMES):  # after every rw bind: credentials stay read-only
        cred = home / name
        if cred.exists():
            argv += ['--ro-bind', str(cred), str(cred)]
    for need in required:
        need = Path(need)
        if need.exists() and (_under(need, Path('/tmp')) or any(_under(need, h) for h in hidden)):
            argv += ['--bind' if need.is_socket() else '--ro-bind', str(need), str(need)]
    argv += ['--unshare-pid', '--die-with-parent', '--new-session', '--chdir', str(cwd), '--']
    return argv + list(inner)


def notice(policy: SandboxPolicy, root: Path) -> str:
    """The system-context block naming what the worker cannot see. Without it a sandboxed agent read
    an empty listing as the answer (A19: 2/2 silent wrong counts); with it, 0 silent fails."""
    lines = '\n'.join(f'- {p}' for p in hidden_paths(policy, root))
    return ('## SANDBOX BOUNDARY\n'
            f'This profile runs inside a filesystem sandbox. These paths are hidden (empty or absent to you):\n'
            f'{lines}\n- every other Hermes profile under {root / "profiles"} except your own home {policy.home}\n'
            "Your own .env and auth.json are read-only. Rule: an empty listing or a zero count under a hidden "
            'path is NOT an answer. Report the task as blocked by the sandbox and name the path.')


def wrap_worker(policy: SandboxPolicy | None, inner: list, env: dict | None, cwd) -> tuple[list, dict | None]:
    """``(argv, env)`` for one managed-worker launch: unchanged unless the profile enabled a boundary."""
    if policy is None:
        return inner, env
    from hermes_constants import get_default_hermes_root
    from gateway.control_socket import resolve_client_socket_path
    root = Path(get_default_hermes_root())
    sockets = {resolve_client_socket_path(root), resolve_client_socket_path(policy.home)} - {None}
    required = [Path(cwd), Path(sys.prefix), Path(sys.base_prefix), Path(sys.executable).parent, *sockets]
    argv = build_argv(policy, inner, root=root, required=required, cwd=Path(cwd))
    env = dict(os.environ if env is None else env)
    env[NOTICE_ENV] = notice(policy, root)
    env[PID_NS_ENV] = '1'
    return argv, env


def with_notice(prompt):
    """The worker's ephemeral system prompt plus the boundary notice its owner passed, if any."""
    block = os.environ.get(NOTICE_ENV, '').strip()
    if not block:
        return prompt
    return f'{prompt}\n\n{block}' if prompt else block


def accept_owner_pid(pid) -> bool:
    """Worker side: whether the bootstrap's ``scope.pid`` names this process. In its own pid namespace
    the worker cannot see its host pid; the owner proved the mapping (``NSpid``) before it reserved,
    so the scope's pid is adopted as this process's owner-visible pid."""
    global _host_pid
    if pid == os.getpid():
        return True
    if os.environ.get(PID_NS_ENV) == '1' and type(pid) is int and pid > 0:
        _host_pid = pid
        return True
    return False


def owner_visible_pid() -> int:
    """This process's pid as its owner and the ledger know it (the host pid for a sandboxed worker)."""
    return _host_pid or os.getpid()
