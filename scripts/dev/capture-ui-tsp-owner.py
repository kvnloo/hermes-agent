#!/usr/bin/env python3
"""Authenticate the private Tern control endpoint against live Linux process facts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import selectors
import socket
import stat
import sys
import tempfile


class OwnerError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise OwnerError(message)


def absolute(path: str | Path) -> str:
    return os.path.abspath(os.fspath(path))


def read_process(pid: int) -> dict[str, object]:
    require(pid > 0, "PID must be positive")
    proc = Path("/proc") / str(pid)
    try:
        raw_stat = (proc / "stat").read_text(encoding="utf-8")
        close = raw_stat.rfind(")")
        require(close > 0, f"malformed /proc/{pid}/stat")
        fields = raw_stat[close + 2 :].split()
        require(len(fields) > 19, f"short /proc/{pid}/stat")
        require(fields[0] not in {"Z", "X"}, f"PID {pid} is not live")
        start_time = int(fields[19])
        parent_pid = int(fields[1])
        status = (proc / "status").read_text(encoding="utf-8")
        uid_line = next(line for line in status.splitlines() if line.startswith("Uid:"))
        uid = int(uid_line.split()[2])
        cmdline = [os.fsdecode(part) for part in (proc / "cmdline").read_bytes().split(b"\0") if part]
        require(cmdline, f"PID {pid} has no command line")
        exe = os.readlink(proc / "exe")
        environ = {}
        for item in (proc / "environ").read_bytes().split(b"\0"):
            if b"=" in item:
                key, value = item.split(b"=", 1)
                environ[os.fsdecode(key)] = os.fsdecode(value)
    except (OSError, StopIteration, ValueError, IndexError) as exc:
        raise OwnerError(f"cannot inspect live PID {pid}: {exc}") from exc
    return {
        "pid": pid,
        "start_time": start_time,
        "parent_pid": parent_pid,
        "uid": uid,
        "exe": exe,
        "cmdline": cmdline,
        "environ": environ,
    }


def identity(process: dict[str, object]) -> dict[str, object]:
    return {key: process[key] for key in ("pid", "start_time", "uid", "exe", "cmdline")}


def require_current_user(process: dict[str, object], what: str) -> None:
    require(process["uid"] == os.geteuid(), f"{what} is not owned by the current user")


def unix_socket(path: str) -> dict[str, object]:
    socket_path = absolute(path)
    try:
        parent = Path(socket_path).parent
        require(parent.resolve(strict=True) == parent, "control socket parent is not canonical")
        info = os.lstat(socket_path)
    except OSError as exc:
        raise OwnerError(f"cannot inspect control socket {socket_path}: {exc}") from exc
    require(not stat.S_ISLNK(info.st_mode), "control socket must not be a symlink")
    require(stat.S_ISSOCK(info.st_mode), "control path is not a Unix socket")
    require(info.st_uid == os.geteuid(), "control socket is not owned by the current user")
    require(stat.S_IMODE(info.st_mode) & 0o077 == 0, "control socket is not private")
    try:
        matches = []
        for line in Path("/proc/net/unix").read_text(encoding="utf-8").splitlines()[1:]:
            fields = line.split(maxsplit=7)
            if len(fields) != 8 or fields[7] != socket_path:
                continue
            socket_type = int(fields[4], 16)
            flags = int(fields[3], 16)
            inode = int(fields[6])
            if socket_type == 1 and flags & 0x10000:
                matches.append(inode)
    except (OSError, ValueError) as exc:
        raise OwnerError(f"cannot inspect Linux Unix socket table: {exc}") from exc
    require(len(matches) == 1, "control path does not identify exactly one live stream listener")
    return {
        "path": socket_path,
        "device": info.st_dev,
        "inode": info.st_ino,
        "uid": info.st_uid,
        "mode": stat.S_IMODE(info.st_mode),
        "kernel_inode": matches[0],
    }

def validate_control_directory(path: str) -> None:
    parent = Path(absolute(path)).parent
    try:
        require(parent.resolve(strict=True) == parent, "control socket directory is not canonical")
        info = os.lstat(parent)
    except OSError as exc:
        raise OwnerError(f"cannot inspect control socket directory: {exc}") from exc
    require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode), "control socket directory must be a real directory")
    require(info.st_uid == os.geteuid(), "control socket directory is not owned by the current user")
    require(stat.S_IMODE(info.st_mode) & 0o022 == 0, "control socket directory is writable by another user")


def control_socket(path: str) -> dict[str, object]:
    validate_control_directory(path)
    return unix_socket(path)


def socket_fd_owners(kernel_inode: int) -> set[int]:
    owners: set[int] = set()
    try:
        proc_entries = list(Path("/proc").iterdir())
    except OSError as exc:
        raise OwnerError(f"cannot enumerate /proc: {exc}") from exc
    target = f"socket:[{kernel_inode}]"
    for proc in proc_entries:
        if not proc.name.isdecimal():
            continue
        try:
            for fd in (proc / "fd").iterdir():
                try:
                    if os.readlink(fd) == target:
                        owners.add(int(proc.name))
                        break
                except OSError:
                    continue
        except OSError:
            continue
    return owners


def require_socket_owned_by(sock: dict[str, object], pid: int) -> None:
    owners = socket_fd_owners(int(sock["kernel_inode"]))
    require(owners == {pid}, f"control socket owner mismatch: expected only PID {pid}, found {sorted(owners)}")


def require_process_identity(actual: dict[str, object], recorded: object, what: str) -> None:
    require(isinstance(recorded, dict), f"missing {what} identity")
    require(identity(actual) == recorded, f"{what} PID identity changed or is stale")


def check_private_record_path(record_path: str, *, must_exist: bool) -> Path:
    path = Path(absolute(record_path))
    directory = path.parent
    try:
        directory_info = os.lstat(directory)
    except OSError as exc:
        raise OwnerError(f"cannot inspect private owner directory: {exc}") from exc
    require(stat.S_ISDIR(directory_info.st_mode) and not stat.S_ISLNK(directory_info.st_mode), "owner directory must be a real directory")
    require(directory_info.st_uid == os.geteuid(), "owner directory is not owned by the current user")
    require(stat.S_IMODE(directory_info.st_mode) & 0o077 == 0, "owner directory is not private")
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        require(not must_exist, "control owner record is absent")
        return path
    except OSError as exc:
        raise OwnerError(f"cannot inspect control owner record: {exc}") from exc
    require(not stat.S_ISLNK(info.st_mode), "control owner record must not be a symlink")
    require(stat.S_ISREG(info.st_mode), "control owner record is not a regular file")
    require(info.st_uid == os.geteuid(), "control owner record is not owned by the current user")
    require(stat.S_IMODE(info.st_mode) == 0o600, "control owner record must have mode 0600")
    return path


def write_record(path: Path, data: dict[str, object]) -> None:
    payload = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise OwnerError(f"cannot create private control owner record: {exc}") from exc
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def read_record(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OwnerError(f"cannot read control owner record: {exc}") from exc
    require(isinstance(value, dict) and value.get("schema") == 1, "malformed control owner record")
    return value


def validate_instance_process(
    process: dict[str, object], *, socket_path: str, iso: str, runtime: str, daemon: str
) -> None:
    require_current_user(process, "Tern process")
    argv = process["cmdline"]
    require(isinstance(argv, list), "malformed Tern command line")
    expected_args = ["--control", absolute(socket_path), absolute(iso)]
    require(any(argv[index : index + len(expected_args)] == expected_args for index in range(len(argv))), "socket owner is not the expected isolated Tern command")
    env = process["environ"]
    require(isinstance(env, dict), "malformed Tern environment")
    require(env.get("TERN_CONFIG_DIR") == absolute(iso), "Tern process uses a different config directory")
    require(env.get("TERN_DAEMON_SOCKET") == absolute(daemon), "Tern process uses a different daemon socket")
    require(env.get("XDG_RUNTIME_DIR") == absolute(runtime), "Tern process uses a different runtime directory")


def validate_supervisor(process: dict[str, object], config_path: str) -> None:
    require_current_user(process, "Sway supervisor")
    argv = process["cmdline"]
    is_sway = isinstance(argv, list) and bool(argv) and os.path.basename(argv[0]).lower() == "sway"
    if isinstance(argv, list) and len(argv) > 1:
        is_sway = is_sway or os.path.basename(argv[1]).lower() == "sway"
    require(is_sway, "owner supervisor is not Sway")
    expected = ["--config", absolute(config_path)]
    require(any(argv[index : index + len(expected)] == expected for index in range(len(argv))), "Sway supervisor uses a different config")


def require_descendant(pid: int, ancestor_pid: int) -> None:
    current = pid
    seen: set[int] = set()
    while current > 1 and current not in seen:
        require(current != ancestor_pid or pid != ancestor_pid, "Tern socket owner cannot be its own Sway supervisor")
        seen.add(current)
        if current == ancestor_pid:
            return
        process = read_process(current)
        current = int(process["parent_pid"])
    raise OwnerError("Tern socket owner is not descended from its recorded supervisor")


def validate_isolated(
    record: dict[str, object], *, sock_path: str, iso: str, runtime: str, daemon: str, config: str
) -> None:
    require(record.get("mode") == "isolated", "control owner mode is not isolated Tern")
    expected_paths = {"iso": absolute(iso), "runtime": absolute(runtime), "daemon": absolute(daemon), "config": absolute(config)}
    require(record.get("paths") == expected_paths, "control owner record names a different isolated instance")
    sock = control_socket(sock_path)
    require(record.get("socket") == sock, "control socket identity changed or is stale")
    owner_record = record.get("owner")
    require(isinstance(owner_record, dict), "missing Tern owner identity")
    owner = read_process(int(owner_record.get("pid", -1)))
    require_process_identity(owner, owner_record, "Tern owner")
    validate_instance_process(owner, socket_path=sock_path, iso=iso, runtime=runtime, daemon=daemon)
    require_socket_owned_by(sock, int(owner["pid"]))
    supervisor_record = record.get("supervisor")
    require(isinstance(supervisor_record, dict), "missing Sway supervisor identity")
    supervisor = read_process(int(supervisor_record.get("pid", -1)))
    require_process_identity(supervisor, supervisor_record, "Sway supervisor")
    validate_supervisor(supervisor, f"{iso}/sway/config")
    require_descendant(int(owner["pid"]), int(supervisor["pid"]))


def tcp_listener_inode(port: int, pid: int) -> int:
    require(1 <= port <= 65535, "local control TCP port is outside 1..65535")
    matches: set[int] = set()
    try:
        lines = Path("/proc/net/tcp").read_text(encoding="ascii").splitlines()[1:]
        for line in lines:
            fields = line.split()
            if len(fields) < 10:
                continue
            address, raw_port = fields[1].split(":", 1)
            if address != "0100007F" or int(raw_port, 16) != port or fields[3] != "0A":
                continue
            matches.add(int(fields[9]))
    except (OSError, ValueError) as exc:
        raise OwnerError(f"cannot inspect Linux TCP listener table: {exc}") from exc
    require(len(matches) == 1, f"127.0.0.1:{port} is not exactly one live TCP listener")
    inode = next(iter(matches))
    owners = socket_fd_owners(inode)
    require(owners == {pid}, f"TCP control listener owner mismatch: expected only PID {pid}, found {sorted(owners)}")
    return inode


def validate_native_target(pid: int, port: int, daemon: str, runtime: str) -> dict[str, object]:
    process = read_process(pid)
    require_current_user(process, "reused Tern process")
    env = process["environ"]
    require(isinstance(env, dict), "malformed reused Tern environment")
    require(env.get("TERN_DAEMON_SOCKET") == absolute(daemon), "reused Tern process has a different daemon socket")
    require(env.get("XDG_RUNTIME_DIR") == absolute(runtime), "reused Tern process has a different runtime directory")
    daemon_sock = unix_socket(daemon)
    daemon_owners = socket_fd_owners(int(daemon_sock["kernel_inode"]))
    require(len(daemon_owners) == 1, "reused Tern daemon socket has no unique process owner")
    daemon_pid = next(iter(daemon_owners))
    daemon_process = read_process(daemon_pid)
    require_current_user(daemon_process, "reused Tern daemon")
    if daemon_pid != pid:
        require_descendant(daemon_pid, pid)
    require(daemon_process["exe"] == process["exe"], "reused Tern daemon runs a different executable")
    daemon_env = daemon_process["environ"]
    require(isinstance(daemon_env, dict) and daemon_env.get("TERN_DAEMON_SOCKET") == absolute(daemon)
            and daemon_env.get("XDG_RUNTIME_DIR") == absolute(runtime),
            "reused Tern daemon uses a different socket or runtime directory")
    tcp_inode = tcp_listener_inode(port, pid)
    return {
        "identity": identity(process),
        "daemon_socket": daemon_sock,
        "daemon_identity": identity(daemon_process),
        "runtime": absolute(runtime),
        "tcp_port": port,
        "tcp_inode": tcp_inode,
    }


def expected_relay_argv(record: dict[str, object]) -> list[str]:
    relay = record.get("relay_target")
    require(isinstance(relay, dict), "missing relay target identity")
    return [
        "serve-relay",
        "--socket", str(record["socket"]["path"]),
        "--record", str(record["record_path"]),
        "--iso", str(record["paths"]["iso"]),
        "--native-pid", str(relay["pid"]),
        "--native-port", str(relay["tcp_port"]),
        "--native-daemon", str(relay["daemon_path"]),
        "--native-runtime", str(relay["runtime"]),
    ]


def validate_relay(
    record: dict[str, object], *, sock_path: str, record_path: str, iso: str,
    native_pid: int, native_port: int, native_daemon: str, native_runtime: str,
) -> None:
    require(record.get("mode") == "relay", "control owner mode is not the requested relay")
    paths = record.get("paths")
    require(paths == {"iso": absolute(iso)}, "relay record names a different isolated socket directory")
    require(record.get("record_path") == absolute(record_path), "relay record path does not match")
    relay_target = record.get("relay_target")
    require(isinstance(relay_target, dict), "missing relay target identity")
    require(
        relay_target.get("pid") == native_pid
        and relay_target.get("tcp_port") == native_port
        and relay_target.get("daemon_path") == absolute(native_daemon)
        and relay_target.get("runtime") == absolute(native_runtime),
        "relay record names a different native Tern target",
    )
    current_target = validate_native_target(native_pid, native_port, native_daemon, native_runtime)
    require(relay_target.get("native") == current_target, "reused Tern process identity changed or is stale")
    sock = control_socket(sock_path)
    require(record.get("socket") == sock, "relay socket identity changed or is stale")
    owner_record = record.get("owner")
    require(isinstance(owner_record, dict), "missing relay process identity")
    owner = read_process(int(owner_record.get("pid", -1)))
    require_process_identity(owner, owner_record, "relay process")
    require_current_user(owner, "relay process")
    argv = owner["cmdline"]
    require(isinstance(argv, list) and len(argv) >= 3, "malformed relay process command line")
    require(os.path.realpath(argv[1]) == os.path.realpath(__file__), "socket is not owned by the control relay helper")
    require(argv[2:] == expected_relay_argv(record), "relay process command line changed")
    require_socket_owned_by(sock, int(owner["pid"]))


def save_isolated(args: argparse.Namespace) -> None:
    record_path = check_private_record_path(args.record, must_exist=False)
    require(not record_path.exists(), "control owner record already exists")
    try:
        socket_info = os.lstat(args.socket)
    except OSError as exc:
        raise OwnerError(f"cannot inspect newly started control socket: {exc}") from exc
    require(not stat.S_ISLNK(socket_info.st_mode), "control socket must not be a symlink")
    require(stat.S_ISSOCK(socket_info.st_mode), "control path is not a Unix socket")
    require(socket_info.st_uid == os.geteuid(), "control socket is not owned by the current user")
    os.chmod(args.socket, 0o600, follow_symlinks=False)
    sock = control_socket(args.socket)
    owners = socket_fd_owners(int(sock["kernel_inode"]))
    require(len(owners) == 1, f"expected exactly one Tern socket owner, found {sorted(owners)}")
    owner_pid = next(iter(owners))
    owner = read_process(owner_pid)
    validate_instance_process(owner, socket_path=args.socket, iso=args.iso, runtime=args.runtime, daemon=args.daemon)
    supervisor = read_process(int(args.supervisor_pid))
    validate_supervisor(supervisor, args.config)
    require_descendant(owner_pid, int(args.supervisor_pid))
    record = {
        "schema": 1,
        "mode": "isolated",
        "paths": {"iso": absolute(args.iso), "runtime": absolute(args.runtime), "daemon": absolute(args.daemon), "config": absolute(args.config)},
        "socket": sock,
        "owner": identity(owner),
        "supervisor": identity(supervisor),
    }
    write_record(record_path, record)



def relay_loop(client: socket.socket, port: int) -> None:
    upstream = socket.create_connection(("127.0.0.1", port), timeout=5)
    upstream.settimeout(None)
    selector = selectors.DefaultSelector()
    selector.register(client, selectors.EVENT_READ, upstream)
    selector.register(upstream, selectors.EVENT_READ, client)
    closed: set[socket.socket] = set()
    try:
        while len(closed) < 2:
            for key, _ in selector.select(timeout=30):
                source = key.fileobj
                destination = key.data
                data = source.recv(65536)
                if not data:
                    closed.add(source)
                    try:
                        destination.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass
                    selector.unregister(source)
                    continue
                destination.sendall(data)
    finally:
        selector.close()
        upstream.close()
        client.close()


def serve_relay(args: argparse.Namespace) -> None:
    record_path = check_private_record_path(args.record, must_exist=False)
    require(not record_path.exists(), "control owner record already exists")
    socket_path = absolute(args.socket)
    require(not os.path.lexists(socket_path), "refusing to replace an existing control socket")
    iso = absolute(args.iso)
    native_pid = int(args.native_pid)
    native_port = int(args.native_port)
    daemon = absolute(args.native_daemon)
    runtime = absolute(args.native_runtime)
    native = validate_native_target(native_pid, native_port, daemon, runtime)
    validate_control_directory(socket_path)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(socket_path)
        os.chmod(socket_path, 0o600, follow_symlinks=False)
        server.listen(8)
        relay_proc = read_process(os.getpid())
        sock = control_socket(socket_path)
        require_socket_owned_by(sock, os.getpid())
        record = {
            "schema": 1,
            "mode": "relay",
            "paths": {"iso": iso},
            "record_path": absolute(record_path),
            "socket": sock,
            "owner": identity(relay_proc),
            "relay_target": {
                "pid": native_pid,
                "tcp_port": native_port,
                "daemon_path": daemon,
                "runtime": runtime,
                "native": native,
            },
        }
        write_record(record_path, record)
        print(f"control relay ready on {socket_path}", flush=True)
        while True:
            client, _ = server.accept()
            try:
                relay_loop(client, native_port)
            except OSError:
                client.close()
    finally:
        server.close()


def validate(args: argparse.Namespace) -> None:
    record_path = check_private_record_path(args.record, must_exist=True)
    record = read_record(record_path)
    if args.expected_mode == "isolated":
        validate_isolated(
            record, sock_path=args.socket, iso=args.iso, runtime=args.runtime,
            daemon=args.daemon, config=args.config,
        )
        return
    validate_relay(
        record,
        sock_path=args.socket,
        record_path=str(record_path),
        iso=args.iso,
        native_pid=int(args.native_pid),
        native_port=int(args.native_port),
        native_daemon=args.native_daemon,
        native_runtime=args.native_runtime,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--socket", required=True)
    record.add_argument("--record", required=True)
    record.add_argument("--iso", required=True)
    record.add_argument("--runtime", required=True)
    record.add_argument("--daemon", required=True)
    record.add_argument("--config", required=True)
    record.add_argument("--supervisor-pid", required=True, type=int)
    check = sub.add_parser("validate")
    check.add_argument("--socket", required=True)
    check.add_argument("--record", required=True)
    check.add_argument("--iso", required=True)
    check.add_argument("--expected-mode", choices=("isolated", "relay"), required=True)
    check.add_argument("--runtime")
    check.add_argument("--daemon")
    check.add_argument("--config")
    check.add_argument("--native-pid", type=int)
    check.add_argument("--native-port", type=int)
    check.add_argument("--native-daemon")
    check.add_argument("--native-runtime")
    relay = sub.add_parser("serve-relay")
    relay.add_argument("--socket", required=True)
    relay.add_argument("--record", required=True)
    relay.add_argument("--iso", required=True)
    relay.add_argument("--native-pid", required=True, type=int)
    relay.add_argument("--native-port", required=True, type=int)
    relay.add_argument("--native-daemon", required=True)
    relay.add_argument("--native-runtime", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "record":
            save_isolated(args)
        elif args.command == "validate":
            validate(args)
        else:
            serve_relay(args)
    except (OwnerError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"control owner: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
