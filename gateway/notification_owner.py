"""Gateway-internal owner route for durable session notifications."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from gateway.config import Platform
from gateway.session import SessionSource
from gateway.slash_access import policy_for_source
from session_notifications import SessionNotification, SessionNotificationStore


@dataclass(frozen=True, slots=True)
class _VerifiedOwnerPrincipal:
    platform: str
    user_id: str
    chat_id: str
    profile_name: str
    session_key: str
    generation: int

    def audit_binding(self) -> str:
        return json.dumps(
            {
                "platform": self.platform,
                "user_id_digest": hashlib.sha256(self.user_id.encode()).hexdigest()[:16],
                "chat_id_digest": hashlib.sha256(self.chat_id.encode()).hexdigest()[:16],
                "profile_name": self.profile_name,
                "session_key_digest": hashlib.sha256(self.session_key.encode()).hexdigest()[:16],
                "generation": self.generation,
            },
            sort_keys=True,
            separators=(",", ":"),
        )


class GatewayNotificationOwnerService:
    """Use the gateway's authenticated admin route; never accept actor objects."""

    def __init__(
        self,
        *,
        db_path: Path,
        gateway_config,
        authorize: Callable[[SessionSource], bool],
        session_key_for_source: Callable[[SessionSource], str],
        current_generation: Callable[[str], int],
    ) -> None:
        self._db_path = Path(db_path)
        self._config = gateway_config
        self._authorize = authorize
        self._session_key_for_source = session_key_for_source
        self._current_generation = current_generation

    def _principal(self, source: SessionSource) -> _VerifiedOwnerPrincipal | None:
        if type(source) is not SessionSource or source.platform is not Platform.TELEGRAM:
            return None
        if not source.user_id or not source.chat_id or not self._authorize(source):
            return None
        policy = policy_for_source(self._config, source)
        # Owner operations require an explicitly configured admin.  The normal
        # backward-compatible "gating disabled" behavior is intentionally not
        # authority for reading this private ledger.
        if not policy.enabled or not policy.is_admin(source.user_id):
            return None
        session_key = self._session_key_for_source(source)
        generation = int(self._current_generation(session_key))
        return _VerifiedOwnerPrincipal(
            platform=source.platform.value,
            user_id=str(source.user_id),
            chat_id=str(source.chat_id),
            profile_name=str(source.profile or "default"),
            session_key=session_key,
            generation=generation,
        )

    def list_pending(self, source: SessionSource, *, limit: int = 100) -> list[SessionNotification] | None:
        principal = self._principal(source)
        if principal is None:
            return None
        rows = SessionNotificationStore(self._db_path)._list_pending(
            profile_name=principal.profile_name,
            session_key=principal.session_key,
            generation=principal.generation,
            limit=limit,
        )
        if self._principal(source) != principal:
            return None
        return rows

    def fetch(self, source: SessionSource, notification_id: str) -> SessionNotification | None:
        principal = self._principal(source)
        if principal is None:
            return None
        row = SessionNotificationStore(self._db_path)._fetch(
            notification_id,
            profile_name=principal.profile_name,
            session_key=principal.session_key,
            generation=principal.generation,
        )
        # Authorization and generation are live capabilities, not a snapshot.
        # Recheck after the ledger read before releasing private metadata.
        current = self._principal(source)
        if current != principal:
            return None
        return row

    def acknowledge(self, source: SessionSource, notification_id: str) -> bool:
        principal = self._principal(source)
        if principal is None:
            return False
        return SessionNotificationStore(self._db_path)._acknowledge(
            notification_id,
            profile_name=principal.profile_name,
            session_key=principal.session_key,
            generation=principal.generation,
            identity_binding=principal.audit_binding(),
            still_authorized=lambda: self._principal(source) == principal,
        )
