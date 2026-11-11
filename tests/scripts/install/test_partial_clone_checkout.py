"""Regression for #153258: a successful filtered clone can fail when checking out blobs."""

import os
from pathlib import Path
import shutil
import subprocess

import pytest


@pytest.mark.platforms("posix")
def test_failed_partial_checkout_retries_unfiltered_clone(tmp_path):
    real_git = shutil.which("git")
    assert real_git is not None

    def git(*args):
        return subprocess.run(
            [real_git, *map(str, args)], check=True, capture_output=True, text=True
        ).stdout.strip()

    origin = tmp_path / "origin.git"
    source = tmp_path / "source"
    git("init", "--bare", origin)
    git("init", "-b", "main", source)
    git("-C", origin, "config", "uploadpack.allowFilter", "true")
    (source / "README.md").write_text("checkout completed\n")
    git("-C", source, "add", "README.md")
    git(
        "-C", source,
        "-c", "user.name=Installer Test",
        "-c", "user.email=installer@example.invalid",
        "commit", "-m", "test checkout",
    )
    pinned = git("-C", source, "rev-parse", "HEAD")
    git("-C", source, "push", str(origin), "main")

    # Simulate GitHub's HTTP 400 on lazy blob fetch; ordinary unfiltered
    # clone + checkout still use real Git against the local bare repository.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "partial-clone"
    shim = bin_dir / "git"
    shim.write_text(
        '''#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys

args = sys.argv[1:]
real = os.environ["REAL_GIT"]
marker = Path(os.environ["PARTIAL_MARKER"])
if "clone" in args:
    code = subprocess.call([real, *args])
    if code == 0:
        if "--filter=blob:none" in args:
            marker.touch()
        else:
            marker.unlink(missing_ok=True)
    sys.exit(code)
if "checkout" in args and marker.exists():
    sys.stderr.write("error: RPC failed; HTTP 400 curl 22 The requested URL returned error: 400\\n")
    sys.exit(128)
os.execv(real, [real, *args])
'''
    )
    shim.chmod(0o755)

    home = tmp_path / "hermes-home"
    installed = tmp_path / "installed"
    env = os.environ.copy()
    env.update(
        REAL_GIT=real_git,
        PARTIAL_MARKER=str(marker),
        HERMES_REPO_URL=origin.as_uri(),
        HERMES_INSTALL_CHANNEL="main",
        HERMES_HOME=str(home),
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
    )
    installer = Path(__file__).resolve().parents[3] / "scripts" / "install.sh"
    result = subprocess.run(
        ["bash", str(installer), "--stage", "repository",
         "--commit", pinned, "--dir", str(installed)],
        env=env, text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists(), "complete-clone fallback was never used"
    assert git("-C", installed, "rev-parse", "HEAD") == pinned
    assert (installed / "README.md").read_text() == "checkout completed\n"
