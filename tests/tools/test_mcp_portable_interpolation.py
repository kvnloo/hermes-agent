"""Plugin-provided (portable) MCP servers must get the same ${VAR} interpolation as
native config.yaml entries. Native servers pass through _interpolate_env_vars in
_load_mcp_config(); portable servers were merged after that loop, so their
placeholders reached the spawn path literally and the child failed to start.
"""
from tools import mcp_tool_config as _mcp_config


class _FakePluginManager:
    def __init__(self, servers):
        self._servers = servers

    def get_portable_mcp_servers(self):
        return self._servers


def _patched_load(monkeypatch, native, portable):
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: native)
    monkeypatch.setattr("hermes_cli.plugins.discover_plugins", lambda: None)
    monkeypatch.setattr(
        "hermes_cli.plugins.get_plugin_manager",
        lambda: _FakePluginManager(portable),
    )


def test_portable_mcp_server_interpolates_env_placeholders(monkeypatch):
    """A portable server using ${VAR} in args gets the resolved value, like native entries."""
    monkeypatch.setenv("PORTABLE_GREETING", "hi-from-plugin")
    portable = {"plug": {"command": "echo", "args": ["${PORTABLE_GREETING}"]}}
    _patched_load(monkeypatch, {}, portable)

    result = _mcp_config._load_mcp_config()

    assert result["plug"]["args"] == ["hi-from-plugin"]


def test_native_config_still_wins_over_portable(monkeypatch):
    """Native config keeps precedence; only the interpolation gap changed."""
    monkeypatch.setenv("PORTABLE_GREETING", "hi-from-plugin")
    native = {"srv": {"command": "native-bin", "args": ["${PORTABLE_GREETING}"]}}
    portable = {"srv": {"command": "plug-bin", "args": ["${PORTABLE_GREETING}"]}}
    _patched_load(monkeypatch, {"mcp_servers": native}, portable)

    result = _mcp_config._load_mcp_config()

    assert result["srv"]["command"] == "native-bin"
    assert result["srv"]["args"] == ["hi-from-plugin"]
