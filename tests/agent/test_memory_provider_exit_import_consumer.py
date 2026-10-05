"""Compose real provider import with the startup SystemExit containment boundary."""

import socket
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


class BrokenBuiltinMemory(ModuleType):
    def __getattr__(self, name):
        raise ImportError(f"authored built-in import failure: {name}")


@pytest.mark.parametrize("failure", ["SystemExit", "KeyboardInterrupt"])
def test_imported_provider_initialization_exit_contract(tmp_path, monkeypatch, caplog, failure):
    def offline(*_args, **_kwargs):
        pytest.fail("Memory consumer attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", offline)
    monkeypatch.setattr(socket.socket, "connect_ex", offline)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(tmp_path / "empty"))
    monkeypatch.delenv("HERMES_ENABLE_PROJECT_PLUGINS", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "memory:\n  provider: exit_consumer\n  memory_enabled: false\n  user_profile_enabled: false\n"
    )
    plugin = tmp_path / "plugins" / "exit_consumer"
    plugin.mkdir(parents=True)
    marker = tmp_path / "initialized.txt"
    (plugin / "values.py").write_text(
        f"from pathlib import Path\nMARKER = Path({str(marker)!r})\nFAILURE = {failure}\n"
    )
    (plugin / "__init__.py").write_text('''from agent.memory_provider import MemoryProvider
from .values import MARKER, FAILURE

class FixtureProvider(MemoryProvider):
    name = "exit_consumer"
    def is_available(self):
        return True
    def initialize(self, session_id, **kwargs):
        MARKER.write_text(session_id)
        raise FAILURE("authored initialization stop")
    def get_tool_schemas(self):
        return []

def register(ctx):
    ctx.register_memory_provider(FixtureProvider())
''')

    from agent import agent_init
    from hermes_cli.config import load_config_readonly

    agent = SimpleNamespace(
        enabled_toolsets=[], disabled_toolsets=[], tools=[], session_id="synthetic-session",
        _session_db=None, session_cwd=None,
        **{f"_{field}": None for field in agent_init._GATEWAY_IDENTITY_PARAMS},
    )
    monkeypatch.setitem(sys.modules, "tools.memory_tool", BrokenBuiltinMemory("tools.memory_tool"))
    try:
        if failure == "KeyboardInterrupt":
            with pytest.raises(KeyboardInterrupt, match="authored initialization stop"):
                agent_init._init_memory(agent, load_config_readonly(), False, "gateway")
        else:
            agent_init._init_memory(agent, load_config_readonly(), False, "gateway")
            assert agent._memory_manager is None
            assert "Memory provider plugin init failed: authored initialization stop" in caplog.text
        assert marker.read_text() == agent.session_id
    finally:
        if agent._memory_manager is not None:
            agent._memory_manager.shutdown_all()
