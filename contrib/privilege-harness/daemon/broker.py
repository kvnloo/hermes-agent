"""Fail-closed single-execution privilege broker core.

The Hermes plugin is only a requester.  This module belongs to the separately
installed helper and deliberately has no shell-command interface.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
import stat
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class BrokerError(RuntimeError):
    pass


class InvalidRequest(BrokerError):
    pass


class Unauthorized(BrokerError):
    pass


class Expired(BrokerError):
    pass


class IntegrityError(BrokerError):
    pass


class AmbiguousExecution(BrokerError):
    pass


@dataclass(frozen=True)
class PeerIdentity:
    uid: int
    pid: int
    start_time: int

    def canonical(self) -> dict:
        return {"uid": self.uid, "pid": self.pid, "start_time": self.start_time}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_text(value: str, limit: int = 240) -> str:
    cleaned = "".join(ch for ch in value if ch >= " " and ch not in "\x7f\u202a\u202b\u202d\u202e\u2066\u2067\u2068\u2069")
    if len(cleaned) > limit:
        cleaned = cleaned[:limit] + "…"
    return html.escape(cleaned, quote=True)


class Catalog:
    def __init__(self, path: Path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidRequest("catalog is not valid UTF-8 JSON") from exc
        if set(document) != {"version", "operations"} or document["version"] != 1:
            raise InvalidRequest("unsupported catalog shape")
        operations = document["operations"]
        if not isinstance(operations, list) or not operations:
            raise InvalidRequest("catalog requires operations")
        self.operations = {}
        for operation in operations:
            self._load_operation(operation)
        self.digest = hashlib.sha256(raw).hexdigest()

    def _load_operation(self, operation: dict) -> None:
        allowed = {"id", "executable", "argv", "slots", "timeout_seconds", "cwd"}
        if not isinstance(operation, dict) or set(operation) - allowed:
            raise InvalidRequest("unknown catalog field")
        operation_id = operation.get("id")
        if not isinstance(operation_id, str) or not operation_id or operation_id in self.operations:
            raise InvalidRequest("invalid or duplicate operation id")
        executable = Path(operation.get("executable", ""))
        executable_name = executable.name.lower()
        if (executable_name.startswith(("python", "perl", "ruby", "node", "php"))
                or executable_name in {"sh", "bash", "dash", "zsh", "fish", "env"}):
            raise InvalidRequest("interpreters and shells are not catalog operations")
        if not executable.is_absolute() or not executable.is_file() or executable.is_symlink():
            raise IntegrityError("executable must be an absolute regular file")
        mode = executable.stat().st_mode
        parent_mode = executable.parent.stat().st_mode
        if mode & (stat.S_IWGRP | stat.S_IWOTH) or parent_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise IntegrityError("executable and containing directory must not be group/world writable")
        if operation.get("cwd") is not None and not Path(operation["cwd"]).is_absolute():
            raise InvalidRequest("cwd must be absolute")
        argv = operation.get("argv")
        slots = operation.get("slots")
        if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
            raise InvalidRequest("argv must be a string list")
        if not isinstance(slots, dict):
            raise InvalidRequest("slots must be an object")
        self.operations[operation_id] = operation

    def plan(self, operation_id: str, values: dict) -> dict:
        operation = self.operations.get(operation_id)
        if operation is None:
            raise InvalidRequest("unknown operation")
        if not isinstance(values, dict) or set(values) != set(operation["slots"]):
            raise InvalidRequest("slot set does not match operation")
        rendered = {}
        for name, spec in operation["slots"].items():
            value = values[name]
            if spec.get("type") != "enum" or value not in spec.get("values", []):
                raise InvalidRequest(f"invalid slot: {name}")
            if not isinstance(value, str) or "\0" in value:
                raise InvalidRequest(f"invalid slot: {name}")
            rendered[name] = value
        argv = [str(operation["executable"])]
        for item in operation["argv"]:
            try:
                argv.append(item.format_map(rendered))
            except (KeyError, ValueError) as exc:
                raise InvalidRequest("invalid argv template") from exc
        executable = Path(operation["executable"])
        return {
            "operation_id": operation_id,
            "argv": argv,
            "cwd": operation.get("cwd", "/"),
            "timeout_seconds": min(max(int(operation.get("timeout_seconds", 30)), 1), 300),
            "catalog_digest": self.digest,
            "executable_digest": _file_digest(executable),
            "executable_stat": [executable.stat().st_dev, executable.stat().st_ino],
        }


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append(self, event: dict) -> None:
        encoded = _canonical(event) + b"\n"
        with self._lock:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(fd, encoded)
                os.fsync(fd)
            finally:
                os.close(fd)


class PrivilegeBroker:
    def __init__(self, *, catalog_path: Path, ledger_path: Path,
                 requester_uids: set[int], operator_uids: set[int],
                 requester_credential: str, operator_credential: str,
                 ttl_seconds: int = 15, clock: Callable[[], float] | None = None,
                 runner: Callable[[dict], dict] | None = None):
        if requester_uids & operator_uids:
            raise InvalidRequest("requester and operator identities must be disjoint")
        if not requester_credential or not operator_credential or hmac.compare_digest(requester_credential, operator_credential):
            raise InvalidRequest("requester and operator credentials must differ")
        self.catalog = Catalog(Path(catalog_path))
        self.ledger = Ledger(Path(ledger_path))
        self.requester_uids = frozenset(requester_uids)
        self.operator_uids = frozenset(operator_uids)
        self.requester_credential = requester_credential
        self.operator_credential = operator_credential
        self.ttl = ttl_seconds
        self.clock = clock or time.monotonic
        self.runner = runner or self._default_runner
        self._records: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._changed = threading.Condition(self._lock)
        self._boot_id = secrets.token_hex(16)

    def _authenticate(self, peer: PeerIdentity, credential: str, operator: bool = False) -> None:
        allowed = self.operator_uids if operator else self.requester_uids
        expected = self.operator_credential if operator else self.requester_credential
        if peer.uid not in allowed or not hmac.compare_digest(credential, expected):
            raise Unauthorized("wrong identity or credential")

    def request(self, *, peer: PeerIdentity, credential: str, operation_id: str,
                slots: dict, reason: str, profile: str, session: str, **unexpected) -> dict:
        self._authenticate(peer, credential)
        if unexpected:
            raise InvalidRequest("process inputs are not accepted")
        if not all(isinstance(value, str) for value in (reason, profile, session)):
            raise InvalidRequest("correlation fields must be strings")
        plan = self.catalog.plan(operation_id, slots)
        request_id = secrets.token_hex(16)
        grant = secrets.token_urlsafe(32)
        created = self.clock()
        record = {
            "request_id": request_id, "plan": plan, "plan_digest": _digest(plan),
            "reason": reason, "profile": profile, "session": session,
            "requester": peer, "grant": grant, "created": created,
            "expires": created + self.ttl, "state": "pending", "boot_id": self._boot_id,
        }
        self.ledger.append({"event": "request", "request_id": request_id,
                            "plan_digest": record["plan_digest"], "requester": peer.canonical()})
        with self._lock:
            self._records[request_id] = record
        return {"status": "pending", "request_id": request_id, "plan": dict(plan)}

    def operator_view(self, request_id: str, *, peer: PeerIdentity, credential: str) -> dict:
        self._authenticate(peer, credential, operator=True)
        record = self._record(request_id)
        return {"request_id": request_id, "operation_id": record["plan"]["operation_id"],
                "argv": [_safe_text(value) for value in record["plan"]["argv"]],
                "reason": _safe_text(record["reason"]), "profile": _safe_text(record["profile"]),
                "session": _safe_text(record["session"]), "plan_digest": record["plan_digest"]}

    def decide(self, request_id: str, action: str, *, peer: PeerIdentity, credential: str) -> dict:
        self._authenticate(peer, credential, operator=True)
        if action not in {"approve", "deny"}:
            raise InvalidRequest("invalid decision")
        with self._lock:
            record = self._record(request_id)
            if record["state"] != "pending":
                raise Unauthorized("request already decided")
            if self.clock() > record["expires"]:
                raise Expired("request expired")
            self.ledger.append({"event": "decision", "request_id": request_id,
                                "action": action, "operator": peer.canonical(),
                                "plan_digest": record["plan_digest"]})
            record["state"] = "approved" if action == "approve" else "denied"
            self._changed.notify_all()
        return {"status": record["state"], "request_id": request_id}

    def list_pending(self, *, peer: PeerIdentity, credential: str) -> list[dict]:
        self._authenticate(peer, credential, operator=True)
        with self._lock:
            ids = [request_id for request_id, record in self._records.items()
                   if record["state"] == "pending" and self.clock() <= record["expires"]]
        return [self.operator_view(request_id, peer=peer, credential=credential) for request_id in ids]

    def await_result(self, request_id: str, timeout: float) -> dict:
        """Claim and execute an approved request from inside the broker only.

        Socket clients never receive or present the internal grant.  The
        server invokes this after its authenticated operator channel records
        an approval decision.
        """
        with self._lock:
            record = self._records.get(request_id)
            if record is None:
                raise AmbiguousExecution("grant belongs to a previous daemon epoch")
            if record["boot_id"] != self._boot_id:
                raise AmbiguousExecution("daemon epoch changed")
            deadline = self.clock() + timeout
            while record["state"] == "pending" and self.clock() < deadline:
                self._changed.wait(timeout=max(0.0, deadline - self.clock()))
            if self.clock() > record["expires"]:
                raise Expired("grant expired")
            if record["state"] == "pending":
                raise Expired("operator decision timed out")
            if record["state"] == "completed":
                return {"status": "completed", "request_id": request_id, "result": record["result"]}
            if record["state"] in {"reserved", "started", "ambiguous"}:
                raise AmbiguousExecution("execution outcome is not terminal")
            if record["state"] != "approved":
                raise Unauthorized("request is not approved")
            self._verify_integrity(record["plan"])
            self.ledger.append({"event": "reserve", "request_id": request_id,
                                "plan_digest": record["plan_digest"]})
            record["state"] = "reserved"
            self.ledger.append({"event": "start", "request_id": request_id})
            record["state"] = "started"
        try:
            result = self.runner(dict(record["plan"]))
        except BaseException:
            with self._lock:
                record["state"] = "ambiguous"
            raise
        with self._lock:
            self.ledger.append({"event": "result", "request_id": request_id, "result": result})
            record["result"] = result
            record["state"] = "completed"
            return {"status": "completed", "request_id": request_id, "result": result}

    def _record(self, request_id: str) -> dict:
        record = self._records.get(request_id)
        if record is None:
            raise Unauthorized("unknown request")
        return record

    def _verify_integrity(self, plan: dict) -> None:
        if self.catalog.digest != hashlib.sha256(self.catalog.path.read_bytes()).hexdigest():
            raise IntegrityError("catalog changed after request")
        executable = Path(plan["argv"][0])
        stat_result = executable.stat()
        if [stat_result.st_dev, stat_result.st_ino] != plan["executable_stat"] or _file_digest(executable) != plan["executable_digest"]:
            raise IntegrityError("executable changed after request")

    @staticmethod
    def _default_runner(plan: dict) -> dict:
        from .executor import Executor
        return Executor(timeout=plan["timeout_seconds"]).execute_plan(plan)
