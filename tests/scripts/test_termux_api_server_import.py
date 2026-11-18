"""A Termux .deb must fail validation when aiohttp is missing (Hermes #155571)."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.termux.validate_installed import api_server_import_smoke


@pytest.mark.platforms("posix")
def test_termux_api_server_http_backend_is_checked(tmp_path: Path) -> None:
    # A fresh interpreter has no optional packages: the missing package must
    # fail the same import probe the installed .deb runs in its own venv.
    runtime = tmp_path / "runtime"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(runtime)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    python = runtime / "bin/python"
    env = {key: value for key, value in os.environ.items()
           if key not in {"PYTHONPATH", "PYTHONHOME"}}

    with pytest.raises(subprocess.CalledProcessError) as missing:
        api_server_import_smoke(python, env, tmp_path)
    assert "No module named 'aiohttp'" in missing.value.stderr

    # Supplying the web interface makes that same probe succeed. The release
    # smoke runs it with the real wheel and checks the native imports too.
    site_packages = next((runtime / "lib").glob("python*/site-packages"))
    aiohttp = site_packages / "aiohttp"
    aiohttp.mkdir()
    (aiohttp / "__init__.py").write_text("from . import web\n", encoding="utf-8")
    (aiohttp / "web.py").write_text("class Application:\n    pass\n", encoding="utf-8")
    api_server_import_smoke(python, env, tmp_path)
