"""The Bot Mode DM child must resolve dependencies ahead of its script directory.

Regression for NousResearch/hermes-agent#156851 (alt-glitch). The fixture uses an
isolated miniature checkout, not a package planted into the real tools/ tree.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[2] / "tools" / "bot_mode_dm.py"


def test_dm_runner_does_not_shadow_installed_package(tmp_path):
    """The real script entry drops tools/ before a lazy lane imports a package."""
    checkout = tmp_path / "checkout"
    script_dir = checkout / "tools"
    script_dir.mkdir(parents=True)
    (script_dir / "__init__.py").write_text("", encoding="utf-8")
    shutil.copyfile(RUNNER, script_dir / "bot_mode_dm.py")

    # An upcoming tools/mcp/ must not take precedence over the installed SDK.
    shadow = script_dir / "mcp"
    shadow.mkdir()
    (shadow / "__init__.py").write_text('ORIGIN = "script-directory"\n', encoding="utf-8")
    site_packages = tmp_path / "site-packages"
    installed = site_packages / "mcp"
    installed.mkdir(parents=True)
    (installed / "__init__.py").write_text('ORIGIN = "installed"\n', encoding="utf-8")

    # --fan-out is stdlib-only until it lazily imports this sibling. Let that
    # real entrypoint choose the module, then probe the dependency it resolves.
    (script_dir / "bot_mode_dm_coordination.py").write_text(
        "def run_fan_out(_spec):\n"
        "    import mcp\n"
        "    print(mcp.ORIGIN)\n"
        "    return 0\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONSAFEPATH", None)
    env["PYTHONPATH"] = str(site_packages)
    result = subprocess.run(
        [sys.executable, str(script_dir / "bot_mode_dm.py"), "--fan-out", "probe"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "installed", result.stdout + result.stderr
