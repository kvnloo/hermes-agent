from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "apps" / "desktop" / "dist"
PR = "87495"
SHA = "486a620b5a66bd41dbe45247d4734932e17c4409"
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

@app.get("/api/health")
def health():
    return {"ok": True, "synthetic_only": True, "pr": PR, "head": SHA, "fixtures": 4, "status": "STALE / EXPERIMENTAL", "surface": "desktop-spatial-runtime"}

@app.get("/{path:path}")
def spa(path: str):
    candidate = (DIST / path).resolve()
    if candidate.is_relative_to(DIST.resolve()) and candidate.is_file() and candidate.name != "index.html":
        return FileResponse(candidate)
    overlay = f'''<div style="position:fixed;z-index:2147483647;inset:0 0 auto 0;background:#7f1d1d;color:white;padding:9px;text-align:center;font:700 12px ui-monospace">PR #{PR} · {SHA} · STALE / EXPERIMENTAL · SYNTHETIC ONLY · 4 FIXTURES</div><div style="position:fixed;z-index:2147483646;top:38px;right:10px;width:min(360px,calc(100vw - 20px));padding:12px;background:#111827eF;color:#f9fafb;border:1px solid #64748b;border-radius:10px;font:12px ui-sans-serif"><b>Synthetic Spatial runtime fixture</b><div style="display:grid;gap:6px;margin-top:8px"><span>Prompt node · synthetic temple concept</span><span>Image node · generated placeholder</span><span>Video node · queued placeholder</span><span>3D node · runtime provenance</span></div></div>'''
    html = (DIST / "index.html").read_text().replace("<body>", "<body>" + overlay, 1)
    return HTMLResponse(html)
