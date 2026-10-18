"""Native Tern browser adapter (not a CDP cloud provider).

Uses the documented ``tern browser`` JSON interface. Discovery grants no drive
permission: only a fresh open or a user RPC can bind a block to a task.
Ownership/release semantics follow OMP's TernTab (Can Bölük / Stencil, MIT).
"""
from __future__ import annotations

import base64
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
    frame: str = "main"


class TernBrowserProvider:
    """One window/pane's task-owned targets; transport is injectable for tests."""

    def __init__(self, request, pane: int, focus=None, ownership_scope=None):
        self.request = request
        self.pane = pane
        self.focus_block = focus
        self.targets: dict[str, Target] = {}
        self.pending_open: str | None = None
        self.pending_releases: dict[int, str] = {}
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
            self.reconcile_open()
            return [{"target_id": str(b["block"]), "url": b.get("url", "about:blank"),
                     "title": b.get("title", ""), "owner": b.get("owner"),
                     "owned": self.targets.get(task, Target(-1, False)).block == b["block"],
                     "available": b.get("driven") is False and not self._taken(b["block"])}
                    for b in self.blocks()]

    def _taken(self, block):
        peers = [self, *(p for p in _providers.values() if p is not None and p is not self
                        and self.ownership_scope is not None and p.ownership_scope == self.ownership_scope)]
        return any(block in peer.pending_releases or any(t.block == block for t in peer.targets.values()) for peer in peers)

    def owned(self, task, target_id=None):
        target = self.targets.get(task)
        if target is None or (target_id is not None and target.block != block_id(target_id)):
            raise TernBrowserError("Browser block is not owned by this session; hand it over explicitly first")
        return target

    def adopt_by_user(self, task, target_id):
        block = block_id(target_id)
        with self.lock:
            self.reconcile_open()
            current = self.targets.get(task)
            if current and current.block == block:
                return self.identity(task)
            entry = next((b for b in self.blocks() if b["block"] == block), None)
            if not entry or self._taken(block) or entry.get("driven") is not False:
                raise TernBrowserError("Block is missing, already driven, or this Tern cannot safely adopt it")
            # Snapshot may install a native delegate even when its answer is lost.
            # Cleanup-only claims never grant drive permission or displace the old target.
            self.pending_releases[block] = task
            try:
                self.request({"op": "snapshot", "block": block, "nodes": 1})
                self.close(task)
            except (TernBrowserError, OSError, subprocess.SubprocessError):
                self.release_pending(task)
                raise
            del self.pending_releases[block]
            self.targets[task] = Target(block, True)
            try:
                return self.identity(task)
            except (TernBrowserError, OSError, subprocess.SubprocessError):
                self.close(task)
                raise

    def release_pending(self, task=None):
        for block, owner in list(self.pending_releases.items()):
            if task is not None and task != owner:
                continue
            try:
                self.request({"op": "release", "block": block})
            except TernBrowserError as error:
                if error.kind not in {"not_found", "closed"}:
                    raise
            del self.pending_releases[block]

    def reconcile_open(self):
        """Only a late reply can identify an abandoned open. Discovery cannot."""
        if self.ownership_scope is not None and any(
                peer is not None and peer is not self and peer.ownership_scope == self.ownership_scope
                and peer.pending_open is not None for peer in _providers.values()):
            raise TernBrowserError("Another profile or pane has an indeterminate open in this window", "open_pending")
        task = self.pending_open
        if task is None:
            return
        reconcile = getattr(self.request, "reconcile_open", None)
        if reconcile is None:
            raise TernBrowserError("Tern open is indeterminate; no exact late answer is available", "open_unknown")
        try:
            answer = reconcile()
        except TernBrowserError as error:
            if error.kind in {"unsupported", "invalid", "no_window"}:
                self.pending_open = None
            raise
        block = answer.get("block")
        if type(block) is not int or block <= 0 or self._taken(block):
            raise TernBrowserError("Late open did not identify an unclaimed block", "open_unknown")
        self.targets[task] = Target(block, False)
        self.pending_open = None
        self.close(task)

    def open(self, task):
        with self.lock:
            self.reconcile_open()
            if task not in self.targets:
                try:
                    answer = self.request({"op": "open", "owner": self.pane, "url": "about:blank"})
                except TernBrowserError as error:
                    if error.kind in {"unsupported", "invalid", "no_window"}:
                        raise TernInterfaceUnavailable(str(error), error.kind) from error
                    self.pending_open = task
                    raise
                except (OSError, subprocess.SubprocessError, ValueError):
                    self.pending_open = task
                    raise
                block = answer.get("block")
                if type(block) is not int or block <= 0 or self._taken(block):
                    self.pending_open = task
                    raise TernBrowserError("Tern did not identify a new browser block", "open_unknown")
                self.targets[task] = Target(block, False)
                try:
                    self.request({"op": "snapshot", "block": block, "nodes": 1})
                except TernBrowserError as error:
                    self.close(task)
                    if error.kind in {"unsupported", "invalid"} or (
                            error.kind == "failed" and "a headless session shows no pages" in str(error)):
                        raise TernInterfaceUnavailable(str(error), error.kind) from error
                    raise
            return self.owned(task)

    def identity(self, task):
        target = self.owned(task)
        state = self.request({"op": "state", "block": target.block})
        return {"target_id": str(target.block), "title": state.get("title", ""),
                "url": state.get("url", "about:blank"), "in_tern": True,
                **({"frame": target.frame} if target.frame != "main" else {})}

    def select_frame(self, task, target_id, frame):
        if not isinstance(frame, str) or not re.fullmatch(r"main|(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))*", frame):
            raise TernBrowserError("frame must be main or an exact native frame path (0, 1.0)", "invalid")
        with self.lock:
            target = self.owned(task, target_id)
            # Verify through the documented eval.frame contract, never a main-page
            # contentDocument fallback (which cannot reach cross-origin frames).
            self.request({"op": "eval", "block": target.block,
                          "function": "function () { return location.href; }", "world": "page",
                          **({"frame": frame} if frame != "main" else {})})
            identity = self.identity(task)
            target.frame = frame
            identity.pop("frame", None)
            if frame != "main":
                identity["frame"] = frame
            return identity

    def release_by_user(self, task, target_id):
        with self.lock:
            self.owned(task, target_id)
            self.close(task)
            return {"target_id": target_id, "released": True}

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
            self.reconcile_open()
            if task in self.pending_releases.values():
                raise TernBrowserError("Handover cleanup is unconfirmed; retry cleanup before driving a page", "ownership")
            target = self.open(task) if command == "open" else self.owned(task)
            if command == "screenshot" and "--annotate" in args:
                raise TernBrowserError("Annotated screenshots are not supported by the Tern adapter", "unsupported")
            if target.frame != "main" and command not in {"eval", "close"}:
                raise TernBrowserError(f"{command} cannot target a child frame with the documented native API; select main first", "unsupported")
            ref = lambda value: value.removeprefix("@")
            operations = {
                "open": lambda: {"op": "goto", "url": args[0]},
                "snapshot": lambda: {"op": "snapshot", "format": "text", "nodes": 3000 if not args else 400},
                "click": lambda: {"op": "act", "action": "click", "ref": ref(args[0])},
                "fill": lambda: {"op": "act", "action": "fill", "ref": ref(args[0]), "text": args[1]},
                "press": lambda: {"op": "input", "events": press_events(args[0])},
                "scroll": lambda: {"op": "input", "events": [{"type": "wheel", "x": 1, "y": 1, "dx": 0, "dy": -500 if args[0] == "up" else 500}]},
                "back": lambda: {"op": "nav", "go": "back"},
                "get": lambda: {"op": "state"},
                "eval": lambda: {"op": "eval", "function": f"function () {{ return ({args[0]}); }}",
                                 "world": "page", **({"frame": target.frame} if target.frame != "main" else {})},
                "screenshot": lambda: {"op": "capture", "format": "png", "full": "--full" in args},
            }
            if command == "close":
                self.close(task)
                return {"success": True, "data": {}}
            build = operations.get(command)
            if build is None:
                raise TernBrowserError(f"Unsupported Tern browser command: {command}", "unsupported")
            answer = self.request({**build(), "block": target.block})
            if command == "open":
                target.frame = "main"
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
            from tools.browser_tern_transport import TernBrowserCLI

            transport = TernBrowserCLI(executable, env, window)
            provider = TernBrowserProvider(
                transport, pane,
                lambda block: transport.invoke(["focus", str(block), "--json"]),
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
            keys = set(provider.targets) if task is None else {task}
            try:
                provider.release_pending(task)
            except (OSError, ValueError, subprocess.SubprocessError, TernBrowserError) as error:
                logger.warning("Tern pending handover cleanup failed: %s", error)
            if provider.pending_open is not None and (task is None or task == provider.pending_open):
                try:
                    provider.reconcile_open()
                except (OSError, ValueError, subprocess.SubprocessError, TernBrowserError) as error:
                    logger.warning("Tern open reconciliation failed: %s", error)
            for key in keys:
                try:
                    provider.close(key)
                except (OSError, ValueError, subprocess.SubprocessError, TernBrowserError) as error:
                    logger.warning("Tern browser cleanup failed: %s", error)
        if task is None:
            for scope, provider in list(_providers.items()):
                if scope[0] == hermes_home_key() and (provider is None or (not provider.targets and not provider.pending_releases and provider.pending_open is None)):
                    del _providers[scope]


def run_command(task, command, args):
    provider = get_provider()
    with _lock:
        bound = [p for key, p in _providers.items() if key[0] == hermes_home_key() and p is not None
                 and (task in p.targets or p.pending_open == task or task in p.pending_releases.values())]
    if any(p is not provider for p in bound):
        return {"success": False, "error": "Owned Tern page is unavailable in this window; release it before changing backend",
                "error_kind": "ownership"}
    if provider is None:
        return None
    try:
        return provider.command(task, command, args)
    except TernInterfaceUnavailable as error:
        if provider.targets or provider.pending_releases or provider.pending_open is not None:
            return {"success": False, "error": str(error), "error_kind": error.kind}
        # Only a brand-new blank block may fall back. An adopted/active target's
        # failure must never switch the agent to some unrelated browser session.
        with _lock:
            for key, value in list(_providers.items()):
                if value is provider:
                    _providers[key] = None
        return None
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError, TernBrowserError) as error:
        return {"success": False, "error": str(error), "error_kind": getattr(error, "kind", "transport")}
