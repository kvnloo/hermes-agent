"""Omarchy's XDG browser wrapper must not hide Desktop update progress (#156156)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SHIM = Path(__file__).resolve().parents[3] / "scripts" / "desktop-update" / "posix.sh"


def _executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


@pytest.mark.platforms("linux")
@pytest.mark.parametrize(
    ("selected", "should_open"),
    [
        pytest.param("chromium.desktop", True, id="chromium"),
        pytest.param("firefox.desktop", False, id="firefox"),
        pytest.param("brave-browser.desktop", False, id="brave"),
        pytest.param("", False, id="unresolved"),
    ],
)
def test_omarchy_wrapper_uses_selected_browser(tmp_path: Path, selected: str, should_open: bool) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _executable(
        bin_dir / "xdg-settings",
        "#!/bin/sh\n"
        'test "$1" = get && test "$2" = default-web-browser || exit 2\n'
        "printf '%s\\n' omarchy-browser.desktop\n",
    )
    _executable(
        bin_dir / "omarchy-cmd-default-browser",
        "#!/bin/sh\n"
        'printf "%s\\n" "$HERMES_TEST_SELECTED_BROWSER"\n',
    )
    # Mask installed host browsers so the hand-off can only launch our probe.
    browser_probe = (
        "#!/bin/sh\n"
        'printf "%s\\n" "$@" > "$HERMES_TEST_BROWSER_INVOCATION"\n'
    )
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        _executable(bin_dir / name, browser_probe)

    install_root = tmp_path / "hermes-agent"
    install_root.mkdir()
    invocation = tmp_path / "browser-invocation"
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "HERMES_HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HERMES_TEST_SELECTED_BROWSER": selected,
        "HERMES_TEST_BROWSER_INVOCATION": str(invocation),
        "HERMES_SELFTEST_HOLD_SECONDS": "1",
    }
    env.pop("HERMES_SELFTEST_FAIL", None)
    result = subprocess.run(
        ["bash", str(SHIM), "--install-root", str(install_root), "--self-test-ui"],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    if should_open:
        assert invocation.is_file(), result.stdout + result.stderr
        assert any(
            arg.startswith("--app=http://127.0.0.1:")
            for arg in invocation.read_text(encoding="utf-8").splitlines()
        )
    else:
        assert not invocation.exists(), result.stdout + result.stderr
        assert "shim: no renderer; skipping UI" in result.stdout
