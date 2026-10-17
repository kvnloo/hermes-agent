from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import stat
import sys
import time

import pytest


CAPTURE_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/dev/capture-ui-tsp.sh"
SOURCE_ROOT = CAPTURE_SCRIPT.parents[2]

_FIXTURE_SUPERVISORS: dict[Path, subprocess.Popen] = {}


def _png_chunk(chunk_type, payload):
    import struct
    import zlib

    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xffffffff)
    )


PNG = (
    b"\x89PNG\r\n\x1a\n"
    + _png_chunk(b"IHDR", bytes.fromhex("00000001000000010806000000"))
    + _png_chunk(b"IDAT", bytes.fromhex("7801010500faff000000000000050001"))
    + _png_chunk(b"IEND", b"")
)


def _capture_fixture(tmp_path, *, current=False, running=True, create_shot=True, start_owner=True):
    real_node = shutil.which("node")
    if real_node is None:
        pytest.skip("Node is required to exercise product receipts")
    repo = tmp_path / "repo"
    script = repo / "scripts/dev/capture-ui-tsp.sh"
    script.parent.mkdir(parents=True)
    (repo / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    shutil.copy2(CAPTURE_SCRIPT, script)
    shutil.copy2(SOURCE_ROOT / "scripts/dev/capture-ui-tsp-owner.py", script.parent / "capture-ui-tsp-owner.py")
    build_scripts = repo / "scripts/build"
    build_scripts.mkdir(parents=True)
    for name in ("freshness.mjs", "frontend-common.mjs"):
        shutil.copy2(SOURCE_ROOT / "scripts/build" / name, build_scripts / name)
    (build_scripts / "tsp.mjs").touch()
    ui_tsp = repo / "ui-tsp"
    (ui_tsp / "src").mkdir(parents=True)
    (ui_tsp / "scripts").mkdir()
    (ui_tsp / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    (ui_tsp / "tsconfig.json").write_text("{}", encoding="utf-8")
    (ui_tsp / "src/entry.ts").write_text("export const product = 'original';", encoding="utf-8")
    (ui_tsp / "scripts/build.mjs").write_text("export const compiler = true;", encoding="utf-8")
    dist = ui_tsp / "dist"
    dist.mkdir()
    (dist / "entry.js").write_text("stale product", encoding="utf-8")
    recorder = repo / "record-tsp-product.mjs"
    recorder.write_text(
        "\n".join([
            "import { buildInputs, recordProduct } from './scripts/build/freshness.mjs';",
            "import { resolve } from 'node:path';",
            "const source = process.env.TSP_CAPTURE_ROOT;",
            "const out = resolve(source, 'ui-tsp/dist');",
            "recordProduct({ source, product: 'tsp', out, inputs: buildInputs(source, 'tsp') });",
        ]) + "\n",
        encoding="utf-8")
    if current:
        subprocess.run(
            [real_node, str(recorder)],
            env={**os.environ, "TSP_CAPTURE_ROOT": str(repo)},
            check=True, capture_output=True, text=True)

    iso = tmp_path / "isolated Tern"
    iso.mkdir()

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    node = bin_dir / "node"
    node.write_text(
        f"#!{sys.executable}\n"
        "from pathlib import Path\n"
        "import os, subprocess, sys\n"
        "root = Path(os.environ['TSP_CAPTURE_ROOT'])\n"
        "dist = root / 'ui-tsp/dist'\n"
        "event = root / 'build-events'\n"
        "name = Path(sys.argv[1]).name\n"
        "if name == 'freshness.mjs':\n"
        "    with event.open('a', encoding='utf-8') as log: log.write('receipt\\n')\n"
        "    result = subprocess.run([os.environ['REAL_NODE'], *sys.argv[1:]], check=False)\n"
        "    raise SystemExit(result.returncode)\n"
        "elif name == 'tsp.mjs':\n"
        "    if os.environ.get('BUILD_FAIL') == 'true':\n"
        "        raise SystemExit(23)\n"
        "    dist.mkdir(parents=True, exist_ok=True)\n"
        "    (dist / 'entry.js').write_text('rebuilt product', encoding='utf-8')\n"
        "    subprocess.run([os.environ['REAL_NODE'], str(root / 'record-tsp-product.mjs')], check=True)\n"
        "    with event.open('a', encoding='utf-8') as log: log.write('build\\n')\n"
        "else:\n"
        "    raise SystemExit(f'unexpected node script: {sys.argv[1]}')\n",
        encoding="utf-8")
    node.chmod(0o755)

    tern = bin_dir / "tern"
    tern.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, socket, sys\n"
        "args = sys.argv[1:]\n"
        "iso = pathlib.Path(os.environ['TSP_ISO_DIR']).resolve()\n"
        "def track_process():\n"
        "    raw = pathlib.Path('/proc/self/stat').read_text(encoding='utf-8')\n"
        "    start_time = int(raw[raw.rfind(')') + 2:].split()[19])\n"
        "    with (iso / '.fixture-processes').open('a', encoding='utf-8') as log:\n"
        "        log.write(f'{os.getpid()} {start_time}\\n')\n"
        "if args[:1] == ['--control']:\n"
        "    control = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
        "    control.bind(args[args.index('--control') + 1])\n"
        "    control.listen(8)\n"
        "    track_process()\n"
        "    while True:\n"
        "        connection, _ = control.accept()\n"
        "        with connection:\n"
        "            if connection.recv(64) == b'__fixture_shutdown__':\n"
        "                raise SystemExit(0)\n"
        "if args[:1] == ['--fixture-native']:\n"
        "    daemon = pathlib.Path(args[1])\n"
        "    port_file = pathlib.Path(args[2])\n"
        "    daemon.parent.mkdir(parents=True, exist_ok=True)\n"
        "    daemon_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n"
        "    daemon_socket.bind(str(daemon))\n"
        "    os.chmod(daemon, 0o600)\n"
        "    daemon_socket.listen(1)\n"
        "    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
        "    listener.bind(('127.0.0.1', 0))\n"
        "    listener.listen(8)\n"
        "    port_file.write_text(str(listener.getsockname()[1]), encoding='utf-8')\n"
        "    while True:\n"
        "        connection, _ = listener.accept()\n"
        "        with connection:\n"
        "            payload = connection.recv(4096)\n"
        "            connection.sendall(payload)\n"
        "action = args[3]\n"
        "if os.environ.get('TSP_REUSE_TERN_PID'):\n"
        "    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:\n"
        "        probe.connect(args[2])\n"
        "        probe.sendall(b'ownership-probe')\n"
        "        if probe.recv(64) != b'ownership-probe':\n"
        "            raise SystemExit('control relay did not preserve its TCP stream')\n"
        "def gate():\n"
        "    applies_raw = os.environ.get('GATE_APPLIES', 'false')\n"
        "    applies = True if applies_raw == 'true' else False if applies_raw == 'false' else None\n"
        "    error_raw = os.environ.get('GATE_ERROR', 'null')\n"
        "    error = None if error_raw == 'null' else error_raw\n"
        "    phase = os.environ.get('GATE_PHASE', 'off')\n"
        "    if (iso / 'shot-captured').exists() and os.environ.get('CLOSE_GATE_AFTER_SHOT') == 'true':\n"
        "        phase = 'waiting'\n"
        "    state = {'applies': applies, 'phase': phase, 'error': error, 'signed_in': os.environ.get('GATE_SIGNED_IN') == 'true'}\n"
        "    if os.environ.get('GATE_ERROR_MISSING') == 'true':\n"
        "        del state['error']\n"
        "    return state\n"
        "if action == 'run':\n"
        "    with (iso / 'tern-actions').open('a', encoding='utf-8') as log: log.write('run\\n')\n"
        "    ok = os.environ.get('RUN_OK', 'true') == 'true'\n"
        "    if ok:\n"
        "        run_script = pathlib.Path(args[4])\n"
        "        line = next(line for line in run_script.read_text(encoding='utf-8').splitlines() if line.startswith('exec node '))\n"
        "        entry = line[len(\"exec node '\"):-1]\n"
        "        (iso / 'tern-owner').write_text('node ' + entry, encoding='utf-8')\n"
        "    print(json.dumps({'ok': ok}))\n"
        "elif action == 'state':\n"
        "    owner_file = iso / 'tern-owner'\n"
        "    if owner_file.exists() and os.environ['FRONTEND_RUNNING'] == 'true':\n"
        "        running = owner_file.read_text(encoding='utf-8')\n"
        "        busy = True\n"
        "        if os.environ.get('CHANGE_OWNER_AFTER_RUN') == 'true' or ((iso / 'shot-captured').exists() and os.environ.get('CHANGE_OWNER_AFTER_SHOT') == 'true'):\n"
        "            running = 'node unrelated-frontend.js'\n"
        "    else:\n"
        "        initial_running = os.environ.get('INITIAL_RUNNING', '')\n"
        "        running = initial_running if initial_running else None\n"
        "        busy = bool(initial_running)\n"
        "    focus_id = int(os.environ.get('FOCUSED_ID', '7'))\n"
        "    if owner_file.exists() and os.environ['FRONTEND_RUNNING'] == 'true' and os.environ.get('CHANGE_FOCUS_AFTER_RUN') == 'true':\n"
        "        focus_id += 1\n"
        "    cwd = os.environ.get('FOCUSED_CWD', os.environ['TSP_CAPTURE_ROOT'])\n"
        "    label = os.environ.get('FOCUSED_LABEL', 'hermes')\n"
        "    focused = {'id': focus_id, 'label': label, 'cwd': cwd, 'running': running, 'busy': busy}\n"
        "    if os.environ.get('MALFORMED_RUNNING') == 'missing':\n"
        "        del focused['running']\n"
        "    elif os.environ.get('MALFORMED_RUNNING') == 'empty':\n"
        "        focused['running'] = ''\n"
        "    print(json.dumps({'ok': True, 'focused': focused, 'gate': gate()}))\n"
        "elif action == 'shot':\n"
        "    name = args[4]\n"
        "    with (iso / 'tern-actions').open('a', encoding='utf-8') as log: log.write('shot\\n')\n"
        "    with (iso / 'tern-events').open('a', encoding='utf-8') as log: log.write(name + '\\n')\n"
        "    if os.environ['CREATE_SHOT'] == 'true':\n"
        "        target = iso / 'target/shots/tern/live' / (name + '.png')\n"
        "        target.parent.mkdir(parents=True, exist_ok=True)\n"
        "        target.write_bytes(bytes.fromhex(os.environ['SHOT_BYTES_HEX']))\n"
        "    (iso / 'shot-captured').touch()\n"
        "    print(json.dumps({'ok': os.environ.get('SHOT_OK', 'true') == 'true'}))\n"
        "else:\n"
        "    raise SystemExit(f'unexpected tern action: {action}')\n",
        encoding="utf-8")
    tern.chmod(0o755)

    sway = tmp_path / "sway"
    sway.write_text(
        f"#!{sys.executable}\n"
        "import os, pathlib, shlex, subprocess, sys, time\n"
        "config = pathlib.Path(sys.argv[sys.argv.index('--config') + 1])\n"
        "iso = pathlib.Path(os.environ['TSP_ISO_DIR'])\n"
        "parent_pid = os.getppid()\n"
        "raw = pathlib.Path('/proc/self/stat').read_text(encoding='utf-8')\n"
        "start_time = int(raw[raw.rfind(')') + 2:].split()[19])\n"
        "with (iso / '.fixture-processes').open('a', encoding='utf-8') as log:\n"
        "    log.write(f'{os.getpid()} {start_time}\\n')\n"
        "if os.environ.get('TSP_REUSE_TERN_PID'):\n"
        "    (iso / 'sway-started').touch()\n"
        "command = shlex.split(next(line[5:] for line in config.read_text(encoding='utf-8').splitlines() if line.startswith('exec ')))\n"
        "child = subprocess.Popen(command)\n"
        "while child.poll() is None:\n"
        "    if (iso / '.fixture-shutdown').exists() or os.getppid() != parent_pid:\n"
        "        child.terminate()\n"
        "        break\n"
        "    time.sleep(0.01)\n"
        "raise SystemExit(child.wait())\n",
        encoding="utf-8")
    sway.chmod(0o755)
    env = {
        **os.environ,
        "PATH": os.pathsep.join((str(bin_dir), os.environ["PATH"])),
        "TSP_ISO_DIR": str(iso),
        "TSP_SHOT_DIR": str(iso / "shots"),
        "TSP_CAPTURE_ROOT": str(repo),
        "REAL_NODE": real_node,
        "TSP_READY_TIMEOUT": "1",
        "HERMES_PYTHON": sys.executable,
        "SWAY_BIN": str(sway),
        "SWAY_LIB": str(tmp_path / "sway-lib"),
        "FRONTEND_RUNNING": "true" if running else "false",
        "SHOT_BYTES_HEX": PNG.hex(),
        "CREATE_SHOT": "true" if create_shot else "false",
    }
    if start_owner:
        run_dir = iso / "run"
        run_dir.mkdir(mode=0o700)
        os.chmod(run_dir, 0o700)
        config_dir = iso / "sway"
        config_dir.mkdir()
        config = config_dir / "config"
        control_path = iso / "ctl.sock"
        config.write_text(
            f"""output * resolution 984x713
exec tern --control "{control_path}" "{iso}"
            """,
            encoding="utf-8")
        fixture_env = {
            **env,
            "XDG_RUNTIME_DIR": str(run_dir),
            "TERN_CONFIG_DIR": str(iso),
            "TERN_DAEMON_SOCKET": str(iso / "daemon.sock"),
        }
        supervisor = subprocess.Popen(
            [str(sway), "--config", str(config)],
            cwd=tmp_path,
            env=fixture_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _FIXTURE_SUPERVISORS[iso.resolve()] = supervisor
        try:
            process_file = iso / ".fixture-processes"
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if supervisor.poll() is not None:
                    raise AssertionError("fixture Sway supervisor exited before owning Tern")
                if control_path.exists() and process_file.exists() and len(process_file.read_text(encoding="utf-8").splitlines()) == 2:
                    break
                time.sleep(0.01)
            else:
                raise AssertionError("fixture Sway supervisor did not establish its owned Tern socket")
            owner_helper = script.parent / "capture-ui-tsp-owner.py"
            recorded = subprocess.run(
                [
                    sys.executable, str(owner_helper), "record",
                    "--socket", str(control_path),
                    "--record", str(run_dir / "control-owner.json"),
                    "--iso", str(iso),
                    "--runtime", str(run_dir),
                    "--daemon", str(iso / "daemon.sock"),
                    "--config", str(config),
                    "--supervisor-pid", str(supervisor.pid),
                ],
                cwd=tmp_path,
                capture_output=True,
                text=True,
            )
            if recorded.returncode != 0:
                raise AssertionError(f"fixture owner attestation failed: {recorded.stderr}")
        except Exception:
            _stop_fixture_processes(iso)
            raise
    return script, repo, iso, env

def _proc_start_time(pid: int) -> int | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return None
    fields = raw[raw.rfind(")") + 2 :].split()
    return int(fields[19]) if len(fields) > 19 else None

def _proc_identity(pid: int) -> dict[str, object]:
    proc = Path(f"/proc/{pid}")
    status = (proc / "status").read_text(encoding="utf-8")
    uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
    cmdline = [os.fsdecode(part) for part in (proc / "cmdline").read_bytes().split(b"\0") if part]
    return {
        "pid": pid,
        "start_time": _proc_start_time(pid),
        "uid": int(uid_line.split()[2]),
        "exe": os.readlink(proc / "exe"),
        "cmdline": cmdline,
    }


def _unix_socket_identity(path: Path) -> dict[str, object]:
    socket_path = str(path.absolute())
    info = os.lstat(socket_path)
    for line in Path("/proc/net/unix").read_text(encoding="utf-8").splitlines()[1:]:
        fields = line.split(maxsplit=7)
        if len(fields) == 8 and fields[7] == socket_path:
            return {
                "path": socket_path,
                "device": info.st_dev,
                "inode": info.st_ino,
                "uid": info.st_uid,
                "mode": stat.S_IMODE(info.st_mode),
                "kernel_inode": int(fields[6]),
            }
    raise AssertionError(f"no live /proc/net/unix entry for {socket_path}")


def _stop_fixture_processes(iso: Path) -> None:
    supervisor = _FIXTURE_SUPERVISORS.pop(iso.resolve(), None)
    if supervisor is None:
        return
    (iso / ".fixture-shutdown").touch()
    supervisor.wait(timeout=2)


def _run_capture(script: Path, tmp_path: Path, env: dict[str, str], *, stop_fixture=True):
    try:
        return subprocess.run(
            ["sh", str(script)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    finally:
        if stop_fixture:
            _stop_fixture_processes(Path(env["TSP_ISO_DIR"]))

def _request_fixture_shutdown(control_path: Path) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as control:
        control.settimeout(1)
        control.connect(str(control_path))
        control.sendall(b"__fixture_shutdown__")


def _wait_for_fixture_exit(iso: Path) -> None:
    process_file = iso / ".fixture-processes"
    if not process_file.exists():
        return
    identities = [tuple(map(int, line.split())) for line in process_file.read_text(encoding="utf-8").splitlines()]
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if all(_proc_start_time(pid) != start_time for pid, start_time in identities):
            return
        time.sleep(0.01)
    raise AssertionError("fixture Sway/Tern processes did not exit after their owner shell ended")


def _run_capture_with_owned_startup(script: Path, tmp_path: Path, env: dict[str, str]):
    iso = Path(env["TSP_ISO_DIR"])
    finished = iso / ".fixture-capture-finished"
    runner_env = {**env, "TSP_CAPTURE_FINISHED": str(finished)}
    with script.open("a", encoding="utf-8") as handle:
        handle.write(chr(10) + ': > "$TSP_CAPTURE_FINISHED"' + chr(10) + "wait" + chr(10))
    process = subprocess.Popen(
        ["sh", str(script)],
        cwd=tmp_path,
        env=runner_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 30
    while not finished.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    if not finished.exists():
        (iso / ".fixture-shutdown").touch()
        stdout, stderr = process.communicate(timeout=3)
        _wait_for_fixture_exit(iso)
        result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
        return result, None
    try:
        socket_identity = _unix_socket_identity(iso / "ctl.sock")
    except Exception:
        try:
            _request_fixture_shutdown(iso / "ctl.sock")
        except OSError:
            (iso / ".fixture-shutdown").touch()
        process.communicate(timeout=3)
        raise
    try:
        _request_fixture_shutdown(iso / "ctl.sock")
    except OSError:
        (iso / ".fixture-shutdown").touch()
    stdout, stderr = process.communicate(timeout=3)
    result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)
    return result, socket_identity

@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_accepts_an_actually_owned_fixture_process(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True, start_owner=False)
    result, socket_identity = _run_capture_with_owned_startup(script, tmp_path, env)
    process_identities = [
        tuple(map(int, line.split()))
        for line in (iso / ".fixture-processes").read_text(encoding="utf-8").splitlines()
    ]
    record = json.loads((iso / "run/control-owner.json").read_text(encoding="utf-8"))

    assert result.returncode == 0, result.stderr
    assert socket_identity == record["socket"]
    assert record["supervisor"]["pid"] == process_identities[0][0]
    assert (record["owner"]["pid"], record["owner"]["start_time"]) == process_identities[1]
    assert record["socket"]["path"] == str(iso / "ctl.sock")
    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run", "shot"]
    assert (iso / "shots/ui-tsp-hello.png").is_file()
    assert record["mode"] == "isolated"




@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_reuses_persisted_identity_for_live_owned_socket(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    try:
        first = _run_capture(script, tmp_path, env, stop_fixture=False)
        assert first.returncode == 0, first.stderr
        (iso / "tern-actions").unlink()
        (iso / "tern-events").unlink()
        (iso / "tern-owner").unlink()
        (iso / "shots/ui-tsp-hello.png").unlink()

        result = _run_capture(script, tmp_path, env, stop_fixture=False)
        assert result.returncode == 0, result.stderr
        assert len((iso / ".fixture-processes").read_text(encoding="utf-8").splitlines()) == 2
    finally:
        _stop_fixture_processes(iso)

    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run", "shot"]

@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_rejects_preexisting_socket_without_owner_record(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True, start_owner=False)
    control = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    control.bind(str(iso / "ctl.sock"))
    control.listen(1)
    os.chmod(iso / "ctl.sock", 0o600)
    try:
        result = _run_capture(script, tmp_path, env)
    finally:
        control.close()

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "tern-events").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_rejects_forged_owner_record_for_foreign_socket(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True, start_owner=False)
    run_dir = iso / "run"
    run_dir.mkdir(mode=0o700)
    os.chmod(run_dir, 0o700)
    control = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    control_path = iso / "ctl.sock"
    control.bind(str(control_path))
    control.listen(1)
    os.chmod(control_path, 0o600)
    identity = _proc_identity(os.getpid())
    record = {
        "schema": 1,
        "mode": "isolated",
        "paths": {
            "iso": str(iso),
            "runtime": str(iso / "run"),
            "daemon": str(iso / "daemon.sock"),
            "config": str(iso / "sway/config"),
        },
        "socket": _unix_socket_identity(control_path),
        "owner": identity,
        "supervisor": identity,
    }
    record_path = run_dir / "control-owner.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    os.chmod(record_path, 0o600)
    try:
        result = _run_capture(script, tmp_path, env)
    finally:
        control.close()

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "tern-events").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_rejects_symlink_control_socket_before_native_mutation(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True, start_owner=False)
    foreign = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    foreign_path = iso / "foreign.sock"
    foreign.bind(str(foreign_path))
    foreign.listen(1)
    os.chmod(foreign_path, 0o600)
    (iso / "ctl.sock").symlink_to(foreign_path)
    try:
        result = _run_capture(script, tmp_path, env)
    finally:
        foreign.close()

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "tern-events").exists()


@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_rejects_stale_owner_identity_before_native_mutation(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    first = _run_capture(script, tmp_path, env)
    assert first.returncode == 0, first.stderr
    (iso / "tern-actions").unlink()
    (iso / "tern-events").unlink()
    (iso / "shots/ui-tsp-hello.png").unlink()

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "tern-events").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_rejects_pid_reuse_with_changed_start_identity(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    try:
        first = _run_capture(script, tmp_path, env, stop_fixture=False)
        assert first.returncode == 0, first.stderr
        record_path = iso / "run/control-owner.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["owner"]["start_time"] += 1
        record_path.write_text(json.dumps(record), encoding="utf-8")
        os.chmod(record_path, 0o600)
        (iso / "tern-actions").unlink()
        (iso / "tern-events").unlink()
        (iso / "shots/ui-tsp-hello.png").unlink()

        result = _run_capture(script, tmp_path, env, stop_fixture=False)
    finally:
        _stop_fixture_processes(iso)

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "tern-events").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
@pytest.mark.skipif(not Path("/proc/net/unix").exists(), reason="Linux /proc is required for socket ownership")
def test_capture_reuses_owned_tern_through_private_local_tcp_relay(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True, start_owner=False)
    daemon = tmp_path / "existing Tern daemon.sock"
    runtime = tmp_path / "existing Tern runtime"
    runtime.mkdir(mode=0o700)
    os.chmod(runtime, 0o700)
    run_dir = iso / "run"
    run_dir.mkdir(mode=0o700)
    os.chmod(run_dir, 0o700)
    port_file = tmp_path / "existing-tern-port"
    tern = Path(env["PATH"].split(os.pathsep)[0]) / "tern"
    native_env = {
        **env,
        "TERN_DAEMON_SOCKET": str(daemon),
        "XDG_RUNTIME_DIR": str(runtime),
    }
    native = subprocess.Popen(
        [str(tern), "--fixture-native", str(daemon), str(port_file)],
        cwd=tmp_path,
        env=native_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    relay = None
    try:
        deadline = time.monotonic() + 2
        while not port_file.exists() and native.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert port_file.exists(), "fixture Tern did not publish its owned loopback port"
        control_port = port_file.read_text(encoding="utf-8")
        owner_helper = Path(env["TSP_CAPTURE_ROOT"]) / "scripts/dev/capture-ui-tsp-owner.py"
        relay = subprocess.Popen(
            [
                sys.executable, str(owner_helper), "serve-relay",
                "--socket", str(iso / "ctl.sock"),
                "--record", str(run_dir / "control-owner.json"),
                "--iso", str(iso),
                "--native-pid", str(native.pid),
                "--native-port", control_port,
                "--native-daemon", str(daemon),
                "--native-runtime", str(runtime),
            ],
            cwd=tmp_path,
            env=native_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 2
        while (
            not (iso / "ctl.sock").exists()
            or not (run_dir / "control-owner.json").exists()
        ) and relay.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert relay.poll() is None, "owned relay exited before reuse"
        assert (iso / "ctl.sock").exists() and (run_dir / "control-owner.json").exists()
        env["TSP_REUSE_TERN_PID"] = str(native.pid)
        env["TSP_REUSE_TERN_CONTROL_PORT"] = control_port
        env["TSP_REUSE_TERN_DAEMON_SOCKET"] = str(daemon)
        env["TSP_REUSE_TERN_RUNTIME_DIR"] = str(runtime)
        env["TSP_EXPECTED_PANE_ID"] = "7"

        result = _run_capture(script, tmp_path, env)

        assert result.returncode == 0, result.stderr
        assert native.poll() is None
        assert not (iso / "sway-started").exists()
        assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run", "shot"]
    finally:
        if relay is not None:
            relay.terminate()
            relay.wait(timeout=2)
        native.terminate()
        native.wait(timeout=2)


@pytest.mark.platforms("posix")
def test_capture_never_launches_stale_product_when_rebuild_fails(tmp_path):
    script, repo, iso, env = _capture_fixture(tmp_path, current=True)
    (repo / "ui-tsp/src/entry.ts").write_text("export const product = 'changed';", encoding="utf-8")
    env["BUILD_FAIL"] = "true"

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("INITIAL_RUNNING", "node old-frontend.js"),
        ("FOCUSED_CWD", "/tmp/not-the-checkout"),
        ("FOCUSED_LABEL", "other"),
    ],
)
def test_capture_refuses_busy_or_unowned_target_before_run(tmp_path, field, value):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env[field] = value

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("MALFORMED_RUNNING", "missing"),
        ("MALFORMED_RUNNING", "empty"),
        ("GATE_ERROR_MISSING", "true"),
    ],
)
def test_capture_refuses_malformed_state_before_native_input(tmp_path, field, value):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env[field] = value

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("GATE_PHASE", "waiting"),
        ("GATE_APPLIES", "true"),
        ("GATE_ERROR", "account unavailable"),
        ("GATE_APPLIES", "unknown"),
    ],
)
def test_capture_refuses_unknown_or_closed_gate_before_native_input(tmp_path, field, value):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env[field] = value

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "tern-actions").exists()


@pytest.mark.platforms("posix")
def test_capture_rejects_stopped_frontend_even_when_historical_png_exists(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True, running=False)
    historical = iso / "target/shots/tern/live/ui-tsp-hello.png"
    historical.parent.mkdir(parents=True)
    historical.write_bytes(PNG)

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "shots/ui-tsp-hello.png").exists()
    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run"]
    assert not (iso / "tern-events").exists()


@pytest.mark.platforms("posix")
def test_capture_rejects_changed_frontend_owner_before_screenshot(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env["CHANGE_OWNER_AFTER_RUN"] = "true"

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run"]
    assert not (iso / "tern-events").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()

@pytest.mark.platforms("posix")
def test_capture_rejects_focused_pane_change_after_launch(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env["CHANGE_FOCUS_AFTER_RUN"] = "true"

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run"]
    assert not (iso / "tern-events").exists()
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
def test_capture_rejects_changed_owner_after_screenshot(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env["CHANGE_OWNER_AFTER_SHOT"] = "true"

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run", "shot"]
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
def test_capture_rejects_gate_closure_after_screenshot(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env["CLOSE_GATE_AFTER_SHOT"] = "true"

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
def test_capture_requires_run_ok_receipt(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env["RUN_OK"] = "false"

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run"]
    assert not (iso / "tern-events").exists()


@pytest.mark.platforms("posix")
def test_capture_requires_shot_ok_receipt(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env["SHOT_OK"] = "false"

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "shots/ui-tsp-hello.png").exists()


@pytest.mark.platforms("posix")
def test_capture_rejects_missing_new_png_instead_of_copying_historical_image(tmp_path):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True, create_shot=False)
    historical = iso / "target/shots/tern/live/ui-tsp-hello.png"
    historical.parent.mkdir(parents=True)
    historical.write_bytes(PNG)

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert not (iso / "shots/ui-tsp-hello.png").exists()


def _png_with_bad_crc():
    damaged = bytearray(PNG)
    ihdr_start = damaged.index(b"IHDR")
    damaged[ihdr_start + 4 + 13] ^= 1
    return bytes(damaged)


def _png_with_invalid_deflate():
    import struct
    import zlib

    damaged = bytearray(PNG)
    idat_start = damaged.index(b"IDAT")
    length = struct.unpack_from(">I", damaged, idat_start - 4)[0]
    data_start = idat_start + 4
    damaged[data_start] ^= 0xff
    crc_start = data_start + length
    crc = zlib.crc32(damaged[idat_start:crc_start]) & 0xffffffff
    struct.pack_into(">I", damaged, crc_start, crc)
    return bytes(damaged)


@pytest.mark.platforms("posix")
@pytest.mark.parametrize(
    "shot_bytes",
    [
        pytest.param(PNG[:8], id="signature-only"),
        pytest.param(PNG[:-1], id="truncated"),
        pytest.param(_png_with_bad_crc(), id="bad-crc"),
        pytest.param(_png_with_invalid_deflate(), id="invalid-compressed-data"),
    ],
)
def test_capture_rejects_incomplete_or_corrupt_png(tmp_path, shot_bytes):
    script, _repo, iso, env = _capture_fixture(tmp_path, current=True)
    env["SHOT_BYTES_HEX"] = shot_bytes.hex()

    result = _run_capture(script, tmp_path, env)

    assert result.returncode != 0
    assert (iso / "tern-actions").read_text(encoding="utf-8").splitlines() == ["run", "shot"]
    assert not (iso / "shots/ui-tsp-hello.png").exists()
