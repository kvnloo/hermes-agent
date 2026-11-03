"""Background processes on the gateway path, reported to ACP clients as ``_hermes/process``.

``hermes acp`` is a gateway viewer, so the in-process report (#130898's ``acp_adapter/background.py``,
which waited on the registry's ``_completion_event``) cannot see the daemon's process registry. This
keeps that wire shape and reads the same source Desktop's status stack polls: ``process.list`` for the
session. A ``terminal`` call whose result started a background process is reported ``running`` keyed by
its ``toolCallId``; each later read that shows it finished (or no longer listed) reports ``exited``.

The gateway already wakes the session when a ``notify_on_complete`` process finishes, so this adds
liveness, not delivery. Clients that do not know the method ignore it, as ACP requires.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

PROCESS_METHOD = "hermes/process"
POLL_SECONDS = 5.0


def started_process_id(tool_name, result):
    """The process id a successful background ``terminal`` result carries, else None."""
    if tool_name != "terminal" or not isinstance(result, str):
        return None
    from acp_adapter.tools import _json_loads_maybe
    data = _json_loads_maybe(result)
    if not isinstance(data, dict) or data.get("error") or data.get("output") != "Background process started":
        return None
    proc_id = data.get("session_id")
    return proc_id if isinstance(proc_id, str) and proc_id else None


class GatewayBackgroundMixin:
    """Tracks the session's background processes for ``GatewayACPAgent``."""

    def _background_state(self):
        # Lazy: GatewayACPAgent.__init__ stays untouched. {sid: {proc_id: report params}}, {sid: task}
        if "_bg_live" not in self.__dict__:
            self._bg_live, self._bg_watchers, self._bg_wake = {}, {}, {}
        return self._bg_live, self._bg_watchers, self._bg_wake

    async def _background_started(self, sid, editor_id, call_id, tool_name, args, result):
        proc_id = started_process_id(tool_name, result)
        if proc_id is None or not self._conn:
            return
        live, watchers, wake = self._background_state()
        command = (args or {}).get("command") if isinstance(args, dict) else None
        params = {"sessionId": editor_id, "toolCallId": call_id, "processId": proc_id,
                  "command": command if isinstance(command, str) else ""}
        live.setdefault(sid, {})[proc_id] = params
        await self._conn.ext_notification(PROCESS_METHOD, {**params, "status": "running"})
        wake.setdefault(sid, asyncio.Event())
        if sid not in watchers or watchers[sid].done():
            watchers[sid] = task = asyncio.create_task(self._watch_background(sid))
            # Shutdown cancels and awaits ``_background`` (``GatewayACPAgent``).
            self._background.add(task)
            task.add_done_callback(self._background.discard)

    def _background_output(self, sid, payload):
        """``agent.terminal.output`` for a tracked process: re-read now instead of at the next tick."""
        live, _, wake = self._background_state()
        if payload.get("process_id") in live.get(sid, {}) and sid in wake:
            wake[sid].set()

    async def _watch_background(self, sid):
        live, watchers, wake = self._background_state()
        try:
            while live.get(sid):
                try:
                    await asyncio.wait_for(wake[sid].wait(), POLL_SECONDS)
                except TimeoutError:
                    pass
                wake[sid].clear()
                await self._report_exits(sid)
        except asyncio.CancelledError:
            raise
        except Exception:  # health: allow BLE001 -- a status poll must never fail the viewer
            logger.debug("ACP background process watch stopped", exc_info=True)
        finally:
            if watchers.get(sid) is asyncio.current_task():
                watchers.pop(sid, None)

    async def _report_exits(self, sid):
        live, _, _ = self._background_state()
        tracked = live.get(sid) or {}
        listed = await self._gateway.rpc("process.list", session_id=sid)
        rows = {row.get("session_id"): row for row in (listed or {}).get("processes", [])}
        for proc_id in list(tracked):
            row = rows.get(proc_id)
            if row is not None and row.get("status") == "running":
                continue
            params = tracked.pop(proc_id)
            report = {**params, "status": "exited"}
            if row is not None:
                report.update(exitCode=row.get("exit_code"), reason=row.get("completion_reason") or "exited")
            else:
                report["reason"] = "lost"
            if self._conn:
                await self._conn.ext_notification(PROCESS_METHOD, report)
        if not tracked:
            live.pop(sid, None)
