"""A launcher generated for a temporary checkout retains its own identity (#129976)."""
import subprocess
import sys
from pathlib import Path

import pytest

from hermes_cli._launchers import _mint_shell_launcher, _publish_conveniences, _write_shell


@pytest.mark.platforms("linux", "macos")
def test_maintains_own_generated_launcher_to_durable_target(tmp_path):
    root = tmp_path / "fixture-checkout"
    root.mkdir()
    output = tmp_path / "fixture-bin"
    output.mkdir()
    # Same root marker the production bootstrap emits, followed only by a
    # marker print: no Hermes bootstrap, packages, configuration or jobs run.
    script = f"import sys\nsys.path.insert(0, {str(root)!r})\nprint('fixture launched')\n"
    launcher = _mint_shell_launcher("hermes", output, Path(sys.executable), script)
    assert launcher is not None
    completed = subprocess.run([str(launcher)], capture_output=True, text=True, timeout=5, check=True)
    assert completed.stdout == "fixture launched\n"
    durable_dir = root / ".hermes" / "bin"
    durable_dir.mkdir(parents=True)
    assert _write_shell(durable_dir / "hermes", [
        sys.executable, "-I", "-c", "print('durable fixture launched')",
    ]) is not None
    published = _publish_conveniences(root, output, ["hermes"], create=False)
    after = subprocess.run([str(launcher)], capture_output=True, text=True, timeout=5, check=True)
    assert (launcher in published, after.stdout) == (True, "durable fixture launched\n")
