"""A model switch on a resumed-not-yet-built session must not be reverted by stale overrides.

#68876 (cold-resume persistence gap): a lazy/deferred resume record restores its
first agent build from ``session["resume_runtime_overrides"]`` whenever they name a
routable provider (``_deferred_build_agent_kwargs`` prefers them over
``model_override``). A ``config.set model`` against that record pinned
``model_override`` but left the stale PRE-switch overrides in place and persisted
nothing — so the first deferred build (or a later reopen) restored the provider the
user switched away from, failing with "No <old provider> credentials found" while
the composer already showed the new pick.
"""

import json
import threading
import types
from contextlib import contextmanager

from tui_gateway import server


class _FakeDB:
    def __init__(self, row):
        self.row, self.meta, self.model = dict(row), None, None

    def get_session(self, key):
        return self.row

    def update_session_meta(self, key, meta, model=None):
        self.meta, self.model = meta, model


def _patch_session_db(monkeypatch, db):
    @contextmanager
    def _ctx(_session):
        yield db

    monkeypatch.setattr(server, "_session_db", _ctx)


def _result(new_model="gpt-5.6-terra", provider="openai-codex", base_url="https://api.example.com/v1", api_mode=""):
    return types.SimpleNamespace(
        new_model=new_model, target_provider=provider, base_url=base_url, api_mode=api_mode,
        api_key="sk-secret", runtime_capabilities=None)


def _deferred_record(overrides, db_row=None):
    session = {
        "agent": None, "resume_session_id": "20260814_175734_d4d172",
        "session_key": "fade618a", "resume_runtime_overrides": overrides,
        "model_override": None, "history_lock": threading.Lock(),
    }
    if db_row is not None:
        session["_session_db"] = db_row
    return session


def test_config_set_model_replaces_stale_resume_runtime_override(monkeypatch):
    """The accepted switch wins over the stale persisted Anthropic runtime."""
    stale = {
        "model_override": {"model": "claude-opus-5", "provider": "anthropic",
                           "base_url": "https://api.anthropic.com", "api_mode": None},
        "provider_override": "anthropic",
        "reasoning_config_override": {"effort": "high"},
    }
    db = _FakeDB({"model_config": json.dumps({"model": "claude-opus-5", "provider": "anthropic"})})
    session = _deferred_record(stale, db)
    _patch_session_db(monkeypatch, db)

    server._pin_session_resume_runtime(session, _result(), persist_global=False)

    overrides = session["resume_runtime_overrides"]
    assert overrides["provider_override"] == "openai-codex"
    assert overrides["model_override"]["model"] == "gpt-5.6-terra"
    assert overrides["model_override"]["provider"] == "openai-codex"
    # The reasoning override rides along: it is a separate session pin.
    assert overrides["reasoning_config_override"] == {"effort": "high"}
    # model_override (the plain pin) matches the accepted pick too.
    assert session["model_override"]["model"] == "gpt-5.6-terra"
    assert session["model_override"]["provider"] == "openai-codex"


def test_config_set_model_persists_non_secret_runtime_identity(monkeypatch):
    """The stored row's model_config carries the switched runtime — never the api_key."""
    db = _FakeDB({"model_config": json.dumps({"model": "claude-opus-5", "provider": "anthropic",
                                               "reasoning_config": {"effort": "high"}})})
    session = _deferred_record({}, db)
    _patch_session_db(monkeypatch, db)

    server._pin_session_resume_runtime(session, _result(), persist_global=False)

    stored = json.loads(db.meta or "{}")
    assert stored["model"] == "gpt-5.6-terra"
    assert stored["provider"] == "openai-codex"
    assert stored["base_url"] == "https://api.example.com/v1"
    # Secrets never reach the row.
    assert "api_key" not in stored
    # Untouched keys survive the merge.
    assert stored["reasoning_config"] == {"effort": "high"}
    assert db.model == "gpt-5.6-terra"


def test_global_switch_leaves_the_stored_row_alone(monkeypatch):
    """A --global switch changes the profile default; the per-session row must keep
    following it rather than pinning the model to this one chat."""
    db = _FakeDB({"model_config": None})
    session = _deferred_record({}, db)
    _patch_session_db(monkeypatch, db)

    server._pin_session_resume_runtime(session, _result(), persist_global=True)

    assert db.meta is None and db.model is None
    assert session.get("resume_runtime_overrides", {}).get("provider_override") is None


def test_apply_model_switch_invokes_the_pin_on_a_deferred_record(monkeypatch):
    """The agent-less resume branch of _apply_model_switch routes through the pin."""
    calls = []
    monkeypatch.setattr(server, "_pin_session_resume_runtime",
                        lambda session, result, persist_global: calls.append((session, persist_global)))
    # This test isolates the pin while the new path also requires a durable marker.
    monkeypatch.setattr(server, "_append_model_switch_marker", lambda *_a, **_kw: None)

    from hermes_cli.model_switch import parse_model_switch_args

    class _Agent:  # satisfies _current_model_runtime's agent branch expectations
        provider, model, base_url, api_key = "anthropic", "claude-opus-5", "", "sk-old"

    def _fake_switch_model(**_kwargs):
        return types.SimpleNamespace(
            success=True, new_model="gpt-5.6-terra", target_provider="openai-codex",
            base_url="", api_mode="", api_key="sk-new", warning_message="", error_message="",
            model_info=None, runtime_capabilities=None)

    session = _deferred_record({})
    session["agent"] = None  # agent-less: the deferred branch must fire
    import hermes_cli.model_switch as ms
    monkeypatch.setattr(ms, "switch_model", _fake_switch_model)

    server._apply_model_switch("sid", session, "gpt-5.6-terra --provider openai-codex",
                               parsed_flags=parse_model_switch_args("gpt-5.6-terra --provider openai-codex"))

    assert len(calls) == 1
    assert calls[0][0] is session



def test_agentless_existing_local_model_switch_persists_runtime_and_marker(monkeypatch, tmp_path):
    """#149870: an established local chat must not acknowledge a memory-only Desktop pick."""
    from hermes_state import SessionDB
    from hermes_cli.model_switch import parse_model_switch_args
    import hermes_cli.model_switch as ms

    db = SessionDB(db_path=tmp_path / "state.db")
    key = "local-" + "f" * 64
    db.create_session(
        session_id=key, source="local", model="old-model",
        model_config={"model": "old-model", "provider": "cmdcode2api",
                      "gateway_runtime": {"provider": "cmdcode2api",
                                          "base_url": "https://old.example/v1"}})
    db.append_message(session_id=key, role="user", content="hello")
    db.append_message(session_id=key, role="assistant", content="prior answer")
    session = {
        "session_key": key, "agent": None, "history_lock": threading.Lock(),
        "history": [{"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "prior answer"}],
        "resume_runtime_overrides": {"provider_override": "cmdcode2api"},
    }
    _patch_session_db(monkeypatch, db)
    monkeypatch.setattr(server, "_ensure_session_db_row", lambda _session: True)
    monkeypatch.setattr(server, "_current_model_runtime",
                        lambda *_args: ("cmdcode2api", "old-model", "", ""))
    monkeypatch.setattr(server, "_expensive_model_confirm", lambda *_args: None)
    monkeypatch.setattr(ms, "switch_model", lambda **_kw: types.SimpleNamespace(
        success=True, new_model="new-model", target_provider="easycliproxyapi_ws",
        base_url="https://new.example/v1", api_mode="chat_completions",
        api_key="sk-secret", runtime_capabilities=None, model_info=None,
        error_message="", warning_message="", usage_notice=""))
    try:
        result = server._apply_model_switch(
            "sid", session, "new-model --provider easycliproxyapi_ws",
            parsed_flags=parse_model_switch_args("new-model --provider easycliproxyapi_ws"),
            persist_override=False, count_switch=False)
        assert result["value"] == "new-model"
        row = db.get_session(key)
        assert row["model"] == "new-model"
        assert SessionDB.session_gateway_runtime(row) == {
            "provider": "easycliproxyapi_ws", "base_url": "https://new.example/v1",
            "api_mode": "chat_completions"}
        rows = [m for m in db.get_messages(key) if m.get("display_kind") == "model_switch"]
        assert len(rows) == 1
        assert "new-model via provider easycliproxyapi_ws" in rows[0]["content"]
        assert len([m for m in session["history"] if m.get("display_kind") == "model_switch"]) == 1
        assert [m["content"] for m in db.get_messages(key)[:2]] == ["hello", "prior answer"]
        assert "sk-secret" not in json.dumps(row)
    finally:
        db.close()
