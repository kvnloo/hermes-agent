"""Legacy borrowed pool errors must be scrubbed when an upgraded install loads auth.json (#71994)."""

from __future__ import annotations

import json
import time

from agent.credential_pool import load_pool


_KEY = "sk-ant-api03-" + "Zq7Wm2Xr9Lk4Pv8Ty3Nb6Hc1Jd5Fg0Se" * 2


def test_loading_legacy_borrowed_row_scrubs_echoed_key_from_auth_json(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("agent.redact._REDACT_ENABLED", False)
    auth_path = tmp_path / "auth.json"
    legacy = {
        "id": "legacy",
        "label": "environment",
        "auth_type": "api_key",
        "priority": 0,
        "source": "env:ANTHROPIC_API_KEY",
        "last_status": "exhausted",
        "last_status_at": time.time(),
        "last_error_reason": f"Invalid API key: {_KEY}",
        "last_error_message": f"Invalid API key: {_KEY}",
    }
    auth_path.write_text(json.dumps({
        "version": 1, "providers": {}, "credential_pool": {"anthropic": [legacy]},
    }))

    pool = load_pool("anthropic")

    assert any(entry.id == "legacy" for entry in pool._entries)
    raw = auth_path.read_text()
    assert _KEY not in raw
    persisted = next(row for row in json.loads(raw)["credential_pool"]["anthropic"]
                     if row["id"] == "legacy")
    assert persisted["last_status"] == "exhausted"
    assert persisted["last_error_reason"].startswith("Invalid API key:")
    assert persisted["last_error_message"].startswith("Invalid API key:")
    assert "access_token" not in persisted
