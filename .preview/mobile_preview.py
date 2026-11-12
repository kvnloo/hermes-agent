from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
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
    ("preview-triage", "Triage — inspect responsive lane navigation", "triage"),
    ("preview-todo", "Todo — use tabs, pan, or keyboard", "todo"),
    ("preview-running", "Running — open this long synthetic card to inspect the mobile drawer containment and touch targets", "running"),
    ("preview-review", "Review — verify the bordered next-lane peek", "review"),
    ("preview-done", "Done — final lane has no false trailing cue", "done"),
]
for key, title, status in fixtures:
    task_id = kb.create_task(
        conn,
        title=title,
        body="Synthetic Tailnet preview fixture. Contains no user tasks, chats, credentials, or canonical board data.",
        assignee="preview-worker",
        created_by="preview-fixture",
        idempotency_key=key,
        initial_status="running",
        board="default",
    )
    conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
conn.commit()
conn.close()

spec = importlib.util.spec_from_file_location("preview_kanban_plugin", PLUGIN / "plugin_api.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
setattr(module, "_ws_upgrade_authorized", lambda _websocket: True)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(module.router, prefix="/api/plugins/kanban")

@app.get("/api/dashboard/plugins")
def plugins():
    return JSONResponse([{
        "name": "kanban",
        "label": "Kanban",
        "description": "Privacy-safe exact-revision mobile Kanban preview",
        "icon": "Package",
        "version": "1.0.0",
        "tab": {"path": "/kanban", "position": "after:skills"},
        "entry": "dist/index.js",
        "css": "dist/style.css",
    }])

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "fixture": True,
        "head": "85208e3720245449ead63868604efacd9ad09012",
        "surface": "standalone-kanban-webui",
    }

app.mount("/dashboard-plugins/kanban", StaticFiles(directory=PLUGIN), name="kanban-assets")
app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="web-assets")

@app.get("/{path:path}")
def spa(path: str):
    candidate = (DIST / path).resolve()
    if candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(DIST / "index.html")
