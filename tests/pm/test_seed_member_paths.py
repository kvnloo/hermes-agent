"""The previous generation's lock seeds the next one; a buildable member whose snapshot dir
(``_member_key``) moved must still lock against it."""

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from pm.workspace import lock_and_sync

pytestmark = pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH")

# Dependency-free, in-tree PEP 517 backend: uv builds the member's metadata offline.
BACKEND = '''from pathlib import Path
def get_requires_for_build_wheel(config_settings=None): return []
get_requires_for_build_editable = get_requires_for_build_wheel
def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    target = Path(metadata_directory) / "example_plugin-1.0.dist-info"
    target.mkdir()
    (target / "METADATA").write_text("Metadata-Version: 2.3\\nName: example-plugin\\nVersion: 1.0\\n")
    return target.name
prepare_metadata_for_build_editable = prepare_metadata_for_build_wheel
'''


class LockOnly:
    """The generation's real ``uv lock``, without installing anything."""
    python = Path(sys.executable)

    def sync(self, root, *, extras, frozen, upgrade=()):
        env = {k: v for k, v in os.environ.items() if not k.startswith("UV_")}
        env.update(UV_NO_CACHE="1", UV_PYTHON_DOWNLOADS="never", UV_OFFLINE="1")
        result = subprocess.run([shutil.which("uv"), "lock", "--offline", "--no-config", "--python", sys.executable],
                                cwd=root, env=env, capture_output=True, text=True, timeout=120, check=False)
        assert result.returncode == 0, result.stderr


def _members(root):
    return tomllib.loads((root / "pyproject.toml").read_text())["tool"]["uv"]["workspace"]["members"]


def _plugin(path):
    path.mkdir(parents=True)
    (path / "pyproject.toml").write_text(
        '[project]\nname="example-plugin"\ndynamic=["version", "dependencies"]\nrequires-python=">=3.11"\n'
        '[build-system]\nrequires=[]\nbuild-backend="backend"\nbackend-path=["."]\n')
    (path / "backend.py").write_text(BACKEND)
    return path


@pytest.mark.parametrize("change", ["moved", "updated"])
def test_buildable_member_relocks_against_the_previous_generations_seed(tmp_path, change):
    """moved: its install path changed between two generations (a renamed profile, a relocated
    home). updated: its source changed. Either can give the member a new snapshot dir while the
    seed still names the old one."""
    core = tmp_path / "core"
    core.mkdir()
    (core / "pyproject.toml").write_text(
        '[project]\nname="core"\nversion="1"\nrequires-python=">=3.11"\n[tool.uv]\npackage=false\n')
    plugin = _plugin(tmp_path / "home" / "plugins" / "example")
    first = tmp_path / "gen1"
    lock_and_sync([plugin], [], root=first, source=core, seed_lock=None, environment=LockOnly())

    if change == "moved":
        plugin = _plugin(tmp_path / "home" / "profiles" / "bot" / "plugins" / "example")
    else:
        (plugin / "plugin.py").write_text("VALUE = 2\n")
    second = tmp_path / "gen2"
    lock_and_sync([plugin], [], root=second, source=core, seed_lock=first / "uv.lock", environment=LockOnly())
    editable = [p["source"]["editable"] for p in tomllib.loads((second / "uv.lock").read_text())["package"]
                if "editable" in p["source"]]
    assert editable == _members(second)
