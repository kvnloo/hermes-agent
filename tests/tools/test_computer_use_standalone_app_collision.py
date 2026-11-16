"""Regression for a standalone CuaDriver.app competing with Hermes' PM pin (#156669)."""

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.computer_use import cua_backend as backend_module
from tools.computer_use import cua_backend_daemon as daemon_module
from tools.computer_use import cua_backend_driver as driver_module


@pytest.mark.skipif(os.name == "nt", reason="macOS/POSIX app shim scenario")
def test_standard_session_uses_pm_pin_not_standalone_path_daemon(tmp_path, monkeypatch):
    """A newer PATH shim/global daemon must not replace the pinned private runtime."""
    import pm

    pinned = (tmp_path / "pm" / "cua-driver-0.21.0-darwin-arm64" /
              "CuaDriver.app" / "Contents" / "MacOS" / "cua-driver")
    standalone = (tmp_path / "Applications" / "CuaDriver.app" /
                  "Contents" / "MacOS" / "cua-driver")
    for binary in (pinned, standalone):
        binary.parent.mkdir(parents=True)
        binary.write_text("fake executable", encoding="utf-8")
        binary.chmod(0o755)

    shim = tmp_path / ".local" / "bin" / "cua-driver"
    shim.parent.mkdir(parents=True)
    shim.symlink_to(standalone)
    foreign_socket = tmp_path / "standalone.sock"
    foreign_socket.write_text("foreign daemon still running", encoding="utf-8")

    monkeypatch.setenv("PATH", str(shim.parent) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.delenv("HERMES_CUA_DRIVER_CMD", raising=False)
    assert shutil.which("cua-driver") == str(shim)
    monkeypatch.setattr(pm, "installed_package",
                        lambda name: SimpleNamespace(binary=pinned))
    monkeypatch.setattr(pm, "ensure", lambda name: None)
    monkeypatch.setattr(pm, "ensure_import", lambda name: None)
    monkeypatch.setattr(backend_module, "sandbox_mcp_invocation", lambda: None)
    monkeypatch.setattr(backend_module, "cua_driver_runtime_contract_status",
                        lambda: {"ready": True})
    monkeypatch.setattr(driver_module, "_resolve_mcp_invocation",
                        lambda binary: (binary, ["mcp"]))
    monkeypatch.setattr(daemon_module, "_validate_cua_driver_app_signature",
                        lambda app: None)
    monkeypatch.setattr(daemon_module._EmbeddedCuaDaemon, "_sanitized_env",
                        lambda self: self.child_env())

    launches, probes = [], []

    def spawn(argv, **kwargs):
        launches.append((argv, kwargs["env"]))
        return SimpleNamespace(stderr=(), poll=lambda: None, wait=lambda **kw: 0)

    def probe(argv, **kwargs):
        probes.append(argv)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(daemon_module.subprocess, "Popen", spawn)
    monkeypatch.setattr(backend_module, "_run_quiet", probe)

    backend = backend_module.CuaDriverBackend(permission_mode="standard")
    private = backend._embedded_daemon
    assert private is not None, "standard mode must not attach to the global daemon"
    monkeypatch.setattr(backend._session, "start", lambda: None)
    monkeypatch.setattr(backend._session, "call_tool", lambda *args: None)

    try:
        backend.start()
        assert driver_module.resolve_cua_driver_cmd() == str(pinned)
        assert private._command == str(pinned)
        assert private.socket_path != str(foreign_socket)
        serve, env = launches[0]
        assert serve[serve.index("--socket") + 1] == private.socket_path
        assert "--permission-mode" in serve and "standard" in serve
        assert "--no-permissions-gate" not in serve
        if serve[0] == "/usr/bin/open":
            assert serve[serve.index("-a") + 1] == str(pinned.parents[2])
            assert str(standalone.parents[2]) not in serve
        else:
            assert serve[0] == str(pinned)
        assert env["HOME"] != str(Path.home())
        command, args = private.proxy_invocation()
        assert command == str(pinned)
        assert args[args.index("--socket") + 1] == private.socket_path
    finally:
        backend.stop()

    socket_probes = [command for command in probes if "--socket" in command]
    assert socket_probes
    assert all(command[0] == str(pinned) for command in probes)
    assert all(command[command.index("--socket") + 1] == private.socket_path
               for command in socket_probes)
    assert foreign_socket.read_text(encoding="utf-8") == "foreign daemon still running"
