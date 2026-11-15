"""Retained native quotas preserve profile, approval and delete-recovery contracts."""
import builtins
import json
from pathlib import Path
from types import SimpleNamespace

import hermes_yaml as yaml
import pytest

from agent.agent_init import _init_memory
from hermes_cli.config import load_config_readonly
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools import memory_tool as mt
from tools import memory_tool_store as ms


@pytest.fixture
def profile(tmp_path):
    home = tmp_path / "synthetic-profile"
    home.mkdir()
    token = set_hermes_home_override(home)
    try:
        yield home
    finally:
        reset_hermes_home_override(token)


def config(home, memory=32, user=32, approval=False):
    (home / "config.yaml").write_text(yaml.safe_dump({"memory": {
        "memory_char_limit": memory, "user_char_limit": user,
        "write_approval": approval,
    }}), encoding="utf-8")


def agent():
    obj = SimpleNamespace(enabled_toolsets=["memory"], disabled_toolsets=[], tools=[])
    _init_memory(obj, load_config_readonly(), skip_memory=True, platform="desktop")
    assert obj._memory_store is not None
    return obj


def call(store, **kwargs):
    return json.loads(mt.memory_tool(store=store, **kwargs))


@pytest.mark.parametrize("boundary", ["tool", "replay"])
def test_both_budgets_refresh_on_one_target_call(profile, boundary):
    config(profile)
    store = agent()._memory_store
    config(profile, 128, 96)
    payload = {"target": "memory", "action": "add", "content": "Synthetic fact"}
    result = call(store, **payload) if boundary == "tool" else mt.apply_memory_pending(payload, store)
    assert result["success"], result
    assert (store.memory_char_limit, store.user_char_limit) == (128, 96)


@pytest.mark.parametrize("value", [None, "4096", True, 4096.5])
def test_invalid_one_budget_keeps_last_good_while_other_refreshes(profile, value):
    config(profile, 64, 64)
    store = agent()._memory_store
    config(profile, value, 96)
    assert call(store, target="user", action="add", content="Synthetic fact")["success"]
    assert (store.memory_char_limit, store.user_char_limit) == (64, 96)


def test_config_loader_failure_keeps_both_last_good_budgets(profile, monkeypatch):
    config(profile, 64, 80)
    store = agent()._memory_store
    def unavailable():
        raise OSError("synthetic unreadable config")
    monkeypatch.setattr("hermes_cli.config.load_config_readonly", unavailable)
    assert call(store, target="memory", action="add", content="Synthetic fact")["success"]
    assert (store.memory_char_limit, store.user_char_limit) == (64, 80)


def test_foreign_scope_does_not_adopt_foreign_quota(profile, tmp_path):
    config(profile, 32, 40)
    store = agent()._memory_store
    other = tmp_path / "foreign-profile"
    other.mkdir()
    config(other, 4096, 4096)
    token = set_hermes_home_override(other)
    try:
        # Read-only argument failure exercises the refresh boundary without a cross-home write.
        result = call(store, target="memory", action="add", content="")
        assert not result["success"]
        assert (store.memory_char_limit, store.user_char_limit) == (32, 40)
        assert not (other / "memories").exists()
    finally:
        reset_hermes_home_override(token)


def test_staged_batch_replay_refreshes_both_budgets_and_keeps_pins(profile, monkeypatch):
    from tools import write_approval as wa
    config(profile, 128, 128)
    obj = agent()
    store = obj._memory_store
    assert call(store, target="user", action="add", content="Synthetic original fact")["success"]
    config(profile, 128, 128, approval=True)
    # No interactive channel: exercise the real configured gate, staging and pinning.
    monkeypatch.setattr(wa, "_prompt_inline_memory_approval", lambda *args: None)
    from hermes_cli.config import load_config
    assert load_config()["memory"]["write_approval"] is True
    assert wa.write_approval_enabled(wa.MEMORY)
    staged = call(store, target="user", operations=[
        {"action": "patch", "old_text": "Synthetic original fact", "content": "Short fact"},
        {"action": "add", "content": "Synthetic pending addition " + "x" * 40},
    ])
    assert staged["staged"], staged
    record = wa.list_pending(wa.MEMORY)[0]
    payload = record["payload"]
    assert payload["operations"][0]["matched_entry"] == "Synthetic original fact"
    before = store._path_for("user").read_bytes()
    snapshot = dict(store._system_prompt_snapshot)
    config(profile, 16, 16, approval=True)
    refused = mt.apply_memory_pending(payload, store)
    assert not refused["success"], refused
    assert store._path_for("user").read_bytes() == before
    config(profile, 256, 256, approval=True)
    replay = mt.apply_memory_pending(payload, store)
    assert replay["success"], replay
    assert (store.memory_char_limit, store.user_char_limit) == (256, 256)
    assert store._system_prompt_snapshot == snapshot
    assert before != store._path_for("user").read_bytes()
    # Stale pin remains a refusal even after successful quota refresh.
    payload["operations"][0]["matched_entry"] = "No longer the reviewed entry"
    before = store._path_for("user").read_bytes()
    assert not mt.apply_memory_pending(payload, store)["success"]
    assert store._path_for("user").read_bytes() == before


def _loop_agent(profile, monkeypatch):
    """Real agent + dispatch pipeline; replace only provider construction/discovery."""
    from run_agent import AIAgent

    monkeypatch.setattr("model_tools.get_tool_definitions", lambda **kw: [])
    monkeypatch.setattr("model_tools.check_toolset_requirements", lambda *a, **kw: {})
    monkeypatch.setattr("agent.process_bootstrap.OpenAI", lambda **kw: object())
    monkeypatch.setattr("agent.model_metadata.fetch_model_metadata", lambda *a, **kw: {})
    monkeypatch.setattr("run_agent._hermes_home", profile)
    obj = AIAgent(api_key="synthetic-no-network", base_url="http://127.0.0.1:1/v1",
                  quiet_mode=True, skip_context_files=True, skip_memory=True,
                  enabled_toolsets=["memory"])
    # Exercise the actual prompt builder once, not a stand-in prefix. Dispatch must never rebuild it.
    obj._cached_system_prompt = obj._build_system_prompt()
    monkeypatch.setattr(obj, "_build_system_prompt", lambda *a, **kw: pytest.fail("prompt rebuilt"))
    return obj


def _loop_call(obj, args):
    from agent import tool_executor as te

    ref = te._ToolCallRef("memory", args, "synthetic-task", "synthetic-call", [])
    dispatch = te._resolve_sequential_dispatch(obj, ref, [])
    return te._run_agent_tool_execution_middleware(
        obj, **ref.middleware_kwargs(), execute=dispatch.execute)


@pytest.mark.parametrize("target", ["memory", "user"])
def test_live_quota_through_current_dispatch_and_metrics(profile, monkeypatch, target):
    from hermes_cli.observability import shared_metrics_loop as metrics

    config(profile, 32, 32)
    obj = _loop_agent(profile, monkeypatch)
    store = obj._memory_store
    frozen = (obj._cached_system_prompt, obj._cached_system_prompt_static,
              dict(store._system_prompt_snapshot))
    rows = []
    monkeypatch.setattr(metrics, "_emit", lambda mark, fields, **kw: rows.append((mark, fields(**kw))))
    # Both budgets refresh through middleware -> hosted policy -> inline table -> metrics wrapper.
    config(profile, 128, 96)
    result = _loop_call(obj, {"target": target, "action": "add", "content": "x" * 48})
    assert result.dispatched and not result.blocked
    assert json.loads(result.result)["success"]
    assert (store.memory_char_limit, store.user_char_limit) == (128, 96)
    config(profile, 16, 16)
    before = store._path_for(target).read_bytes()
    refused = json.loads(_loop_call(obj, {"target": target, "action": "add", "content": "more"}).result)
    assert not refused["success"] and store._path_for(target).read_bytes() == before
    shortened = json.loads(_loop_call(obj, {"target": target, "action": "patch",
                                          "old_text": "x" * 48, "content": "short"}).result)
    assert shortened["success"]
    memory_rows = [fields for mark, fields in rows if mark == "MEMORY_OP_MARK"]
    assert [row["outcome"] for row in memory_rows] == ["success", "failed", "success"]
    assert memory_rows[1]["failure_class"] == "over_budget"
    assert obj._memory_store is store
    assert (obj._cached_system_prompt, obj._cached_system_prompt_static,
            store._system_prompt_snapshot) == frozen
    obj.close()


def test_live_quota_through_slash_approval_consumer(profile, monkeypatch):
    from hermes_cli.write_approval_commands import handle_pending_subcommand
    from tools import write_approval as wa

    config(profile, 128, 128, approval=True)
    obj = _loop_agent(profile, monkeypatch)
    store = obj._memory_store
    monkeypatch.setattr(wa, "_prompt_inline_memory_approval", lambda *a: None)
    staged = json.loads(_loop_call(obj, {"target": "user", "action": "add", "content": "x" * 48}).result)
    assert staged["staged"]
    pending_id = staged["pending_id"]
    config(profile, 16, 16, approval=True)
    refused = handle_pending_subcommand(wa.MEMORY, ["approve", pending_id], memory_store=store)
    assert "Approved 0" in refused and "Failed:" in refused
    assert wa.get_pending(wa.MEMORY, pending_id) is not None
    assert store.user_entries == []
    config(profile, 128, 128, approval=True)
    applied = handle_pending_subcommand(wa.MEMORY, ["approve", pending_id], memory_store=store)
    assert "Approved 1" in applied
    assert wa.get_pending(wa.MEMORY, pending_id) is None
    assert store.user_entries == ["x" * 48]
    assert store._system_prompt_snapshot["user"] == ""
    obj.close()


def test_hosted_dispatch_refuses_before_quota_reader(profile, monkeypatch):
    from agent.runtime_scope import bind_state
    from hermes_scope import Principal, Scope

    config(profile, 32, 32)
    obj = _loop_agent(profile, monkeypatch)
    store = obj._memory_store
    config(profile, 128, 128)
    scope = Scope("synthetic-tenant", "synthetic-agent", Principal("synthetic-user"),
                  owner=Principal("synthetic-user"), can_administer=True)
    with monkeypatch.context() as guarded, bind_state(scope):
        guarded.setattr("hermes_cli.config.load_config_readonly",
                        lambda: pytest.fail("hosted call read host config"))
        result = _loop_call(obj, {"action": "add", "content": "never written"})
    assert result.blocked and "not available to a hosted agent" in result.result
    assert (store.memory_char_limit, store.user_char_limit) == (32, 32)
    assert store.memory_entries == [] and not store._path_for("memory").exists()
    obj.close()


@pytest.mark.parametrize("fail_backup", [False, True])
def test_cold_delete_only_keeps_exclusive_backup_or_refuses_without_write(profile, monkeypatch, fail_backup):
    config(profile, 24, 24)
    store = agent()._memory_store
    path = store._path_for("memory")
    raw = "Synthetic oversized entry " + "x" * 70
    path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(ms.time, "time", lambda: 1234567890)
    occupied = path.with_suffix(path.suffix + ".bak.1234567890")
    occupied.write_text("Synthetic existing backup", encoding="utf-8")
    real_open = builtins.open
    if fail_backup:
        def denied(file, mode="r", *args, **kwargs):
            if str(file).startswith(str(path) + ".bak.") and mode == "x":
                raise PermissionError("synthetic backup refusal")
            return real_open(file, mode, *args, **kwargs)
        monkeypatch.setattr(builtins, "open", denied)
    result = call(store, target="memory", action="remove", old_text=raw)
    assert occupied.read_text(encoding="utf-8") == "Synthetic existing backup"
    if fail_backup:
        assert not result["success"], result
        assert path.read_text(encoding="utf-8") == raw
    else:
        assert result["success"], result
        backup = Path(result["drift_backup"])
        assert backup != occupied
        assert backup.read_text(encoding="utf-8") == raw
        assert path.read_text(encoding="utf-8") == ""
