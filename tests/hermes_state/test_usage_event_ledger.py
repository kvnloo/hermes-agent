"""Per-call usage events preserve event-time analytics across long sessions."""

from hermes_state import SessionDB


def test_incremental_calls_append_immutable_events_across_midnight(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    db.create_session("gateway-long", source="telegram", model="model-a")

    before_midnight = 1_767_225_599.0  # 2025-12-31 23:59:59 UTC
    after_midnight = 1_767_225_601.0   # 2026-01-01 00:00:01 UTC
    for timestamp, tokens in ((before_midnight, 10), (after_midnight, 20)):
        db.update_token_counts(
            "gateway-long",
            input_tokens=tokens,
            output_tokens=1,
            model="model-a",
            billing_provider="openrouter",
            api_call_count=1,
            event_timestamp=timestamp,
            spend_class="unknown",
            paid_spend_usd=None,
        )

    rows = db._conn.execute(
        "SELECT timestamp, source, input_tokens, api_call_count, spend_class "
        "FROM usage_events ORDER BY timestamp"
    ).fetchall()
    assert [r["timestamp"] for r in rows] == [before_midnight, after_midnight]
    assert [r["input_tokens"] for r in rows] == [10, 20]
    assert all(r["source"] == "telegram" for r in rows)
    assert all(r["api_call_count"] == 1 for r in rows)
    assert all(r["spend_class"] == "unknown" for r in rows)

    summary = db._conn.execute(
        "SELECT input_tokens, api_call_count FROM sessions WHERE id = 'gateway-long'"
    ).fetchone()
    assert dict(summary) == {"input_tokens": 30, "api_call_count": 2}
    db.close()


def test_absolute_compatibility_summary_does_not_create_synthetic_event(tmp_path):
    db = SessionDB(tmp_path / "state.db")
    db.create_session("legacy", source="telegram", model="model-a")
    db.update_token_counts(
        "legacy", input_tokens=900, api_call_count=9, absolute=True
    )
    assert db._conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0] == 0
    db.close()
