"""Named capacity pools, privacy class, MoA preset, shadow receipts."""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.capacity_pools import (
    CapacityLeaseTable,
    build_receipt,
    factory_route,
    normalize_task_capacity,
    systemd_slice_for,
    wrap_spawn_command,
)


@pytest.fixture
def kanban_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from hermes_cli import kanban_db as kb
    kb.init_db()
    return home


@pytest.fixture(autouse=True)
def storage_reserve_ok(monkeypatch):
    from hermes_cli import kanban_db as kb
    monkeypatch.setattr(kb, "_storage_pressure_level", lambda path="/workspace": "ok")


def test_normalize_rejects_unknown_privacy():
    try:
        normalize_task_capacity(privacy_class="public", capacity_pools=["cpu-batch"])
    except ValueError as exc:
        assert "privacy" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_normalize_accepts_known_fields():
    meta = normalize_task_capacity(
        privacy_class="public-oss",
        capacity_pools=["cpu-batch", "provider-groq"],
        moa_preset="coding-free",
    )
    assert meta["privacy_class"] == "public-oss"
    assert meta["capacity_pools"] == ["cpu-batch", "provider-groq"]
    assert meta["moa_preset"] == "coding-free"


def test_lease_table_atomic_all_or_none():
    table = CapacityLeaseTable({"gpu-3080ti-12g": 1, "cpu-batch": 1})
    assert table.acquire("t_a", ["gpu-3080ti-12g", "cpu-batch"]) is True
    assert table.acquire("t_b", ["gpu-3080ti-12g"]) is False
    assert table.held("gpu-3080ti-12g") == 1
    assert table.held("cpu-batch") == 1
    table.release("t_a")
    assert table.held("gpu-3080ti-12g") == 0
    assert table.acquire("t_b", ["gpu-3080ti-12g"]) is True


def test_factory_route_splits_triage_and_coding():
    triage = factory_route("observe")
    coding = factory_route("review")
    assert triage["moa_preset"] == "triage-tiny"
    assert coding["moa_preset"] == "coding-free"
    assert triage["privacy_class"] == "public-oss"
    assert coding["privacy_class"] == "public-oss"
    assert "cpu-batch" in triage["capacity_pools"]
    assert "provider-gemini" not in triage["capacity_pools"]
    assert "provider-gemini" not in coding["capacity_pools"]
    assert coding["capacity_pools"][1] == "provider-groq"
    assert coding["provider_override"] == "moa"


def test_systemd_slice_and_shadow_wrap():
    assert systemd_slice_for(["cpu-interactive"]) == "hermes-interactive.slice"
    assert systemd_slice_for(["cpu-batch"]) == "hermes-batch.slice"
    cmd = ["hermes", "chat", "-q", "x"]
    assert wrap_spawn_command(cmd, ["cpu-batch"], enforce=False) == cmd
    wrapped = wrap_spawn_command(cmd, ["cpu-batch"], enforce=True)
    assert wrapped[0] == "systemd-run"
    assert "--slice=hermes-batch.slice" in wrapped
    assert wrapped[-4:] == cmd


def test_receipt_has_no_secrets_and_records_shadow():
    receipt = build_receipt(
        task_id="t_x",
        privacy_class="public-oss",
        pools=["cpu-batch"],
        moa_preset="triage-tiny",
        load1=4.0,
        nproc=20,
        provider_remaining={"codex_weekly_used_pct": 8, "grok_weekly_used_pct": 13},
        would_block=False,
        shadow=True,
        chosen_model="triage-tiny",
        chosen_provider="moa",
    )
    blob = str(receipt)
    assert "api_key" not in blob.lower()
    assert receipt["shadow"] is True
    assert receipt["fallback"] == "none"
    assert receipt["intended_slice"] == "hermes-batch.slice"


def test_provider_remaining_parses_bars_without_secrets():
    from hermes_cli.capacity_pools import provider_remaining

    def runner(argv):
        if argv and argv[0] == "codexbar":
            return [
                {
                    "provider": "codex",
                    "usage": {
                        "accountEmail": "secret@example.com",
                        "secondary": {"usedPercent": 10},
                        "extraRateWindows": [
                            {"id": "codex-spark", "window": {"usedPercent": 0}},
                            {"id": "codex-spark-weekly", "window": {"usedPercent": 48}},
                        ],
                    },
                }
            ]
        return {
            "providers": [
                {
                    "provider": "grok",
                    "windows": [{"id": "credits", "percentUsed": 14, "percentRemaining": 86}],
                }
            ]
        }

    out = provider_remaining(runner=runner)
    blob = str(out)
    assert "secret@" not in blob
    assert "example.com" not in blob
    assert out["codex_weekly_used_pct"] == 10
    assert out["codex_5h_used_pct"] == 0
    assert out["grok_weekly_used_pct"] == 14


def test_create_task_persists_capacity_metadata(kanban_home):
    from hermes_cli import kanban_db as kb

    with kb.connect() as conn:
        tid = kb.create_task(
            conn,
            title="oss review",
            assignee="alice",
            privacy_class="public-oss",
            capacity_pools=["cpu-batch", "provider-groq"],
            moa_preset="coding-free",
        )
        task = kb.get_task(conn, tid)
    assert task.privacy_class == "public-oss"
    assert task.capacity_pools == ["cpu-batch", "provider-groq"]
    assert task.moa_preset == "coding-free"
    assert task.model_override == "coding-free"
    assert task.provider_override == "moa"


def test_dispatch_shadow_receipt_does_not_block_spawn(
    kanban_home, all_assignees_spawnable, monkeypatch,
):
    from hermes_cli import kanban_db as kb

    monkeypatch.setattr(kb, "_system_compute_sample", lambda: {"nproc": 20, "load1": 4.0})
    monkeypatch.delenv("HERMES_KANBAN_CAPACITY_ENFORCE", raising=False)
    monkeypatch.setattr(
        "hermes_cli.capacity_pools.provider_remaining",
        lambda runner=None: {"codex_weekly_used_pct": 8, "grok_weekly_used_pct": 13},
    )
    spawns = []

    def fake_spawn(task, workspace, board=None):
        spawns.append(task.id)
        return 42

    with kb.connect() as conn:
        kb.create_task(
            conn,
            title="batch",
            assignee="alice",
            privacy_class="public-oss",
            capacity_pools=["cpu-batch"],
            moa_preset="triage-tiny",
        )
        res = kb.dispatch_once(conn, spawn_fn=fake_spawn)

    assert len(spawns) == 1
    assert res.capacity_receipts
    rec = res.capacity_receipts[0]
    assert rec["shadow"] is True
    assert rec["would_block"] is False
    assert rec["fallback"] == "none"
    assert rec["moa_preset"] == "triage-tiny"
    assert rec["broker"]["pinned"] is True
    assert rec["broker"]["model"] == "triage-tiny"
    assert rec["broker"]["applied"] is False


def test_broker_apply_pins_unpinned_task_in_memory(
    kanban_home, all_assignees_spawnable, monkeypatch,
):
    from hermes_cli import kanban_db as kb

    monkeypatch.setenv("HERMES_KANBAN_BROKER_APPLY", "1")
    monkeypatch.setattr(
        "hermes_cli.capacity_pools.provider_remaining",
        lambda runner=None: {"grok_weekly_used_pct": 10},
    )
    seen = []

    def fake_spawn(task, workspace, board=None):
        seen.append((task.model_override, task.provider_override))
        return 42

    with kb.connect() as conn:
        kb.create_task(
            conn,
            title="observe scout ticket",
            assignee="alice",
            privacy_class="public-oss",
        )
        kb.dispatch_once(conn, spawn_fn=fake_spawn)

    assert seen == [("triage-tiny", "moa")]

