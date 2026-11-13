from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / ".preview" / "home-isolated"
DIST = ROOT / "hermes_cli" / "web_dist"
PLUGIN = ROOT / "plugins" / "kanban" / "dashboard"
PR = "88716"
SHA = "e187840ac45f21652d8eedb31599673fe5446c8c"
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
    ("preview-triage-v2", "Triage — inspect touch lane navigation", "triage"),
    ("preview-todo-v2", "Todo — selected lane is deterministic", "todo"),
    ("preview-ready-v2", "Ready — verify all eight selectors", "ready"),
    ("preview-running-v2", "Running — inspect vertical card scrolling", "running"),
    ("preview-blocked-v2", "Blocked — inspect mobile drawer containment", "blocked"),
    ("preview-review-v2", "Review — verify drawer open and close", "review"),
    ("preview-done-v2", "Done — verify no horizontal overflow", "done"),
    ("preview-scheduled-v2", "Scheduled — final lane is reachable", "scheduled"),
]
for key, title, status in fixtures:
    task_id = kb.create_task(conn, title=title, body=f"SYNTHETIC ONLY fixture; no user data. Exact SHA: {SHA}", assignee="preview-worker", created_by="preview-fixture", idempotency_key=key, initial_status="running", board="default")
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
    return JSONResponse([{"name":"kanban","label":"Kanban","description":"Synthetic-only exact-revision preview","icon":"Package","version":"1.0.0","tab":{"path":"/kanban","position":"after:skills"},"entry":"dist/index.js","css":"dist/style.css"}])

@app.get("/api/health")
def health():
    return {"ok": True, "synthetic_only": True, "pr": PR, "head": SHA, "fixtures": 8, "status": "PHONE VALIDATION REQUIRED"}

app.mount("/dashboard-plugins/kanban", StaticFiles(directory=PLUGIN), name="kanban-assets")
app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="web-assets")

BANNER = f'''<div style="position:fixed;z-index:2147483647;top:0;left:0;right:0;padding:9px 12px;background:#7f1d1d;color:white;font:700 12px/1.3 ui-monospace,monospace;text-align:center">PR #{PR} · {SHA} · PHONE VALIDATION REQUIRED · SYNTHETIC ONLY · 8 FIXTURES</div><style>body{{padding-top:38px!important}}</style>'''

@app.get("/{path:path}")
def spa(path: str):
    candidate = (DIST / path).resolve()
    if candidate.is_relative_to(DIST.resolve()) and candidate.is_file() and candidate.name != "index.html":
        return FileResponse(candidate)
    html = (DIST / "index.html").read_text().replace("<body>", "<body>" + BANNER, 1)
    return HTMLResponse(html)
