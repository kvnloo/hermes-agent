from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path("/workspace/zer0/oss/hermes-agent/.worktrees/t_8ac76e84")
HOME = Path("/tmp/hermes-hold-drag-2e9fx4ts")
DIST = ROOT / "hermes_cli" / "web_dist"
PLUGIN = ROOT / "plugins" / "kanban" / "dashboard"
os.environ["HERMES_HOME"] = str(HOME)
os.environ["HERMES_KANBAN_DB"] = str(HOME / "kanban/boards/hold-drag-review/kanban.db")
os.environ["HERMES_KANBAN_BOARD"] = "hold-drag-review"

spec = importlib.util.spec_from_file_location("combined_kanban_plugin", PLUGIN / "plugin_api.py")
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
        "description": "Exact hold-drag density v3 private preview",
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
        "commit": "dcb6804e9411c9559e9f53a3958876882ec247da",
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
