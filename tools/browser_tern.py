"""Native Tern browser adapter (not a CDP cloud provider).

Uses the documented ``tern browser`` JSON interface. Discovery grants no drive
permission: only a fresh open or a user RPC can bind a block to a task.
Ownership/release semantics follow OMP's TernTab (Can Bölük / Stencil, MIT).
"""
from __future__ import annotations

import base64
import json
import logging
import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from hermes_constants import get_hermes_home, hermes_home_key

logger = logging.getLogger(__name__)
_ownership_lock = threading.RLock()


class TernBrowserError(RuntimeError):
    def __init__(self, message, kind="failed"):
        super().__init__(message)
        self.kind = kind


class TernInterfaceUnavailable(TernBrowserError):
    pass


def press_events(combo):
    """DOM trusted key steps, following OMP's tern/keys.ts protocol."""
    if not combo:
        raise TernBrowserError("A key name is required")
    names = combo.split("+") if len(combo) > 1 and "+" in combo else [combo]
    modifiers = {"Control": "ctrl", "Ctrl": "ctrl", "Alt": "alt", "Shift": "shift", "Meta": "meta"}
    mods, down = [], []
    for name in names:
        key = "Control" if name == "Ctrl" else name
        down.append({"type": "key", "action": "down", "key": key, "mods": list(mods)})
        if name in modifiers:
            mods.append(modifiers[name])
    up = []
    for step in reversed(down):
        key = step["key"]
        if key in modifiers and modifiers[key] in mods:
            mods.remove(modifiers[key])
        up.append({"type": "key", "action": "up", "key": key, "mods": list(mods)})
    return down + up


def block_id(value):
    # Do not normalize identifiers into something the user did not select.
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]*", value):
        raise TernBrowserError("target_id must be a positive decimal block id")
    return int(value)


@dataclass
class Target:
    block: int
    adopted: bool


class TernBrowserProvider:
    """One window/pane's task-owned targets; transport is injectable for tests."""

    def __init__(self, request, pane: int, focus=None, ownership_scope=None):
        self.request = request
        self.pane = pane
        self.focus_block = focus
        self.targets: dict[str, Target] = {}
        self.lock = _ownership_lock
        self.ownership_scope = ownership_scope
        self.session_info = {"session_name": "tern", "features": {"tern": True}, "_first_nav": False}

    def blocks(self):
        answer = self.request({"op": "blocks"})
        if not isinstance(answer, dict) or not isinstance(answer.get("blocks"), list):
            raise TernBrowserError("Tern browser block discovery unavailable")
        return [b for b in answer["blocks"] if isinstance(b, dict) and type(b.get("block")) is int and b["block"] > 0]

    def listing(self, task):
        with self.lock:
            return [{"target_id": str(b["block"]), "url": b.get("url", "about:blank"),
                     "title": b.get("title", ""), "owner": b.get("owner"),
                     "owned": self.targets.get(task, Target(-1, False)).block == b["block"],
                     "available": b.get("driven") is False and not self._taken(b["block"])}
                    for b in self.blocks()]

    def _taken(self, block):
        peers = [self, *(p for p in _providers.values() if p is not None and p is not self
                        and self.ownership_scope is not None and p.ownership_scope == self.ownership_scope)]
        return any(t.block == block for peer in peers for t in peer.targets.values())

    def owned(self, task, target_id=None):
        target = self.targets.get(task)
        if target is None or (target_id is not None and target.block != block_id(target_id)):
            raise TernBrowserError("Browser block is not owned by this session; hand it over explicitly first")
        return target

    def adopt_by_user(self, task, target_id):
        block = block_id(target_id)
        with self.lock:
            current = self.targets.get(task)
            if current and current.block == block:
                return self.identity(task)
            entry = next((b for b in self.blocks() if b["block"] == block), None)
            if not entry or self._taken(block) or entry.get("driven") is not False:
                raise TernBrowserError("Block is missing, already driven, or this Tern cannot safely adopt it")
            # Fail before taking ownership on headless/unsupported native interfaces.
            self.request({"op": "snapshot", "block": block, "nodes": 1})
            self.close(task)
            self.targets[task] = Target(block, True)
            return self.identity(task)

    def open(self, task):
        with self.lock:
            if task not in self.targets:
                try:
                    answer = self.request({"op": "open", "owner": self.pane, "url": "about:blank"})
                except TernBrowserError as error:
                    if error.kind in {"unsupported", "invalid"}:
                        raise TernInterfaceUnavailable(str(error), error.kind) from error
                    raise
                block = answer.get("block")
                if type(block) is not int or block <= 0 or self._taken(block):
                    raise TernBrowserError("Tern did not open a new browser block")
                self.targets[task] = Target(block, False)
                try:
                    self.request({"op": "snapshot", "block": block, "nodes": 1})
                except TernBrowserError as error:
                    self.close(task)
                    if error.kind in {"unsupported", "failed", "invalid"}:
                        raise TernInterfaceUnavailable(str(error), error.kind) from error
                    raise
            return self.owned(task)

    def identity(self, task):
        target = self.owned(task)
        state = self.request({"op": "state", "block": target.block})
        return {"target_id": str(target.block), "title": state.get("title", ""),
                "url": state.get("url", "about:blank"), "in_tern": True}

    def focus(self, task, target_id):
        with self.lock:
            target = self.owned(task, target_id)
            if self.focus_block is None:
                raise TernBrowserError("Tern focus unavailable")
            self.focus_block(target.block)
            return self.identity(task)

    def close(self, task):
        with self.lock:
            target = self.targets.get(task)
            if target:
                try:
                    self.request({"op": "release" if target.adopted else "close", "block": target.block})
                except TernBrowserError as error:
                    if error.kind not in {"not_found", "closed"}:
                        raise
                del self.targets[task]

    def command(self, task, command, args):
        with self.lock:
            target = self.open(task) if command == "open" else self.owned(task)
            if command == "screenshot" and "--annotate" in args:
                raise TernBrowserError("Annotated screenshots are not supported by the Tern adapter")
            ref = lambda value: value.removeprefix("@")
            operations = {
                "open": lambda: {"op": "goto", "url": args[0]},
                "snapshot": lambda: {"op": "snapshot", "format": "text", "nodes": 4000 if not args else 400},
                "click": lambda: {"op": "act", "action": "click", "ref": ref(args[0])},
                "fill": lambda: {"op": "act", "action": "fill", "ref": ref(args[0]), "text": args[1]},
                "press": lambda: {"op": "input", "events": press_events(args[0])},
                "scroll": lambda: {"op": "input", "events": [{"type": "wheel", "x": 1, "y": 1, "dx": 0, "dy": -500 if args[0] == "up" else 500}]},
                "back": lambda: {"op": "nav", "go": "back"},
                "get": lambda: {"op": "state"},
                "eval": lambda: {"op": "eval", "function": f"function () {{ return ({args[0]}); }}"},
                "screenshot": lambda: {"op": "capture", "format": "png", "full": "--full" in args},
            }
            if command == "close":
                self.close(task)
                return {"success": True, "data": {}}
            build = operations.get(command)
            if build is None:
                raise TernBrowserError(f"Unsupported Tern browser command: {command}")
            answer = self.request({**build(), "block": target.block})
            identity = self.identity(task)
            data = {**answer, "url": identity["url"], "title": identity["title"]}
            if command == "snapshot":
                data["snapshot"] = answer.get("text", answer.get("tree", ""))
            if command == "get":
                data["value"] = identity["url"]
            if command == "eval":
                data["result"] = answer.get("value")
            if command == "screenshot":
                paths = [arg for arg in args if not arg.startswith("--")]
                destination = Path(paths[-1]) if paths else get_hermes_home() / "browser_screenshots" / f"tern-{target.block}.png"
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(base64.b64decode(answer["data"], validate=True))
                data["path"] = str(destination)
            return {"success": True, "data": data, "tern_target": identity}


_providers: dict[tuple, TernBrowserProvider | None] = {}
_lock = _ownership_lock


def _context():
    from tools.environments.local import served_profile_child_env
    from hermes_platform.resolver import locate_command, LookupContext

    env = served_profile_child_env(inherit_credentials=False)
    from tools.browser_tool_cdp import _get_cdp_override_raw
    if _get_cdp_override_raw():
        return None  # An explicitly connected browser wins over automatic Tern selection.
    pane, window = env.get("TERN_PANE", ""), env.get("TERN_WINDOW_KEY", "")
    resolved = locate_command("tern", LookupContext(path=env.get("PATH")))
    executable = resolved.command[0] if resolved.found else None
    if not executable or not re.fullmatch(r"[1-9][0-9]*", pane) or not window:
        return None
    return env, executable, int(pane), window


def get_provider():
    context = _context()
    if context is None:
        return None
    env, executable, pane, window = context
    key = (hermes_home_key(), window, pane, env.get("TERN_DAEMON_SOCKET"), env.get("TERN_CONFIG_DIR"))
    with _lock:
        if key not in _providers:
            def invoke(argv):
                result = subprocess.run([executable, *argv, "--window", window], env=env,
                                        capture_output=True, text=True, timeout=35)
                answer = json.loads(result.stdout)
                if result.returncode or "error" in answer:
                    error = answer.get("error")
                    detail = error if isinstance(error, dict) else {}
                    raise TernBrowserError(str(detail.get("message", error or "Tern browser failed")), detail.get("kind", "failed"))
                # CLI wraps the browser op answer in `ok`.
                return answer["ok"] if isinstance(answer.get("ok"), dict) else answer

            provider = TernBrowserProvider(
                lambda op: invoke(["browser", json.dumps(op), "--timeout", "30"]), pane,
                lambda block: invoke(["focus", str(block), "--json"]),
                ownership_scope=(window, env.get("TERN_DAEMON_SOCKET"), env.get("TERN_CONFIG_DIR")))
            try:
                provider.blocks()
            except (OSError, ValueError, subprocess.SubprocessError, TernBrowserError):
                provider = None
            _providers[key] = provider
        return _providers[key]


def cleanup(task=None):
    with _lock:
        for scope, provider in list(_providers.items()):
            if scope[0] != hermes_home_key() or provider is None:
                continue
            for key in list(provider.targets) if task is None else [task]:
                try:
                    provider.close(key)
                except (OSError, ValueError, subprocess.SubprocessError, TernBrowserError) as error:
                    logger.warning("Tern browser cleanup failed: %s", error)
        if task is None:
            for scope, provider in list(_providers.items()):
                if scope[0] == hermes_home_key() and (provider is None or not provider.targets):
                    del _providers[scope]


def run_command(task, command, args):
    provider = get_provider()
    if provider is None:
        return None
    try:
        return provider.command(task, command, args)
    except TernInterfaceUnavailable as error:
        if provider.targets:
            return {"success": False, "error": str(error)}
        # Only a brand-new blank block may fall back. An adopted/active target's
        # failure must never switch the agent to some unrelated browser session.
        with _lock:
            for key, value in list(_providers.items()):
                if value is provider:
                    _providers[key] = None
        return None
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, TernBrowserError) as error:
        return {"success": False, "error": str(error)}
