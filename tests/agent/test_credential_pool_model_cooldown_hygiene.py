"""Model-cooldown hygiene at the pool/store boundary: legacy benches are bounded on disk, and
elapsed cooldowns neither survive a flush nor cost a store read per selection."""
from __future__ import annotations

import json
import time

import pytest

from agent.credential_pool_model_cooldowns import MODEL_ENTITLEMENT_BENCH_SECONDS

MODEL = "gpt-5.3-codex"
YEAR = 365 * 24 * 60 * 60


@pytest.fixture
def home(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    root.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(root))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("hermes_cli.auth._import_codex_cli_tokens", lambda: None)

    def write(cooldowns: dict[str, float]):
        (root / "auth.json").write_text(json.dumps({"version": 1, "credential_pool": {"openai-codex": [{
            "id": "cred-1", "label": "acct", "auth_type": "api_key", "priority": 0, "source": "manual",
            "access_token": "tok-1", "last_status": "ok", "model_cooldowns": cooldowns,
        }]}}))

    return write


def _disk_cooldowns() -> dict[str, float]:
    from hermes_cli.auth import read_credential_pool
    (row,) = read_credential_pool("openai-codex")
    return row.get("model_cooldowns") or {}


def test_legacy_year_long_bench_is_bounded_on_disk_not_only_in_memory(home):
    """The merge keeps the later value per model, so the bound must reach the disk side too."""
    home({MODEL: time.time() + YEAR})
    from agent.credential_pool import load_pool

    pool = load_pool("openai-codex")
    pool._persist()
    on_disk = _disk_cooldowns()[MODEL]
    assert on_disk <= time.time() + MODEL_ENTITLEMENT_BENCH_SECONDS + 5

    # A second process loading the bounded row keeps the same deadline instead of re-extending it.
    again = load_pool("openai-codex")
    again._persist()
    assert _disk_cooldowns()[MODEL] == pytest.approx(on_disk, abs=1)


def test_genuine_provider_window_below_the_sentinel_is_left_alone(home):
    until = time.time() + 10 * 24 * 60 * 60
    home({MODEL: until})
    from agent.credential_pool import load_pool

    load_pool("openai-codex")._persist()
    assert _disk_cooldowns()[MODEL] == pytest.approx(until, abs=1)


def test_expired_model_cooldown_is_pruned_and_costs_no_store_read(home, monkeypatch):
    home({MODEL: time.time() - 3600})
    from agent.credential_pool import load_pool
    import agent.credential_pool_cooldowns as cooldowns

    pool = load_pool("openai-codex")
    reads = []
    real = cooldowns.read_pool_rows_by_id
    monkeypatch.setattr(cooldowns, "read_pool_rows_by_id", lambda p: reads.append(p) or real(p))

    assert pool.select(model=MODEL) is not None  # prunes the elapsed cooldown on first sight
    reads.clear()
    for _ in range(3):
        assert pool.select(model=MODEL) is not None
        assert pool.has_available() and pool.next_available_at() is None
    assert reads == []
    assert _disk_cooldowns() == {}

@pytest.mark.parametrize("peer_entitled", (True, False))
def test_stale_flush_keeps_peer_model_cooldown_classification(home, tmp_path, peer_entitled):
    """An older writer cannot relabel a peer's newer model cooldown as entitlement or rate-limit."""
    from agent.credential_pool import load_pool
    from agent.credential_pool_model_cooldowns import MODEL_ENTITLEMENT_KEY
    from hermes_cli.auth import read_credential_pool

    older = time.time() + 3600
    newer = older + 1800
    home({MODEL: older})
    path = tmp_path / "hermes" / "auth.json"
    store = json.loads(path.read_text())
    row = store["credential_pool"]["openai-codex"][0]
    row[MODEL_ENTITLEMENT_KEY] = {MODEL: older}
    path.write_text(json.dumps(store))
    stale = load_pool("openai-codex")

    # A second process records a newer denial before the first process flushes.
    store = json.loads(path.read_text())
    row = store["credential_pool"]["openai-codex"][0]
    row["model_cooldowns"][MODEL] = newer
    if peer_entitled:
        row[MODEL_ENTITLEMENT_KEY][MODEL] = newer
    else:
        row.pop(MODEL_ENTITLEMENT_KEY, None)
    path.write_text(json.dumps(store))
    stale._persist()

    (saved,) = read_credential_pool("openai-codex")
    assert saved["model_cooldowns"][MODEL] == pytest.approx(newer)
    assert saved.get(MODEL_ENTITLEMENT_KEY, {}).get(MODEL) == (
        newer if peer_entitled else None
    )
    fresh = load_pool("openai-codex")
    assert fresh.select(model=MODEL) is None
    state = fresh.limit_state([MODEL])
    assert state and state.get("not_entitled", []) == ([MODEL] if peer_entitled else [])
