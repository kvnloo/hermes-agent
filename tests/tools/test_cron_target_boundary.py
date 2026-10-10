"""Transport-free owner review composition for PR #135952 / issue #135942.

The native IRC adapter supports channel and nick destinations. A scoped parser
experiment must retain those forms without widening Telegram or plugin syntax.
This is evidence only; the optional diagnostic harness changes no source file.
"""

import pytest

from cron import jobs
from cron.scheduler_delivery import _resolve_single_delivery_target
from tests.tools.test_cron_deferred_delivery_validation import (
    _dispatch,
    delivery_home as delivery_home,
)


def _arguments(action, lane, target, seed):
    args = {lane: target, "name": "Boundary composition"}
    if action == "create":
        args.update(prompt="Check status", schedule="every hour", paused=True)
    else:
        args["job_id"] = seed["job_id"]
    return args


def _seed():
    result = _dispatch(
        "create", prompt="Check status", schedule="every hour", paused=True,
        deliver="local",
    )
    assert result["success"] is True, result
    return result


@pytest.mark.parametrize("action", ["create", "update"])
@pytest.mark.parametrize("lane", ["deliver", "failure_deliver"])
@pytest.mark.parametrize(
    "target,chat_id,thread_id",
    [
        ("irc:#future-room", "#future-room", None),
        ("irc:future-nick", "future-nick", None),
        ("telegram:-1001234567890:17585", "-1001234567890", "17585"),
    ],
)
def test_native_and_explicit_targets_remain_schedulable(
    delivery_home, action, lane, target, chat_id, thread_id,
):
    fire_target = _resolve_single_delivery_target({}, target)
    assert fire_target["chat_id"] == chat_id
    assert fire_target["thread_id"] == thread_id
    seed = _seed()
    result = _dispatch(action, **_arguments(action, lane, target, seed))
    assert result["success"] is True, result
    stored = jobs.get_job(result["job_id"] if action == "create" else seed["job_id"])
    assert stored[lane] == target


@pytest.mark.parametrize("action", ["create", "update"])
@pytest.mark.parametrize("lane", ["deliver", "failure_deliver"])
@pytest.mark.parametrize(
    "bad_target",
    [
        "irc:#future room",  # standalone sender's single-token preflight rejects spaces
        "irc:#future\x00room",  # the same native preflight rejects NUL
        "telegram:not-a-chat",  # neither explicit Telegram syntax nor a directory match
        "strict-target:stream:5:daily",  # frozen plugin parser does not recognize this form
        "strict-target:stream:13/daily",  # parser succeeds; final validator rejects channel 13
    ],
)
def test_invalid_second_target_rejects_atomically(
    delivery_home, action, lane, bad_target,
):
    seed = _seed()
    store = delivery_home / "cron" / "jobs.json"
    before = store.read_bytes()
    target = f"telegram:-1001234567890:17585,{bad_target}"
    result = _dispatch(action, **_arguments(action, lane, target, seed))
    assert result["success"] is False, result
    assert bad_target in result["error"]
    assert store.read_bytes() == before


@pytest.mark.parametrize("action", ["create", "update"])
@pytest.mark.parametrize("lane", ["deliver", "failure_deliver"])
def test_native_irc_first_does_not_hide_telegram_rejection(delivery_home, action, lane):
    seed = _seed()
    store = delivery_home / "cron" / "jobs.json"
    before = store.read_bytes()
    target = "irc:#future-room,telegram:not-a-chat"
    result = _dispatch(action, **_arguments(action, lane, target, seed))
    assert result["success"] is False, result
    assert "telegram:not-a-chat" in result["error"]
    assert store.read_bytes() == before
