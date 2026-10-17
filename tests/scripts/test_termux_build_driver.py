"""Verify the Termux builder image identity covers its runtime inputs."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.platforms("posix")



@pytest.mark.parametrize("changed_input", ["Dockerfile", "base"])
def test_builder_image_identity_covers_all_inputs(tmp_path, changed_input):
    repo = tmp_path / "source with spaces"
    scripts = repo / "scripts/termux"
    scripts.mkdir(parents=True)
    for name in ("build_builder_image.sh", "termux-builder.Dockerfile"):
        shutil.copy2(ROOT / "scripts/termux" / name, scripts / name)
    shutil.copytree(ROOT / "pm", repo / "pm", ignore=shutil.ignore_patterns("__pycache__"))
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "python3").symlink_to(sys.executable)
    # Only inspect an already-published image; any build/push call is a failure.
    command = 'docker() { [[ "$1 $2" == "manifest inspect" ]]; }; export -f docker; bash "$1"'
    env = {**os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
           "GITHUB_REPOSITORY_OWNER": "FiXtUrE"}

    def image():
        result = subprocess.run(["bash", "-c", command, "fixture", str(scripts / "build_builder_image.sh")],
                                env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        return result.stdout.splitlines()[-1]

    original = image()
    assert original.startswith("ghcr.io/fixture/hermes-termux-builder:")
    assert image() == original
    changed = scripts / "termux-builder.Dockerfile" if changed_input == "Dockerfile" else repo / "pm/lock.json"
    before = changed.read_bytes()
    if changed_input == "Dockerfile":
        changed.write_bytes(before + b"\nRUN apt install -y git\n")
    else:
        pin = json.loads(before)
        digest = pin["packages"]["termux-docker"]["version"]
        pin["packages"]["termux-docker"]["version"] = digest[:-1] + ("a" if digest[-1] != "a" else "b")
        changed.write_text(json.dumps(pin))
    assert image() != original
    changed.write_bytes(before)
    assert image() == original
