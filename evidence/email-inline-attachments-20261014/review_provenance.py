"""Read-only exact-source audit for canonical per-file subprocesses."""

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


def pytest_sessionfinish(session, exitstatus):
    root = Path(__file__).resolve().parent
    editable = json.loads(importlib.metadata.distribution("hermes-agent").read_text("direct_url.json"))
    editable_root = Path(unquote(urlparse(editable["url"]).path)).resolve()
    imported, foreign = {}, {}
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            imported[name] = str(path.relative_to(root))
        elif path.is_relative_to(editable_root):
            foreign[name] = str(path)
    assert not foreign, foreign
    assert imported["plugins.platforms.email.adapter"] == "plugins/platforms/email/adapter.py"
    paths = ("pyproject.toml", "uv.lock", "scripts/run_tests.sh", "pm/pyproject.toml", "pm/uv.lock", "plugins/platforms/email/adapter.py")
    result = {
        "python": sys.version,
        "executable": sys.executable,
        "base_prefix": sys.base_prefix,
        "root": str(root),
        "home": os.environ["HOME"],
        "pytest_args": session.config.args,
        "exitstatus": int(exitstatus),
        "imports": imported,
        "foreign_imports": foreign,
        "editable": editable,
        "hashes": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths},
    }
    stem = Path(session.config.args[0].split("::")[0]).stem
    output = Path(os.environ["HOME"]) / f"{stem}-provenance.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
