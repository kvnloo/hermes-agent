"""Regression for historical gateway actors after room authority handoff (#148257)."""

from types import SimpleNamespace

import pytest

from gateway.hosted_room_discussion import (
    DiscussionValidationError,
    _require_gateway_actor,
)


@pytest.mark.parametrize(
    ("current_id", "historical_id"),
    [
        ("install:example:gateway-store", "install:example"),
        ("install:example", "install:example:gateway-store"),
    ],
)
def test_replay_accepts_gateway_actor_from_other_handoff_id_space(
    current_id: str, historical_id: str
) -> None:
    room = SimpleNamespace(gateway_id=current_id)
    _require_gateway_actor(
        {"kind": "gateway", "id": historical_id},
        room,
        "historical gateway event rejected",
    )


def test_replay_rejects_unrelated_gateway_actor() -> None:
    room = SimpleNamespace(gateway_id="install:example:gateway-store")
    with pytest.raises(DiscussionValidationError, match="historical gateway event rejected"):
        _require_gateway_actor(
            {"kind": "gateway", "id": "install:other"},
            room,
            "historical gateway event rejected",
        )
