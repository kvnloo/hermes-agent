from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / ".preview" / "home-isolated"
DIST = ROOT / "hermes_cli" / "web_dist"
PLUGIN = ROOT / "plugins" / "kanban" / "dashboard"
for key in tuple(os.environ):
    if key.upper().startswith("HERMES_KANBAN_"):
        os.environ.pop(key, None)
os.environ["HERMES_HOME"] = str(HOME)
os.environ["HERMES_KANBAN_BOARD"] = "default"
HOME.mkdir(parents=True, exist_ok=True)

from hermes_cli import kanban_db as kb

kb.init_db(board="default")
conn = kb.connect(board="default")
fixtures = [
    ("fixture-active", "Active attention — try Settle or Snooze", "active"),
    ("fixture-settled", "Settled attention — try Wake", "settled"),
    ("fixture-snoozed", "Snoozed attention — try Wake", "snoozed"),
]
for key, title, state in fixtures:
    task_id = kb.create_task(
        conn,
        title=title,
        body="Synthetic Tailnet preview fixture. Contains no user tasks, chats, or secrets.",
        assignee="fixture-worker",
        created_by="preview-fixture",
        idempotency_key=key,
        initial_status="running",
        board="default",
    )
    receipt = kb.project_task_attention(conn, task_id)
    if state == "active" and receipt["state"] != "active":
        kb.update_task_attention(conn, task_id, action="wake", actor="fixture", source="preview", expected_revision=receipt["revision"], idempotency_key=f"{key}-wake-{receipt['revision']}")
    elif state == "settled" and receipt["state"] == "active":
        kb.update_task_attention(conn, task_id, action="settle", actor="fixture", source="preview", expected_revision=receipt["revision"], idempotency_key=f"{key}-settle-{receipt['revision']}")
    elif state == "snoozed" and receipt["state"] == "active":
        kb.update_task_attention(conn, task_id, action="snooze", wake_at=int(time.time()) + 86400 * 30, actor="fixture", source="preview", expected_revision=receipt["revision"], idempotency_key=f"{key}-snooze-{receipt['revision']}")
conn.close()

spec = importlib.util.spec_from_file_location("preview_kanban_plugin", PLUGIN / "plugin_api.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
# This server is itself loopback-only and reachable remotely only through the
# tailnet-scoped Tailscale Serve listener, so no dashboard session secret exists.
setattr(module, "_ws_upgrade_authorized", lambda _websocket: True)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(module.router, prefix="/api/plugins/kanban")

@app.get("/api/dashboard/plugins")
def plugins():
    return JSONResponse([{
        "name": "kanban",
        "label": "Kanban",
        "description": "Privacy-safe sidebar attention visual validation",
        "icon": "Package",
        "version": "1.0.0",
        "tab": {"path": "/kanban", "position": "after:skills"},
        "entry": "dist/index.js",
        "css": "dist/style.css",
    }])

@app.get("/api/health")
def health():
    return {"ok": True, "synthetic_only": True, "pr": "88752", "head": "6d5f34c45e9154fa47df6fef6d8866d15176c6fe", "fixtures": 3, "status": "STALE / EXPERIMENTAL"}

app.mount("/dashboard-plugins/kanban", StaticFiles(directory=PLUGIN), name="kanban-assets")
app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="web-assets")

@app.get("/{path:path}")
def spa(path: str):
    candidate = (DIST / path).resolve()
    if candidate.is_relative_to(DIST.resolve()) and candidate.is_file() and candidate.name != "index.html":
        return FileResponse(candidate)
    banner = '<div style="position:fixed;z-index:2147483647;top:0;left:0;right:0;padding:9px 12px;background:#7f1d1d;color:white;font:700 12px/1.3 ui-monospace,monospace;text-align:center">PR #88752 · 6d5f34c45e9154fa47df6fef6d8866d15176c6fe · STALE / EXPERIMENTAL · SYNTHETIC ONLY · 3 FIXTURES</div><style>body{padding-top:38px!important}</style>'
    html = (DIST / "index.html").read_text().replace("<body>", "<body>" + banner, 1)
    return HTMLResponse(html)
