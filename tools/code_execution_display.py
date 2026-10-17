"""Call-scoped eval presentation. No registry, polling or authority of its own."""
from __future__ import annotations

import contextlib
import contextvars
import copy
import json
import logging
import threading
import uuid
from typing import Any

logger = logging.getLogger(__name__)
_scope: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar("eval_presentation", default=None)


@contextlib.contextmanager
def eval_progress_scope(tool_id, callback):
    token = _scope.set({"tool_id": tool_id, "callback": callback})
    try:
        yield
    finally:
        _scope.reset(token)


class EvalPresentation:
    def __init__(self, code):
        self.scope = _scope.get()
        self.cell: dict[str, Any] = {"id": uuid.uuid4().hex, "code": code, "language": "python",
                     "status": "running", "output": "", "events": [], "views": []}
        self.revision = 0
        self.active = True
        self.lock = threading.RLock()

    def emit(self):
        self.revision += 1
        if self.scope and self.scope["callback"]:
            try:
                self.scope["callback"]("eval.update", "execute_code", None, None,
                                       eval_update={"tool_id": self.scope["tool_id"],
                                                    "cell": copy.deepcopy(self.cell), "revision": self.revision})
            except Exception:
                logger.debug("eval presentation callback failed", exc_info=True)

    def dispatch(self, tool, args, invoke):
        with self.lock:
            if not self.active:
                event = None
            else:
                event = {"id": uuid.uuid4().hex, "tool": tool, "status": "running"}
                self.cell["events"].append(event)
                self.emit()
        try:
            result = invoke()
        except BaseException:
            with self.lock:
                if self.active and event is not None:
                    event["status"] = "error"
                    self.emit()
            raise
        try:
            body = json.loads(result) if isinstance(result, str) else result
        except ValueError:
            body = None
        with self.lock:
            if self.active and event is not None:
                event["status"] = "error" if isinstance(body, dict) and (body.get("error") or body.get("exit_code", 0)) else "done"
                self.emit()
        return result

    def finish(self, result):
        with self.lock:
            self.active = False
            return self._finish(result)

    def _finish(self, result):
        body = json.loads(result)
        if not isinstance(body, dict):
            return result
        status = str(body.get("status", ""))
        if body.get("error") and status not in ("timeout", "interrupted", "yielded_to_background"):
            status = "error"
        self.cell["status"] = {"timeout": "timeout", "interrupted": "cancelled", "error": "error",
                               "yielded_to_background": "background"}.get(status, "done")
        self.cell["output"] = body.get("output", "")
        if body.get("error"):
            self.cell["error"] = body["error"]
        # Runner companions are untrusted script output. Gateway + frontend validate them.
        raw_views = body.pop("_printed_views", [])
        if not isinstance(raw_views, list):
            raw_views = []
        from agent.redact import redact_sensitive_text
        from tools.ansi_strip import strip_ansi
        # Never bypass the stdout redactor through a companion (including source code).
        def clean(value: Any) -> Any:
            if isinstance(value, str):
                return redact_sensitive_text(strip_ansi(value), code_file=True)
            if isinstance(value, list):
                return [clean(item) for item in value]
            if isinstance(value, dict):
                return {key: clean(item) for key, item in value.items()}
            return value
        self.cell = clean(self.cell)
        output = self.cell["output"]
        self.cell["views"] = [entry for entry in clean(raw_views)[:256]
                              if isinstance(entry, dict) and isinstance(entry.get("start"), int)
                              and isinstance(entry.get("printed"), str)
                              and output[entry["start"]:entry["start"] + len(entry["printed"])] == entry["printed"]]
        for event in self.cell["events"]:
            if event["status"] == "running":
                event["status"] = self.cell["status"] if self.cell["status"] != "done" else "cancelled"
        self.emit()
        body["eval_display"] = {"version": 1, "cells": [self.cell]}
        body["eval_revision"] = self.revision
        return json.dumps(body, ensure_ascii=False)


_current: contextvars.ContextVar[EvalPresentation | None] = contextvars.ContextVar("eval_cell_presentation", default=None)


def present_execution(execute, code, **kwargs):
    presentation = EvalPresentation(code)
    token = _current.set(presentation)
    presentation.emit()
    try:
        return presentation.finish(execute(code, **kwargs))
    finally:
        presentation.active = False
        _current.reset(token)


def nested_dispatch(tool, args, invoke):
    presentation = _current.get()
    return presentation.dispatch(tool, args, invoke) if presentation else invoke()


# Embedded into generated hermes_tools.py. Only explicit prints create view entries.
PRINT_VIEW_SOURCE = '''
_printed_views = []

def print_view(value, kind="json", columns=None):
    """Print literal text and opt into a matching native JSON/Markdown/table view.

    table takes rows of cells and an explicit columns list. Plain print is unchanged.
    """
    import sys
    if kind not in ("json", "markdown", "table"):
        raise ValueError("print_view kind must be json, markdown or table")
    heads, rows = [], []
    if kind == "json":
        text = json.dumps(value, ensure_ascii=False, indent=2)
    elif kind == "markdown":
        text = str(value)
    else:
        heads = [str(c) for c in (columns or [])]
        rows = [[str(c) for c in row] for row in value]
        if not heads or any(len(row) != len(heads) for row in rows):
            raise ValueError("table rows must match columns")
        text = " | ".join(heads) + "\\n" + "\\n".join(" | ".join(row) for row in rows)
    printed = text + "\\n"
    # A redirected StringIO is owned by the kernel runner. Other streams simply print.
    start = len(sys.stdout.getvalue()) if hasattr(sys.stdout, "getvalue") else None
    print(text)
    if start is not None and len(printed) <= 32768 and len(_printed_views) < 256:
        _printed_views.append({"id": "view-" + str(len(_printed_views)), "kind": kind,
                               "start": start, "printed": printed, "columns": heads, "rows": rows})
'''
