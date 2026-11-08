"""Regression for #62336: cookie, webhook and creds exports must never persist in snapshots."""

import os
import shlex
import subprocess

import pytest

from tools.environments.base_session_env import (
    _SNAP_TMP_SUFFIX,
    _snapshot_bootstrap_script,
    _wrap_command_script,
)

pytestmark = pytest.mark.platforms("posix")


@pytest.mark.parametrize(
    ("name", "secret"),
    [
        ("SESSION_COOKIE", "SYNTHETIC_COOKIE_VALUE"),
        ("slack_webhook_url", "https://hooks.example.invalid/services/SYNTHETIC_WEBHOOK_VALUE"),
        ("GOOGLE_APPLICATION_CREDS_JSON", "SYNTHETIC_CREDS_VALUE"),
    ],
)
def test_cookie_webhook_and_creds_are_not_snapshotted(tmp_path, name, secret):
    """Both bootstrap and the next command's re-dump omit these credential names."""
    snap = tmp_path / "hermes-snap.sh"
    kwargs = {
        "quoted_cwd": shlex.quote(str(tmp_path)),
        "quoted_snap": shlex.quote(str(snap)),
        "snap_tmp_template": shlex.quote(str(snap) + _SNAP_TMP_SUFFIX),
        "cwd_marker": "__HERMES_CWD_secret_shapes__",
    }
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "SHELL": "/bin/bash",
        "KEEP_ME": "ordinary",
        name: secret,
    }
    bash = "/bin/bash" if os.path.exists("/bin/bash") else "bash"

    bootstrap = _snapshot_bootstrap_script(excluded_names=(), **kwargs)
    first = subprocess.run(
        [bash, "-c", bootstrap], cwd=tmp_path, env=env,
        capture_output=True, text=True, check=False,
    )
    assert first.returncode == 0, first.stderr
    contents = snap.read_text()
    assert name not in contents
    assert secret not in contents
    assert 'KEEP_ME="ordinary"' in contents

    wrapper = _wrap_command_script(
        f"export {name}=SYNTHETIC_SECOND_VALUE",
        passthrough_names=(), snapshot_ready=True, **kwargs,
    )
    second = subprocess.run(
        [bash, "-c", wrapper], cwd=tmp_path, env=env,
        capture_output=True, text=True, check=False,
    )
    assert second.returncode == 0, second.stderr
    contents = snap.read_text()
    assert name not in contents
    assert "SYNTHETIC_SECOND_VALUE" not in contents
    assert 'KEEP_ME="ordinary"' in contents
