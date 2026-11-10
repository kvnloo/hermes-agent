"""Masked sudo prompt for ACP sessions through the client's own secret card.

ACP has no secret-input request, so an ACP turn had no sudo callback and the terminal tool took the
headless path (``sudo: a password is required``). When the client exposes a ``request_secret`` MCP
tool (T3 Code does), the callback calls it in-process with file delivery, reads the one-use file,
deletes it and hands the value straight to the terminal tool's ``sudo -S`` rewrite. The value never
enters the model context, a tool result, the transcript or a log; the model only sees the command.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable, Iterable
from typing import Any

logger = logging.getLogger(__name__)

SUFFIX = "__request_secret"
TIMEOUT_MS = 180_000


def find_secret_tool(names: Iterable[str] | None) -> str | None:
    """Client secret tool among the agent's tools: prefer T3 Code's, else any ``*__request_secret``."""
    matches = sorted(n for n in (names or ()) if n.endswith(SUFFIX))
    return next((n for n in matches if "t3_code" in n), matches[0] if matches else None)


def _secret_file(result: Any) -> str | None:
    """Pull ``file`` out of an MCP result that may be nested JSON strings (``{"result": "{...}"}``)."""
    for _ in range(4):
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except ValueError:
                return None
            continue
        if not isinstance(result, dict):
            return None
        if result.get("status") == "saved" and isinstance(result.get("file"), str):
            return result["file"]
        result = result.get("result")
    return None


def make_sudo_callback(tool_names: Callable[[], Iterable[str] | None],
                       dispatch: Callable[[str, dict], Any] | None = None) -> Callable[[], str]:
    """Zero-argument callback for ``terminal_tool.set_sudo_password_callback``; "" means skipped."""
    if dispatch is None:
        from tools.registry import registry
        dispatch = registry.dispatch

    def callback() -> str:
        from tools.terminal_tool_sudo import get_sudo_prompt_command
        name = find_secret_tool(tool_names())
        if not name:
            return ""
        command = get_sudo_prompt_command()
        try:
            from gateway.run import _redact_approval_command
            command = _redact_approval_command(command)
        except Exception:
            pass
        reason = f"sudo for: {command[:300]}" if command else "sudo password for a terminal command"
        try:
            result = dispatch(name, {"label": "sudo password", "reason": reason, "delivery": "file",
                                     "timeoutMs": TIMEOUT_MS, "clientRequestId": os.urandom(8).hex()})
        except Exception as exc:
            # Raise, not "": the terminal tool records an error outcome and still fails closed,
            # so a lost prompt no longer reads as the owner choosing to skip (analyst R02 F8).
            logger.warning("sudo prompt via %s failed", name, exc_info=False)
            raise RuntimeError(f"sudo prompt via {name} failed") from exc
        path = _secret_file(result)
        if not path:
            return ""
        try:
            with open(path, encoding="utf-8") as f:
                value = f.read()
        except OSError:
            return ""
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        return value.removesuffix("\n")

    return callback
