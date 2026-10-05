"""An installed provider remains usable when the independent built-in store cannot import."""

import socket
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


class BrokenBuiltinMemory(ModuleType):
    def __getattr__(self, name):
        raise ImportError(f"synthetic built-in memory import failure: {name}")


@pytest.mark.parametrize("builtin_broken", [False, True], ids=["healthy-control", "builtin-import-failure"])
def test_installed_provider_initializes_through_real_import(tmp_path, monkeypatch, builtin_broken):
    def offline(sock, address):
        raise AssertionError("memory import consumer must not connect to a service")

    monkeypatch.setattr(socket.socket, "connect", offline)
    monkeypatch.setattr(socket.socket, "connect_ex", offline)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    home = tmp_path / "home"
    plugin = home / "plugins" / "import_consumer"
    plugin.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    (home / "config.yaml").write_text(
        "memory:\n  provider: import_consumer\n  memory_enabled: false\n  user_profile_enabled: false\n",
        encoding="utf-8",
    )
    (plugin / "value.py").write_text("MARKER = 'relative-import-ok'\n", encoding="utf-8")
    (plugin / "__init__.py").write_text('''from agent.memory_provider import MemoryProvider
from .value import MARKER

class FixtureProvider(MemoryProvider):
    name = "import_consumer"
    def is_available(self):
        return True
    def initialize(self, session_id, **kwargs):
        self.observed = (session_id, kwargs["hermes_home"], MARKER)
    def get_tool_schemas(self):
        return []

def register(ctx):
    ctx.register_memory_provider(FixtureProvider())
''', encoding="utf-8")

    from agent import agent_init
    from hermes_cli.config import load_config_readonly

    agent = SimpleNamespace(
        enabled_toolsets=[], disabled_toolsets=[], tools=[], session_id="synthetic-session",
        _session_db=None, session_cwd=None,
        **{f"_{field}": None for field in agent_init._GATEWAY_IDENTITY_PARAMS},
    )
    if builtin_broken:
        monkeypatch.setitem(sys.modules, "tools.memory_tool", BrokenBuiltinMemory("tools.memory_tool"))
    try:
        agent_init._init_memory(agent, load_config_readonly(), False, "gateway")
        assert agent._memory_manager is not None
        provider, = agent._memory_manager.providers
        assert provider.observed == (agent.session_id, str(home), "relative-import-ok")
        assert type(provider).__module__.startswith("_hermes_user_memory.import_consumer__source_")
    finally:
        if agent._memory_manager is not None:
            agent._memory_manager.shutdown_all()
