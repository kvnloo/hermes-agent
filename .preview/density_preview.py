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
if not (DIST / "assets").is_dir():
    # Generated host shell is shared by sibling worktrees and is not part of
    # the reviewed Kanban source bytes. Keep the preview's plugin assets local.
    DIST = Path("/workspace/zer0/oss/hermes-agent/hermes_cli/web_dist")
PLUGIN = ROOT / "plugins" / "kanban" / "dashboard"
REVIEWED_REVISION = "0ba3d009d6af4a3f02cb332c9bde0f4a7218bafd"
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
    ("density-triage", "Triage density — title-first compact card", "triage", None),
    ("density-todo", "Todo density — operational metadata stays aligned", "todo", "preview-worker"),
    ("density-ready", "Ready density — keyboard focus and 44px mobile controls", "ready", "preview-worker"),
    ("density-running", "Running density — open drawer to inspect full prose and aligned metadata", "running", "preview-worker"),
    ("density-blocked", "Blocked density — compact presentation does not change lifecycle state", "blocked", "preview-worker"),
    ("density-review", "Review density — presentation-only reviewed revision", "review", "reviewer"),
    ("density-done", "Done density — source-byte identity is independently verified", "done", "preview-worker"),
]
for key, title, status, assignee in fixtures:
    task_id = kb.create_task(
        conn,
        title=title,
        body="Synthetic isolated density/alignment preview fixture. Full prose remains available in the drawer. No production board, user chat, credential, or canonical lifecycle data is mounted.",
        assignee=assignee,
        created_by="density-preview-fixture",
        idempotency_key=key,
        initial_status="running",
        board="default",
    )
    conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
conn.commit()
conn.close()

spec = importlib.util.spec_from_file_location("density_preview_kanban_plugin", PLUGIN / "plugin_api.py")
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
        "label": "Kanban density preview",
        "description": "Isolated standalone WebUI density/alignment preview; not the Desktop renderer",
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
        "reviewed_revision": REVIEWED_REVISION,
        "surface": "standalone-kanban-webui",
        "production_board_mounted": False,
    }

app.mount("/dashboard-plugins/kanban", StaticFiles(directory=PLUGIN), name="kanban-assets")
app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="web-assets")

@app.get("/{path:path}")
def spa(path: str):
    candidate = (DIST / path).resolve()
    if candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(DIST / "index.html")
