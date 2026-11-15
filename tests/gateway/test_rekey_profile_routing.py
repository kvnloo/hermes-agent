"""In-memory routing rekey for `hermes profile rename`.

The routing index lives in ``SessionStore._entries`` and is written back periodically, so a durable
DB rewrite alone is clobbered — the live store must rekey its in-memory copy too. This is why a
renamed profile's old namespace kept resurfacing until the gateway restarted.
"""
from __future__ import annotations


def _make_store(tmp_path):
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    store = SessionStore(
        sessions_dir,
        GatewayConfig(sessions_dir=sessions_dir, write_sessions_json=False,
                      multiplex_profiles=True),
    )
    store._ensure_loaded()
    return store


def _entry(session_key, chat_id, profile):
    from gateway.session import SessionEntry, SessionSource, Platform
    from gateway.session_lifecycle import _now
    now = _now()
    return SessionEntry(
        session_key=session_key, session_id=f"sid-{chat_id}",
        platform=Platform.FEISHU, chat_type="dm", created_at=now, updated_at=now,
        origin=SessionSource(platform=Platform.FEISHU, chat_id=chat_id, profile=profile),
    )


def test_rekeys_old_namespace_and_origin_profile(tmp_path):
    store = _make_store(tmp_path)
    with store._lock:
        store._entries["agent:oldname:feishu:dm:chatA"] = _entry(
            "agent:oldname:feishu:dm:chatA", "chatA", "oldname")
        store._entries["agent:keepme:feishu:dm:chatB"] = _entry(
            "agent:keepme:feishu:dm:chatB", "chatB", "keepme")

    moved = store.rekey_profile_routing("oldname", "newname")
    assert moved == 1

    assert "agent:oldname:feishu:dm:chatA" not in store._entries
    new_entry = store._entries["agent:newname:feishu:dm:chatA"]
    assert new_entry.session_key == "agent:newname:feishu:dm:chatA"
    assert new_entry.origin.profile == "newname"
    # Bystander namespace untouched.
    assert store._entries["agent:keepme:feishu:dm:chatB"].origin.profile == "keepme"


def test_does_not_overwrite_existing_new_namespace_key(tmp_path):
    store = _make_store(tmp_path)
    with store._lock:
        store._entries["agent:oldname:feishu:dm:chatA"] = _entry(
            "agent:oldname:feishu:dm:chatA", "chatA", "oldname")
        # A collision on the target key (should not happen in practice) is left alone.
        store._entries["agent:newname:feishu:dm:chatA"] = _entry(
            "agent:newname:feishu:dm:chatA", "chatA", "newname")

    import pytest
    with pytest.raises(ValueError, match="routing collision"):
        store.rekey_profile_routing("oldname", "newname")
    assert "agent:oldname:feishu:dm:chatA" in store._entries
    assert "agent:newname:feishu:dm:chatA" in store._entries

def test_rename_repins_live_native_and_cross_routed_chats(tmp_path):
    store = _make_store(tmp_path)
    own = _entry("agent:oldname:feishu:dm:a", "a", "oldname")
    own.transport_profile = "oldname"
    forwarded = _entry("agent:satellite:feishu:dm:b", "b", "satellite")
    forwarded.transport_profile = "oldname"
    bystander = _entry("agent:satellite:feishu:dm:c", "c", "satellite")
    bystander.transport_profile = "other"
    with store._lock:
        store._entries.update({
            own.session_key: own,
            forwarded.session_key: forwarded,
            bystander.session_key: bystander,
        })

    assert store.rekey_profile_routing("oldname", "newname") == 1
    assert "agent:oldname:feishu:dm:a" not in store._entries
    native = store._entries["agent:newname:feishu:dm:a"]
    assert native.origin.profile == "newname"
    assert native.transport_profile == "newname"
    cross_route = store._entries["agent:satellite:feishu:dm:b"]
    assert cross_route.origin.profile == "satellite"
    assert cross_route.transport_profile == "newname"
    assert store._entries["agent:satellite:feishu:dm:c"].transport_profile == "other"
