"""Regression for #106671: auth helpers follow the installed skill location."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


_SCRIPTS = Path(__file__).resolve().parents[2] / "skills/software-development/github/scripts"


@pytest.mark.platforms("posix")
def test_gh_env_finds_credential_helper_in_profile_install(tmp_path):
    profile_scripts = (
        tmp_path / "hermes/profiles/work/skills/software-development/github/scripts"
    )
    profile_scripts.mkdir(parents=True)
    for name in ("gh-env.sh", "git-credential-token.py"):
        shutil.copy2(_SCRIPTS / name, profile_scripts / name)

    home = tmp_path / "home"
    home.mkdir()
    (home / ".git-credentials").write_text(
        "https://octocat:ghp_fixture_only@github.com\n", encoding="utf-8"
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, script in (
        ("gh", "#!/bin/sh\nexit 1\n"),
        ("uv", '#!/bin/sh\n[ "$1" = run ] || exit 2\nshift\nexec "$@"\n'),
        ("curl", "#!/bin/sh\nprintf '%s\\n' '{\"login\":\"octocat\"}'\n"),
    ):
        stub = bin_dir / name
        stub.write_text(script, encoding="utf-8")
        stub.chmod(0o755)

    env = dict(os.environ)
    env.update(
        HOME=str(home),
        HERMES_HOME=str(tmp_path / "hermes"),
        PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '/usr/bin:/bin')}",
        GITHUB_TOKEN="",
        GH_TOKEN="",
    )
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1" >/dev/null; printf "%s\\n" "$GH_AUTH_METHOD" "$GH_USER" "$GITHUB_TOKEN"',
            "bash",
            str(profile_scripts / "gh-env.sh"),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["curl", "octocat", "ghp_fixture_only"]
