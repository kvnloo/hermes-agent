"""Secret-taking CLI flags accept ``-`` so the secret stays out of argv and shell history."""

import io
from types import SimpleNamespace

from hermes_cli import secret_prompt
from hermes_cli.subcommands import peer as peer_cmd


def test_dash_reads_first_stdin_line_and_literal_and_empty_pass_through(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("s3cret-from-pipe\nignored\n"))
    assert secret_prompt.resolve_secret_arg("-", "Key: ") == "s3cret-from-pipe"
    # Not a terminal: no prompt, the caller reports the missing secret.
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert secret_prompt.resolve_secret_arg("", "Key: ") == ""
    assert secret_prompt.resolve_secret_arg(" literal ", "Key: ") == "literal"


def test_peer_add_dash_stores_stdin_key(monkeypatch):
    saved = {}
    monkeypatch.setattr(peer_cmd, "_load_peers", dict)
    monkeypatch.setattr(peer_cmd, "_save_peers", lambda peers: None)
    monkeypatch.setattr("hermes_cli.config.save_env_value", lambda k, v: saved.__setitem__(k, v))
    monkeypatch.setattr("sys.stdin", io.StringIO("peer-key-123456\n"))
    args = SimpleNamespace(peer_action="add", name="spark", url="http://spark.lan:8377", key="-", note="")
    assert peer_cmd.cmd_peer(args) == 0
    assert list(saved.values()) == ["peer-key-123456"]


def test_empty_piped_webhook_secret_refuses_route_rebind(monkeypatch, tmp_path, capsys):
    """An explicit empty --secret - must not silently rotate a saved route."""
    from hermes_cli import webhook

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(webhook, "_is_webhook_enabled", lambda: True)
    named = tmp_path / "profiles" / "work"
    named.mkdir(parents=True)
    (named / "config.yaml").write_text("{}\n", encoding="utf-8")

    base = dict(
        webhook_action="subscribe", name="events", route_profile=None,
        events="", description="", prompt="", skills="", deliver="log",
        deliver_chat_id="", secret="existing-hmac", signature=None,
    )
    webhook.webhook_command(SimpleNamespace(**base))
    previous = webhook._load_subscriptions()["events"].copy()

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    result = webhook.webhook_command(SimpleNamespace(**{
        **base, "route_profile": "work", "secret": "-",
    }))
    assert result == 1
    assert webhook._load_subscriptions()["events"] == previous
    assert "No HMAC secret read from stdin" in capsys.readouterr().out
