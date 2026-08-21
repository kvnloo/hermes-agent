from __future__ import annotations

import json
from dataclasses import replace

import pytest

from plugins.platforms.telegram.mode_router import (
    RouterError,
    TelegramModeRouter,
    default_slots,
)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def router(tmp_path, *, enabled=True):
    clock = Clock()
    value = TelegramModeRouter(tmp_path / "router.json", "42", enabled=enabled, clock=clock)
    value.bind_captain_dm("42", "42")
    return value, clock


def enroll(value, slot="company.bridge", *, nonce=None, user="42", origin="captain_dm", **overrides):
    nonce = nonce or value.begin_enrollment("42", slot)
    args = dict(chat_id="-1001", thread_id="7", chat_type="supergroup", is_forum=True, is_private=True, captain_is_admin=True, origin=origin)
    args.update(overrides)
    return value.complete_enrollment(user, nonce, **args)


def test_schema_defaults_are_disabled_and_use_only_canonical_profiles():
    slots = default_slots()
    assert all(not slot.enabled for slot in slots.values())
    assert {slot.profile for slot in slots.values()} <= {None, "chiefstaff", "starwars"}
    assert slots["feeds.youtube_chat"].modes.to_wire() == {
        "chat.type": "feed", "work.mode": "directed", "updates.mode": "summary", "feed.mode": "summary", "authority": "observe",
    }


def test_modes_are_orthogonal_validated_and_unknowns_fail_closed(tmp_path):
    value, _ = router(tmp_path)
    with pytest.raises(RouterError):
        value.set_modes("42", "captain_dm", {"work.mode": "focused"})
    with pytest.raises(RouterError):
        value.set_modes("42", "captain_dm", {"mystery": "x"})
    with pytest.raises(RouterError):
        value.set_modes("42", "captain_dm", {"feed.mode": "continuous"})
    with pytest.raises(RouterError, match="RECORDED_NOT_ACTIVE"):
        value.set_modes("42", "captain_dm", {"work.mode": "autonomous"})


def test_override_expires_and_restart_is_safe(tmp_path):
    value, clock = router(tmp_path)
    value.set_modes("42", "captain_dm", {"updates.mode": "silent"}, ttl_seconds=30)
    assert value.effective_modes("captain_dm").updates_mode.value == "silent"
    reloaded = TelegramModeRouter(value.state_path, "42", enabled=True, clock=clock)
    assert reloaded.effective_modes("captain_dm").updates_mode.value == "silent"
    clock.now += 31
    assert reloaded.effective_modes("captain_dm").updates_mode.value == "milestone"


def test_wrong_owner_and_group_change_without_confirmation_are_rejected(tmp_path):
    value, _ = router(tmp_path)
    with pytest.raises(RouterError, match="owner"):
        value.begin_enrollment("7", "company.bridge")
    with pytest.raises(RouterError, match="confirmation"):
        value.set_modes("42", "company.bridge", {"updates.mode": "summary"})


@pytest.mark.parametrize("field,bad", [
    ("chat_type", "group"), ("is_forum", False), ("is_private", False), ("captain_is_admin", False),
])
def test_enrollment_requires_admin_private_forum_supergroup(tmp_path, field, bad):
    value, _ = router(tmp_path)
    nonce = value.begin_enrollment("42", "company.bridge")
    kwargs = {field: bad}
    with pytest.raises(RouterError):
        enroll(value, nonce=nonce, **kwargs)


def test_enrollment_must_be_approved_from_dm_and_nonce_is_one_time(tmp_path):
    value, _ = router(tmp_path)
    nonce = value.begin_enrollment("42", "company.bridge")
    with pytest.raises(RouterError, match="Captain DM"):
        enroll(value, nonce=nonce, origin="group")
    enroll(value, nonce=nonce)
    with pytest.raises(RouterError, match="replayed"):
        enroll(value, nonce=nonce)


def test_expired_nonce_and_duplicate_binding_fail(tmp_path):
    value, clock = router(tmp_path)
    nonce = value.begin_enrollment("42", "company.bridge", ttl_seconds=30)
    clock.now += 31
    with pytest.raises(RouterError, match="expired"):
        enroll(value, nonce=nonce)
    enroll(value, "company.bridge")
    nonce2 = value.begin_enrollment("42", "company.reviews")
    with pytest.raises(RouterError, match="already enrolled"):
        enroll(value, "company.reviews", nonce=nonce2)


def test_unknown_chat_wrong_topic_non_captain_bot_and_spoof_are_silent(tmp_path):
    value, _ = router(tmp_path)
    enroll(value)
    assert value.route(user_id="42", chat_id="-999", thread_id="7", message_id="1", text="hello").reason == "unknown-chat-or-topic"
    assert value.route(user_id="42", chat_id="-1001", thread_id="8", message_id="1", text="hello").reason == "unknown-chat-or-topic"
    assert value.route(user_id="9", chat_id="-1001", thread_id="7", message_id="1", text="hello").reason == "untrusted-non-captain"
    assert value.route(user_id="42", chat_id="-1001", thread_id="7", message_id="1", text="hello", sender_is_bot=True).reason == "bot-loop-blocked"
    assert value.route(user_id="42", chat_id="-1001", thread_id="7", message_id="1", text="@mbp execute").reason == "unknown-or-inactive-persona"
    assert value.route(user_id="42", chat_id="-1001", thread_id="7", message_id="2", text="@secondmate pretend").reason == "unknown-or-inactive-persona"


def test_route_receipt_attribution_dedupe_rate_and_no_body_in_audit(tmp_path):
    value, _ = router(tmp_path)
    enroll(value)
    decision = value.route(user_id="42", chat_id="-1001", thread_id="7", message_id="1", text="private body")
    assert decision.accepted
    assert decision.visible_attribution == "[First Mate · chiefstaff]"
    assert decision.receipt == {"profile": "chiefstaff", "lane": "company", "request_id": decision.request_id, "node": "verified-local"}
    assert value.route(user_id="42", chat_id="-1001", thread_id="7", message_id="1", text="again").reason == "duplicate"
    for index in range(2, 13):
        assert value.route(user_id="42", chat_id="-1001", thread_id="7", message_id=str(index), text="x").accepted
    assert value.route(user_id="42", chat_id="-1001", thread_id="7", message_id="13", text="x").reason == "rate-limited"
    assert "private body" not in value.state_path.read_text()


def test_freeze_resume_are_reversible_and_lower_authority(tmp_path):
    value, _ = router(tmp_path)
    enroll(value)
    value.freeze("42", "company.bridge", confirmed=True)
    modes = value.effective_modes("company.bridge")
    assert modes.work_mode.value == "frozen"
    assert modes.authority.value == "observe"
    value.resume("42", "company.bridge", confirmed=True)
    assert value.effective_modes("company.bridge").work_mode.value == "directed"


def test_corrupt_and_unknown_profile_state_fail_closed(tmp_path):
    path = tmp_path / "router.json"
    path.write_text("not json")
    with pytest.raises(RouterError, match="disabled"):
        TelegramModeRouter(path, "42", enabled=True)

    value, _ = router(tmp_path / "other")
    raw = json.loads(value.state_path.read_text())
    raw["slots"]["captain_dm"]["profile"] = "mbp"
    value.state_path.write_text(json.dumps(raw))
    with pytest.raises(RouterError, match="disabled"):
        TelegramModeRouter(value.state_path, "42", enabled=True)


def test_disabled_candidate_preserves_existing_dm_path(tmp_path):
    value, _ = router(tmp_path, enabled=False)
    assert value.route(user_id="42", chat_id="42", thread_id=None, message_id="1", text="hello").reason == "router-disabled"
