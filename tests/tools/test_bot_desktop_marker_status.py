"""Marker-owned Docker Bot Desktop status probes its recorded owner without making a new environment."""
from __future__ import annotations

import subprocess

import pytest

from tools.bot_desktop import placement, runtime, sandbox_host


def test_published_env_from_marker_execs_only_the_recorded_container(monkeypatch):
    marker = {
        "backend": "DockerEnvironment",
        "container": "recorded-container",
        "docker": "docker.exe",
        "dir": "/tmp/hermes-bot-desktop/lena-tabwright",
    }
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b"DISPLAY=:20\nXAUTHORITY=/tmp/xauth\n", b"")

    monkeypatch.setattr(sandbox_host.subprocess, "run", run)

    assert sandbox_host.published_env_from_marker(marker) == {
        "DISPLAY": ":20", "XAUTHORITY": "/tmp/xauth"}
    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[:6] == ["docker.exe", "exec", "--user", "pn", "recorded-container", "bash"]
    assert "/tmp/hermes-bot-desktop/lena-tabwright" in argv[-1]
    assert kwargs["timeout"] == 15 and kwargs["check"] is False


def test_published_env_from_marker_fails_closed_on_missing_or_invalid_owner(monkeypatch):
    calls = []
    monkeypatch.setattr(sandbox_host.subprocess, "run", lambda *args, **kwargs: calls.append(args))

    assert sandbox_host.published_env_from_marker({}) == {}
    assert sandbox_host.published_env_from_marker(
        {"backend": "SSHEnvironment", "container": "id", "docker": "docker", "dir": "/tmp/screen"}) == {}
    assert calls == []


def test_published_env_from_marker_returns_empty_when_launcher_probe_fails(monkeypatch):
    marker = {
        "backend": "DockerEnvironment", "container": "recorded-container", "docker": "docker",
        "dir": "/tmp/hermes-bot-desktop/lena-tabwright",
    }
    monkeypatch.setattr(sandbox_host.subprocess, "run",
                        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, b"", b"not found"))

    assert sandbox_host.published_env_from_marker(marker) == {}


def test_published_env_from_marker_handles_docker_errors(monkeypatch):
    marker = {
        "backend": "DockerEnvironment", "container": "recorded-container", "docker": "docker",
        "dir": "/tmp/hermes-bot-desktop/lena-tabwright",
    }

    def fail_run(*args, **kwargs):
        raise OSError("docker unavailable")

    monkeypatch.setattr(sandbox_host.subprocess, "run", fail_run)

    assert sandbox_host.published_env_from_marker(marker) == {}


def test_standalone_status_uses_the_recorded_docker_container(monkeypatch):
    marker = {
        "backend": "DockerEnvironment", "container": "recorded-container", "docker": "docker",
        "dir": "/tmp/hermes-bot-desktop/lena-tabwright",
    }
    monkeypatch.setattr(sandbox_host, "_read_marker", lambda: marker)
    monkeypatch.setattr(sandbox_host, "marker_sandbox_alive", lambda value: True)
    probed = []
    monkeypatch.setattr(sandbox_host, "docker_marker_missing_binaries",
                        lambda value: probed.append(("missing", value)) or [])
    monkeypatch.setattr(sandbox_host, "published_env_from_marker",
                        lambda value: probed.append(("published", value)) or {"DISPLAY": ":20"})
    monkeypatch.setattr(runtime, "_sandbox_env",
                        lambda **kwargs: pytest.fail("status must not look up or create another terminal env"))

    status = runtime._sandbox_status("lena-tabwright", placement.Placement(placement.TERMINAL, "docker"))

    assert status.running and status.display == ":20" and status.profile == "lena-tabwright"
    assert probed == [("missing", marker), ("published", marker)]


def test_standalone_status_reflects_missing_marker_owned_docker_stack(monkeypatch):
    marker = {
        "backend": "DockerEnvironment", "container": "recorded-container", "docker": "docker",
        "dir": "/tmp/hermes-bot-desktop/lena-tabwright",
    }
    monkeypatch.setattr(sandbox_host, "_read_marker", lambda: marker)
    monkeypatch.setattr(sandbox_host, "marker_sandbox_alive", lambda value: True)
    monkeypatch.setattr(sandbox_host, "docker_marker_missing_binaries", lambda value: ["Xvnc"])
    monkeypatch.setattr(sandbox_host, "published_env_from_marker", lambda value: {})

    status = runtime._sandbox_status("lena-tabwright", placement.Placement(placement.TERMINAL, "docker"))

    assert not status.running and status.blocker and "Xvnc" in status.blocker
    assert "placement: gateway" in status.blocker  # non-running Docker marker retains image guidance.


def test_marker_status_uses_default_docker_user_when_pn_is_unavailable(monkeypatch):
    """A Docker image without 'pn' must remain visible after the gateway loses its env registry."""
    class DockerEnvironment:
        _container_id = "recorded-container"
        _docker_exe = "docker.exe"

    monkeypatch.setattr(sandbox_host, "_user_for", lambda env: None)
    marker = {**sandbox_host._owner_identity(DockerEnvironment()),
              "dir": "/tmp/hermes-bot-desktop/lena-tabwright"}
    assert marker["user"] is None  # explicit fallback survives in the on-disk marker

    commands = []

    def run(argv, **kwargs):
        commands.append(argv)
        assert "--user" not in argv, "Docker must use the image default when pn is unavailable"
        output = (b"DISPLAY=:20\nXAUTHORITY=/tmp/xauth\n"
                  if "launcher.pid" in argv[-1] else b"")
        return subprocess.CompletedProcess(argv, 0, output, b"")

    monkeypatch.setattr(sandbox_host.subprocess, "run", run)
    assert sandbox_host.published_env_from_marker(marker)["DISPLAY"] == ":20"
    assert sandbox_host.docker_marker_missing_binaries(marker) == []
    assert len(commands) == 2
