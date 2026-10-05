"""Real plugin discovery and dispatch for the published post-admission hook.

This exercises the hook helper, not message admission or adapter delivery.
"""

import json
import socket
import textwrap
from types import SimpleNamespace

import pytest


def _write_plugin(home, name, source):
    plugin = home / "plugins" / name
    plugin.mkdir(parents=True)
    (plugin / "plugin.yaml").write_text(
        f"name: {name}\nversion: 1.0.0\nkind: standalone\n"
    )
    (plugin / "__init__.py").write_text(textwrap.dedent(source))
    return plugin


@pytest.mark.asyncio
@pytest.mark.parametrize("broken_import", [False, True], ids=["loaded", "import-failure"])
async def test_loaded_post_admission_hook_and_import_failure(tmp_path, monkeypatch, broken_import):
    def deny_network(*_args, **_kwargs):
        pytest.fail("Consumer fixture attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(tmp_path / "empty"))
    monkeypatch.delenv("HERMES_ENABLE_PROJECT_PLUGINS", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "plugins:\n  enabled: [consumer, ordinary]\n"
    )
    calls = tmp_path / "calls.jsonl"
    plugin = _write_plugin(tmp_path, "consumer", '''\
        import json
        from .values import CALLS

        def consume(session_key, platform, source, message_id, text):
            with CALLS.open("a") as handle:
                handle.write(json.dumps([session_key, platform, source, message_id, text]) + "\\n")
            return {"action": "handled", "reply": "Queued locally."}

        def register(ctx):
            ctx.register_hook("post_gateway_admission", consume)
    ''')
    (plugin / "values.py").write_text(
        'raise ImportError("authored fixture import failure")\n' if broken_import else
        f"from pathlib import Path\nCALLS = Path({str(calls)!r})\n"
    )
    _write_plugin(tmp_path, "ordinary", '''\
        def observe(session_id):
            return {"context": "ordinary:" + session_id}

        def register(ctx):
            ctx.register_hook("pre_llm_call", observe)
    ''')

    from gateway.config import Platform
    from gateway.platforms.event import MessageEvent
    from gateway.run_inbound_consumer import run_post_admission_hook
    from gateway.session import SessionSource
    from hermes_cli.lifecycle import ainvoke_hook
    from hermes_cli.plugins import get_plugin_manager

    manager = get_plugin_manager()
    source = SessionSource(platform=Platform.TELEGRAM, chat_id="synthetic-chat", user_id="synthetic-user")
    event = MessageEvent(text="queue report", message_id="synthetic-message", source=source)
    runner = SimpleNamespace(config=SimpleNamespace(multiplex_profiles=False))
    try:
        manager.discover_and_load()
        result = await run_post_admission_hook(runner, event, source, "synthetic-session")
        if broken_import:
            assert result == (False, None)
            assert not calls.exists()
        else:
            assert result == (True, "Queued locally.")
            assert [json.loads(line) for line in calls.read_text().splitlines()] == [[
                "synthetic-session", "telegram", source.to_dict(),
                "synthetic-message", "queue report",
            ]]
        assert await ainvoke_hook("pre_llm_call", session_id="ordinary-session") == [
            {"context": "ordinary:ordinary-session"}
        ]
    finally:
        manager.unload()
