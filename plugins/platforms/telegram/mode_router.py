"""Disabled-by-default single-token Telegram operating-mode router.

This module owns policy and durable state only.  It never reads a bot token and
never creates chats/topics.  The Telegram adapter may opt into it after an
operator supplies an explicit config and Captain completes enrollment.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

SCHEMA_VERSION = 1


class RouterError(ValueError):
    """A fail-closed router policy error."""


class ChatType(str, Enum):
    CAPTAIN = "captain"
    FOCUS = "focus"
    PRODUCT = "product"
    COUNCIL = "council"
    OPERATIONS = "operations"
    FEED = "feed"


class ConversationMode(str, Enum):
    BRAINSTORM = "brainstorm"
    PORTFOLIO = "portfolio"
    COPILOT = "copilot"
    COUNCIL = "council"


class WorkMode(str, Enum):
    AUTONOMOUS = "autonomous"
    DIRECTED = "directed"
    FROZEN = "frozen"


class UpdatesMode(str, Enum):
    CONTINUOUS = "continuous"
    SUMMARY = "summary"
    MILESTONE = "milestone"
    SILENT = "silent"


class FeedMode(str, Enum):
    CONTINUOUS = "continuous"
    SUMMARY = "summary"
    HYBRID = "hybrid"
    OFF = "off"


class Authority(str, Enum):
    OBSERVE = "observe"
    DRAFT = "draft"
    EXECUTE_LOCAL = "execute-local"
    EXTERNAL_GATED = "external-gated"


@dataclass(frozen=True)
class Modes:
    chat_type: ChatType = ChatType.OPERATIONS
    conversation_mode: ConversationMode = ConversationMode.COPILOT
    work_mode: WorkMode = WorkMode.DIRECTED
    updates_mode: UpdatesMode = UpdatesMode.MILESTONE
    feed_mode: FeedMode = FeedMode.OFF
    authority: Authority = Authority.OBSERVE

    @classmethod
    def parse(cls, raw: Mapping[str, Any], base: "Modes | None" = None) -> "Modes":
        base = base or cls()
        allowed = {"chat.type", "chat.mode", "work.mode", "updates.mode", "feed.mode", "authority"}
        unknown = set(raw) - allowed
        if unknown:
            raise RouterError(f"unknown mode keys: {sorted(unknown)}")
        try:
            modes = cls(
                chat_type=ChatType(raw.get("chat.type", base.chat_type.value)),
                conversation_mode=ConversationMode(raw.get("chat.mode", base.conversation_mode.value)),
                work_mode=WorkMode(raw.get("work.mode", base.work_mode.value)),
                updates_mode=UpdatesMode(raw.get("updates.mode", base.updates_mode.value)),
                feed_mode=FeedMode(raw.get("feed.mode", base.feed_mode.value)),
                authority=Authority(raw.get("authority", base.authority.value)),
            )
        except (TypeError, ValueError) as exc:
            raise RouterError("invalid mode value") from exc
        modes.validate()
        return modes

    def validate(self, *, autonomous_eligible: bool = False) -> None:
        if self.chat_type is ChatType.FEED:
            if self.authority is not Authority.OBSERVE:
                raise RouterError("feed routes are observe-only")
        elif self.feed_mode is not FeedMode.OFF:
            raise RouterError("feed mode is only valid for feed routes")
        if self.work_mode is WorkMode.FROZEN and self.authority in {
            Authority.EXECUTE_LOCAL,
            Authority.EXTERNAL_GATED,
        }:
            raise RouterError("frozen work cannot hold execution authority")
        if self.work_mode is WorkMode.AUTONOMOUS and not autonomous_eligible:
            raise RouterError(
                "autonomous mode has no active governance receipt "
                "(focused governance is RECORDED_NOT_ACTIVE)"
            )

    def to_wire(self) -> dict[str, str]:
        return {
            "chat.type": self.chat_type.value,
            "chat.mode": self.conversation_mode.value,
            "work.mode": self.work_mode.value,
            "updates.mode": self.updates_mode.value,
            "feed.mode": self.feed_mode.value,
            "authority": self.authority.value,
        }


@dataclass(frozen=True)
class RouteSlot:
    key: str
    group: str
    topic: str | None
    modes: Modes
    profile: str | None = "chiefstaff"
    lane: str = "company"
    enabled: bool = False
    chat_id: str | None = None
    thread_id: str | None = None


@dataclass(frozen=True)
class Override:
    values: dict[str, str]
    expires_at: float
    owner_id: str


@dataclass(frozen=True)
class EnrollmentChallenge:
    nonce_hash: str
    slot: str
    expires_at: float
    used: bool = False


@dataclass(frozen=True)
class RouteDecision:
    accepted: bool
    reason: str
    profile: str | None = None
    lane: str | None = None
    request_id: str | None = None
    visible_attribution: str | None = None
    receipt: dict[str, str] | None = None
    session_scope: str | None = None
    conversation_mode: str | None = None


def default_slots() -> dict[str, RouteSlot]:
    def slot(key: str, group: str, topic: str | None, chat: str, *, profile="chiefstaff", lane="company", authority="observe", updates="milestone", feed="off") -> RouteSlot:
        return RouteSlot(key, group, topic, Modes.parse({
            "chat.type": chat, "work.mode": "directed", "updates.mode": updates,
            "feed.mode": feed, "authority": authority,
        }), profile, lane)

    slots = {
        "captain_dm": slot("captain_dm", "Captain DM", None, "captain", authority="external-gated"),
    }
    company = {
        "bridge": ("operations", "execute-local"), "company_council": ("council", "draft"),
        "overnight_operations": ("operations", "execute-local"), "decisions_required": ("operations", "observe"),
        "reviews": ("operations", "observe"), "incidents": ("operations", "observe"),
        "receipts": ("operations", "observe"),
    }
    products = ["hermes3d", "hermes_oss", "keel_mesh", "infrastructure", "content_creative", "products_experiments"]
    feeds = ["youtube_chat", "github_ci", "stream_health", "system_health", "releases"]
    for key, (chat, authority) in company.items():
        slots[f"company.{key}"] = slot(f"company.{key}", "zer0 Company", key.replace("_", " ").title(), chat, authority=authority)
    for key in products:
        slots[f"products.{key}"] = slot(f"products.{key}", "zer0 Products", key.replace("_", " ").title(), "product", lane=key, authority="execute-local")
    # Only an actually canonical lane is eligible to speak.
    slots["products.products_experiments"] = replace(slots["products.products_experiments"], profile="starwars", lane="temple_guard")
    for key in feeds:
        slots[f"feeds.{key}"] = slot(f"feeds.{key}", "zer0 Feeds", key.replace("_", " ").title(), "feed", profile=None, lane=key, updates="summary", feed="summary")
    return slots


class TelegramModeRouter:
    """Policy kernel for an explicitly enabled, single-bot Telegram router."""

    CONTROL_COMMANDS = frozenset({"status", "chat", "work", "updates", "feed", "authority", "freeze", "resume", "mute"})
    PROFILES = frozenset({"chiefstaff", "starwars"})

    def __init__(self, state_path: Path, captain_user_id: str, *, enabled: bool = False, clock: Callable[[], float] = time.time):
        if not captain_user_id:
            raise RouterError("captain_user_id is required")
        self.state_path = Path(state_path)
        self.captain_user_id = str(captain_user_id)
        self.enabled = bool(enabled)
        self.clock = clock
        self.slots = default_slots()
        self.overrides: dict[str, Override] = {}
        self.challenges: dict[str, EnrollmentChallenge] = {}
        self.audit: list[dict[str, Any]] = []
        self._seen: dict[str, float] = {}
        self._rate: dict[str, list[float]] = {}
        self.generation = 0
        self._load()

    def _load(self) -> None:
        if not self.state_path.exists():
            return
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            if raw.get("schema_version") != SCHEMA_VERSION:
                raise RouterError("unsupported router state schema")
            self.generation = int(raw.get("generation", 0))
            for key, value in raw.get("slots", {}).items():
                if key not in self.slots:
                    raise RouterError("unknown persisted route slot")
                slot = self.slots[key]
                modes = Modes.parse(value.get("modes", {}), slot.modes)
                profile = value.get("profile", slot.profile)
                if profile is not None and profile not in self.PROFILES:
                    raise RouterError("unknown persisted profile")
                self.slots[key] = replace(slot, modes=modes, profile=profile, enabled=bool(value.get("enabled", False)), chat_id=value.get("chat_id"), thread_id=value.get("thread_id"))
            self.overrides = {key: Override(dict(v["values"]), float(v["expires_at"]), str(v["owner_id"])) for key, v in raw.get("overrides", {}).items() if key in self.slots}
            self.challenges = {key: EnrollmentChallenge(**v) for key, v in raw.get("challenges", {}).items()}
            self.audit = list(raw.get("audit", []))[-500:]
        except Exception as exc:
            self.enabled = False
            raise RouterError("router state is corrupt; router disabled") from exc

    def _persist(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": SCHEMA_VERSION, "generation": self.generation,
            "slots": {k: {"modes": v.modes.to_wire(), "profile": v.profile, "lane": v.lane, "enabled": v.enabled, "chat_id": v.chat_id, "thread_id": v.thread_id} for k, v in self.slots.items()},
            "overrides": {k: asdict(v) for k, v in self.overrides.items()},
            "challenges": {k: asdict(v) for k, v in self.challenges.items()},
            "audit": self.audit[-500:],
        }
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.state_path.name}.", dir=self.state_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.state_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _owner(self, user_id: str) -> None:
        if not hmac.compare_digest(str(user_id), self.captain_user_id):
            raise RouterError("owner authorization required")

    def _record(self, action: str, *, slot: str, owner: str, detail: Mapping[str, Any] | None = None) -> str:
        receipt = secrets.token_hex(8)
        # Deliberately exclude message bodies, tokens, names and raw nonce values.
        self.audit.append({"at": int(self.clock()), "action": action, "slot": slot, "owner_hash": hashlib.sha256(owner.encode()).hexdigest()[:12], "receipt": receipt, "detail": dict(detail or {})})
        return receipt

    def begin_enrollment(self, user_id: str, slot: str, *, ttl_seconds: int = 600) -> str:
        self._owner(user_id)
        if slot == "captain_dm" or slot not in self.slots:
            raise RouterError("slot cannot be enrolled")
        nonce = secrets.token_urlsafe(24)
        digest = hashlib.sha256(nonce.encode()).hexdigest()
        self.challenges[digest] = EnrollmentChallenge(digest, slot, self.clock() + min(max(ttl_seconds, 30), 900))
        self._record("enrollment-started", slot=slot, owner=str(user_id))
        self._persist()
        return nonce

    def complete_enrollment(self, user_id: str, nonce: str, *, chat_id: str, thread_id: str, chat_type: str, is_forum: bool, is_private: bool, captain_is_admin: bool, origin: str = "captain_dm") -> str:
        self._owner(user_id)
        digest = hashlib.sha256(nonce.encode()).hexdigest()
        challenge = self.challenges.get(digest)
        if not challenge or challenge.used or challenge.expires_at <= self.clock():
            raise RouterError("invalid, expired, or replayed enrollment nonce")
        if origin != "captain_dm":
            raise RouterError("enrollment approval must originate in Captain DM")
        if chat_type != "supergroup" or not is_forum or not is_private or not captain_is_admin:
            raise RouterError("enrollment requires a private forum supergroup administered by Captain")
        if not chat_id or not thread_id:
            raise RouterError("exact chat and topic IDs are required")
        for key, existing in self.slots.items():
            if key != challenge.slot and existing.enabled and (existing.chat_id, existing.thread_id) == (str(chat_id), str(thread_id)):
                raise RouterError("chat/topic binding already enrolled")
        slot = self.slots[challenge.slot]
        self.slots[challenge.slot] = replace(slot, enabled=True, chat_id=str(chat_id), thread_id=str(thread_id))
        self.challenges[digest] = replace(challenge, used=True)
        self.generation += 1
        receipt = self._record("enrollment-completed", slot=challenge.slot, owner=str(user_id), detail={"generation": self.generation})
        self._persist()
        return receipt

    def bind_captain_dm(self, user_id: str, chat_id: str) -> None:
        self._owner(user_id)
        if str(chat_id) != self.captain_user_id:
            raise RouterError("Captain DM must match Captain user ID")
        self.slots["captain_dm"] = replace(self.slots["captain_dm"], enabled=True, chat_id=str(chat_id))
        self.generation += 1
        self._record("captain-dm-bound", slot="captain_dm", owner=str(user_id))
        self._persist()

    def set_modes(self, user_id: str, slot: str, values: Mapping[str, Any], *, ttl_seconds: int | None = None, confirmed: bool = False) -> str:
        self._owner(user_id)
        if slot not in self.slots:
            raise RouterError("unknown slot")
        if slot != "captain_dm" and not confirmed:
            raise RouterError("group/topic changes require confirmation")
        current = self.effective_modes(slot)
        candidate = Modes.parse(values, current)
        if candidate.work_mode is WorkMode.AUTONOMOUS:
            raise RouterError("autonomous governance is RECORDED_NOT_ACTIVE")
        if ttl_seconds is not None:
            ttl = min(max(int(ttl_seconds), 30), 86400)
            self.overrides[slot] = Override(candidate.to_wire(), self.clock() + ttl, str(user_id))
            action = "override-set"
        else:
            self.slots[slot] = replace(self.slots[slot], modes=candidate)
            action = "modes-set"
        self.generation += 1
        receipt = self._record(action, slot=slot, owner=str(user_id), detail={"keys": sorted(values), "generation": self.generation})
        self._persist()
        return receipt

    def effective_modes(self, slot: str) -> Modes:
        if slot not in self.slots:
            raise RouterError("unknown slot")
        override = self.overrides.get(slot)
        if override and override.expires_at > self.clock():
            return Modes.parse(override.values, self.slots[slot].modes)
        if override:
            del self.overrides[slot]
            self._persist()
        return self.slots[slot].modes

    def freeze(self, user_id: str, slot: str, *, confirmed: bool = False) -> str:
        modes = self.effective_modes(slot)
        values = {"work.mode": "frozen", "authority": "observe", "feed.mode": "off" if modes.chat_type is ChatType.FEED else modes.feed_mode.value}
        return self.set_modes(user_id, slot, values, confirmed=confirmed)

    def resume(self, user_id: str, slot: str, *, confirmed: bool = False) -> str:
        return self.set_modes(user_id, slot, {"work.mode": "directed"}, confirmed=confirmed)

    def status(self, user_id: str, slot: str) -> dict[str, Any]:
        self._owner(user_id)
        route = self.slots.get(slot)
        if not route:
            raise RouterError("unknown slot")
        return {"schema_version": SCHEMA_VERSION, "enabled": self.enabled and route.enabled, "slot": slot, "modes": self.effective_modes(slot).to_wire(), "profile": route.profile, "lane": route.lane, "generation": self.generation}

    def route(self, *, user_id: str, chat_id: str, thread_id: str | None, message_id: str, text: str, sender_is_bot: bool = False) -> RouteDecision:
        if not self.enabled:
            return RouteDecision(False, "router-disabled")
        if sender_is_bot:
            return RouteDecision(False, "bot-loop-blocked")
        slot = next((v for v in self.slots.values() if v.enabled and v.chat_id == str(chat_id) and (v.thread_id or None) == (str(thread_id) if thread_id is not None else None)), None)
        if slot is None:
            return RouteDecision(False, "unknown-chat-or-topic")
        if str(user_id) != self.captain_user_id:
            return RouteDecision(False, "untrusted-non-captain")
        key = f"{chat_id}:{thread_id}:{message_id}"
        now = self.clock()
        self._seen = {k: expiry for k, expiry in self._seen.items() if expiry > now}
        if key in self._seen:
            return RouteDecision(False, "duplicate")
        bucket = [stamp for stamp in self._rate.get(slot.key, []) if now - stamp < 60]
        if len(bucket) >= 12:
            return RouteDecision(False, "rate-limited")
        bucket.append(now)
        self._rate[slot.key] = bucket
        self._seen[key] = now + 3600
        profile = self._persona_profile(text, slot)
        if profile is None:
            return RouteDecision(False, "unknown-or-inactive-persona")
        request_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        persona = "First Mate" if profile == "chiefstaff" else "Second Mate · Temple Guard"
        mode = self.effective_modes(slot.key).conversation_mode.value
        return RouteDecision(
            True, "accepted", profile, slot.lane, request_id,
            f"[{persona} · {profile}]",
            {"profile": profile, "lane": slot.lane, "request_id": request_id, "node": "verified-local"},
            f"chat-{mode}",
            mode,
        )

    def _persona_profile(self, text: str, slot: RouteSlot) -> str | None:
        lowered = text.lower()
        if "@mbp" in lowered:
            return None
        if "@secondmate:temple-guard" in lowered:
            return "starwars"
        if "@firstmate" in lowered:
            return "chiefstaff"
        if "@secondmate" in lowered or "@council" in lowered:
            return None
        return slot.profile if slot.profile in self.PROFILES else None
