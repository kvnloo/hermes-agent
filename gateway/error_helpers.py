"""Transient-error classification and loop diagnostics extracted from gateway.run.

Preserves the helper extraction authored in PR #77455 against current source.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("gateway.run")


_TRANSIENT_NETWORK_ERROR_CLASS_NAMES = frozenset({
    "TimedOut", "NetworkError", "ReadError", "WriteError", "ConnectError", "ConnectTimeout",
    "ReadTimeout", "WriteTimeout", "PoolTimeout", "RemoteProtocolError", "ServerDisconnectedError",
    "ClientConnectorError", "ClientOSError"})


def _is_transient_network_error(exc: BaseException) -> bool:
    """True for transient network errors safe to log + swallow (the next poll recovers; never crash).

    Walks the cause chain so wrapped errors (PTB ``NetworkError`` over ``httpx.ConnectError``) match.

    The crash class targeted by #31066 / #31110: an unhandled Telegram ``TimedOut`` (or peer
    ``NetworkError`` / ``httpx`` connection error) propagating to the event loop and killing the entire
    gateway process. These are by definition transient — the next poll cycle or user action recovers — so
    they must never crash the process.
    """
    seen: set[int] = set()
    cur: Optional[BaseException] = exc
    depth = 0
    while cur is not None and depth < 12:
        ident = id(cur)
        if ident in seen:
            break
        seen.add(ident)
        depth += 1
        if type(cur).__name__ in _TRANSIENT_NETWORK_ERROR_CLASS_NAMES:
            return True
        cur = getattr(cur, "__cause__", None) or getattr(cur, "__context__", None)
    return False


def _gateway_loop_exception_handler(
    loop: "asyncio.AbstractEventLoop", context: Dict[str, Any]) -> None:
    """Loop-level safety net for transient network errors (installed once by ``start_gateway``).

    Logs WARNING with traceback; non-transient errors go to the default handler so real bugs surface.

    Catches the ``telegram.error.TimedOut`` crash class (issues #31066 / #31110) and any peer transient
    network error before it can kill the gateway process.
    """
    exc = context.get("exception")
    if exc is not None and _is_transient_network_error(exc):
        task = context.get("future") or context.get("task")
        task_name = ""
        if task is not None:
            try:
                task_name = task.get_name() if hasattr(task, "get_name") else repr(task)
            except Exception:
                task_name = repr(task)
        # logging's traceback formatter requires a real BaseException, not
        # merely an object with an available cause/context chain.
        exc_info = (type(exc), exc, exc.__traceback__) if isinstance(exc, BaseException) else None
        logger.warning(
            "Gateway swallowed transient network error from %s: %s: %s", task_name or "<unknown task>",
            type(exc).__name__, exc, exc_info=exc_info)
        return
    loop.default_exception_handler(context)
