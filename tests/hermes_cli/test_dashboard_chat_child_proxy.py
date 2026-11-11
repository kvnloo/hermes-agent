"""The dashboard's spawned Ink client preserves proxy egress but bypasses its local sidecar."""

from pathlib import Path

from hermes_cli import main_tui_launch, web_server_chat
from tools.environments import local as local_env


def test_dashboard_chat_child_bypasses_loopback_proxy(monkeypatch):
    proxy_env = {
        "NODE_USE_ENV_PROXY": "1",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "NO_PROXY": "build.internal",
        "no_proxy": "corp.internal",
    }
    monkeypatch.setattr(local_env, "build_subprocess_env", lambda **_kwargs: dict(proxy_env))
    monkeypatch.setattr(
        main_tui_launch, "_make_tui_argv",
        lambda *_args, **_kwargs: (["node", "fake-tui.js"], Path("/tmp")),
    )
    monkeypatch.setattr(main_tui_launch, "_apply_tui_python_env", lambda _env: None)
    monkeypatch.setattr(
        web_server_chat, "_build_gateway_ws_url",
        lambda: "ws://127.0.0.1:9119/api/ws?token=local",
    )

    sidecar_url = "ws://127.0.0.1:9119/api/pub?channel=chat-1"
    _argv, _cwd, child_env = web_server_chat._resolve_chat_argv(sidecar_url=sidecar_url)

    assert child_env["HERMES_TUI_SIDECAR_URL"] == sidecar_url
    assert child_env["NODE_USE_ENV_PROXY"] == "1"
    for key in ("HTTP_PROXY", "HTTPS_PROXY"):
        assert child_env[key] == proxy_env[key]
    for key, preexisting in (("NO_PROXY", "build.internal"), ("no_proxy", "corp.internal")):
        entries = set(child_env[key].split(","))
        assert preexisting in entries
        assert {"127.0.0.1", "localhost", "::1"} <= entries
