"""Security regression tests: Discord component views honor allowlists.

The interactive component views (ExecApprovalView, SlashConfirmView,
UpdatePromptView, ModelPickerView, ClarifyChoiceView) historically accepted only
``allowed_user_ids``. Deployments that configure DISCORD_ALLOWED_ROLES
without DISCORD_ALLOWED_USERS therefore had a wide-open component
surface: any guild member who could see the prompt could approve exec
commands, cancel slash confirmations, or switch the model -- even when
the same user would be rejected at the slash and on_message gates.

These tests pin user/role/global allowlist semantics, explicit allow-all
handling, and fail-closed behavior so the parity cannot regress.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gateway.config import PlatformConfig

# Trigger the shared discord mock from tests/gateway/conftest.py before
# importing the production module.
from plugins.platforms.discord.adapter import (
    ClarifyChoiceView,
    DiscordAdapter,
    ExecApprovalView,
    ModelPickerView,
    SlashConfirmView,
    UpdatePromptView,
    _resolve_exec_approval_admin_gate,
)
from plugins.platforms.discord.adapter_component_auth import _component_check_auth


@pytest.fixture(autouse=True)
def _clear_component_auth_env(monkeypatch):
    from unittest.mock import MagicMock, patch

    for name in (
        "DISCORD_ALLOW_ALL_USERS",
        "GATEWAY_ALLOW_ALL_USERS",
        "GATEWAY_ALLOWED_USERS",
    ):
        monkeypatch.delenv(name, raising=False)

    # Default-mock PairingStore so tests don't hit the filesystem.
    # Pairing-specific tests override this with explicit mock values.
    mock_store = MagicMock()
    mock_store.is_approved.return_value = False
    with patch("gateway.pairing.PairingStore", return_value=mock_store):
        yield


# ---------------------------------------------------------------------------
# Direct helper coverage -- the views all delegate to this helper, so
# pinning the helper's contract pins all call sites.
# ---------------------------------------------------------------------------


def _interaction(user_id, role_ids=None, *, drop_user=False, drop_roles=False):
    """Build a mock interaction with the requested user/role shape.

    drop_user simulates a payload whose .user attribute is None.
    drop_roles simulates a payload where .user has no .roles attribute
    at all (DM-context Member, raw User payload).
    """
    if drop_user:
        return SimpleNamespace(user=None)

    user_kwargs = {"id": user_id}
    if not drop_roles:
        user_kwargs["roles"] = [SimpleNamespace(id=r) for r in (role_ids or [])]
    return SimpleNamespace(user=SimpleNamespace(**user_kwargs))


# ── no policy configured -> deny unless allow-all is explicit ──────────────


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    [
        ("DISCORD_ALLOW_ALL_USERS", "true"),
        ("GATEWAY_ALLOW_ALL_USERS", "yes"),
    ],
)
def test_component_check_explicit_allow_all_passes(monkeypatch, env_name, env_value):
    monkeypatch.setenv(env_name, env_value)
    interaction = _interaction(11111)
    assert _component_check_auth(interaction, set(), set()) is True


# ── user allowlist ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("snapshot", [{"11111"}, {"*"}])
@pytest.mark.parametrize(("verdict", "expected"), [(None, True), (True, True), (False, False)])
def test_snapshot_user_is_confirmed_with_the_live_check(snapshot, verdict, expected):
    # The user set is the adapter's connect-time snapshot; None means no live check is wired.
    seen = []

    def live_auth(interaction):
        seen.append(interaction.user.id)
        return verdict

    assert _component_check_auth(_interaction(11111), snapshot, set(), live_auth=live_auth) is expected
    assert seen == [11111]


@pytest.mark.asyncio
async def test_approval_buttons_follow_a_revoke_made_after_connect():
    # `hermes pairing revoke` in another process rewrites .env and the pairing store, never the
    # adapter's snapshot; the card's buttons must follow the gateway's per-call check instead.
    adapter = DiscordAdapter(PlatformConfig(enabled=True, token="***"))
    adapter._allowed_user_ids = {"11111"}
    live = {"11111": True}
    adapter.set_authorization_check(lambda user_id, chat_type=None, chat_id=None, **_: live.get(user_id, False))
    channel = SimpleNamespace(send=AsyncMock(return_value=SimpleNamespace(id=1)))
    adapter._client = SimpleNamespace(get_channel=lambda _chat_id: channel, fetch_channel=AsyncMock())

    result = await adapter.send_exec_approval(chat_id="555", command="make deploy", session_key="discord:555")
    assert result.success is True
    view = channel.send.call_args.kwargs["view"]
    assert view._check_auth(_interaction(11111)) is True
    live["11111"] = False
    assert view._check_auth(_interaction(11111)) is False


# ── role allowlist OR semantics ────────────────────────────────────────────


# ── fail-closed on missing role data ───────────────────────────────────────


# ---------------------------------------------------------------------------
# View construction: every view must accept allowed_role_ids and route
# through the shared helper. Default value preserves prior call-sites.
# ---------------------------------------------------------------------------


def test_exec_approval_view_accepts_role_allowlist():
    view = ExecApprovalView(
        session_key="sess-1",
        allowed_user_ids={"11111"},
        allowed_role_ids={42},
    )
    # Role-only user passes
    assert view._check_auth(_interaction(99999, role_ids=[42])) is True
    # Neither user nor role match: reject
    assert view._check_auth(_interaction(99999, role_ids=[7])) is False


def test_slash_confirm_view_accepts_role_allowlist():
    view = SlashConfirmView(
        session_key="sess-1",
        confirm_id="c1",
        allowed_user_ids=set(),
        allowed_role_ids={42},
    )
    assert view._check_auth(_interaction(99999, role_ids=[42])) is True
    assert view._check_auth(_interaction(99999, role_ids=[7])) is False


def test_update_prompt_view_accepts_role_allowlist():
    view = UpdatePromptView(
        session_key="sess-1",
        allowed_user_ids=set(),
        allowed_role_ids={42},
    )
    assert view._check_auth(_interaction(99999, role_ids=[42])) is True
    assert view._check_auth(_interaction(99999, role_ids=[7])) is False


def test_clarify_choice_view_accepts_role_allowlist():
    view = ClarifyChoiceView(
        choices=["one", "two"],
        clarify_id="clarify-1",
        allowed_user_ids=set(),
        allowed_role_ids={42},
    )
    assert view._check_auth(_interaction(99999, role_ids=[42])) is True
    assert view._check_auth(_interaction(99999, role_ids=[7])) is False


# ---------------------------------------------------------------------------
# Empty allowlists across views: fail closed unless allow-all is explicit.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "view_factory",
    [
        lambda: ExecApprovalView(session_key="s", allowed_user_ids=set()),
        lambda: SlashConfirmView(session_key="s", confirm_id="c", allowed_user_ids=set()),
        lambda: UpdatePromptView(session_key="s", allowed_user_ids=set()),
        lambda: ClarifyChoiceView(
            choices=["one"],
            clarify_id="c",
            allowed_user_ids=set(),
        ),
    ],
)
def test_views_empty_allowlists_reject_by_default(view_factory, monkeypatch):
    monkeypatch.delenv("DISCORD_ALLOW_ALL_USERS", raising=False)
    monkeypatch.delenv("GATEWAY_ALLOW_ALL_USERS", raising=False)
    monkeypatch.delenv("GATEWAY_ALLOWED_USERS", raising=False)
    view = view_factory()
    assert view._check_auth(_interaction(99999)) is False


def test_model_picker_view_empty_allowlists_reject_by_default(monkeypatch):
    monkeypatch.delenv("DISCORD_ALLOW_ALL_USERS", raising=False)
    monkeypatch.delenv("GATEWAY_ALLOW_ALL_USERS", raising=False)
    monkeypatch.delenv("GATEWAY_ALLOWED_USERS", raising=False)

    async def _noop(*_a, **_k):
        return ""

    view = ModelPickerView(
        providers=[],
        current_model="m",
        current_provider="p",
        session_key="s",
        on_model_selected=_noop,
        allowed_user_ids=set(),
    )
    assert view.allowed_role_ids == set()
    assert view._check_auth(_interaction(99999)) is False

    # Cancel is gated too: a stranger cannot close the owner's picker.
    import asyncio
    from unittest.mock import AsyncMock

    stranger = _interaction(99999)
    stranger.response = SimpleNamespace(send_message=AsyncMock())
    asyncio.run(view._on_cancel(stranger))
    assert view.resolved is False
    stranger.response.send_message.assert_awaited_once()
    assert stranger.response.send_message.await_args.kwargs.get("ephemeral") is True


def test_view_empty_allowlists_allow_with_explicit_allow_all(monkeypatch):
    monkeypatch.setenv("DISCORD_ALLOW_ALL_USERS", "true")
    view = ExecApprovalView(session_key="s", allowed_user_ids=set())
    assert view._check_auth(_interaction(99999)) is True


# ---------------------------------------------------------------------------
# Pairing store: users approved via ``hermes pairing approve`` must be
# authorized even without DISCORD_ALLOWED_USERS / DISCORD_ALLOWED_ROLES.
# ---------------------------------------------------------------------------


def test_component_check_pairing_approved_user_passes(monkeypatch):
    """User approved in pairing store passes even without allowlists."""
    from unittest.mock import MagicMock, patch

    mock_store = MagicMock()
    mock_store.is_approved.return_value = True
    # Override the autouse fixture's mock with approved=True
    with patch("gateway.pairing.PairingStore", return_value=mock_store):
        interaction = _interaction(11111)
        assert _component_check_auth(interaction, set(), set()) is True
    mock_store.is_approved.assert_called_once_with("discord", "11111")


# ---------------------------------------------------------------------------
# Opt-in admin gate for exec-approval buttons (feat/discord-admin-exec-approval).
# Default OFF: any admitted user can approve (the v0.16-restored behavior).
# When `require_admin_for_exec_approval` is true, the clicker must ALSO be in
# `allow_admin_from`. Fails closed (logged) when the toggle is on but no
# admins are configured. Only ExecApprovalView is gated — other views stay
# user-scope.
# ---------------------------------------------------------------------------


def test_admin_gate_resolver_on_parses_admins():
    """Toggle true -> gate enabled, admins coerced from allow_admin_from."""
    require_admin, admins = _resolve_exec_approval_admin_gate(
        {"require_admin_for_exec_approval": True, "allow_admin_from": "111, 222"}
    )
    assert require_admin is True
    assert admins == {"111", "222"}
    # list form normalizes identically
    _, admins_list = _resolve_exec_approval_admin_gate(
        {"require_admin_for_exec_approval": "true", "allow_admin_from": [111, 222]}
    )
    assert admins_list == {"111", "222"}


def test_exec_view_gate_on_non_admin_rejected():
    """Gate on: admitted user who is NOT an admin is rejected at the button."""
    view = ExecApprovalView(
        session_key="s",
        allowed_user_ids={"11111", "22222"},
        require_admin=True,
        admin_user_ids={"11111"},
    )
    # 22222 is admitted (in allowlist) but not an admin -> rejected.
    assert view._check_auth(_interaction(22222)) is False


def test_exec_view_gate_on_no_admins_fails_closed(caplog):
    """Gate on but no admins configured -> nobody approves, logged once."""
    import logging

    view = ExecApprovalView(
        session_key="s",
        allowed_user_ids={"11111"},
        require_admin=True,
        admin_user_ids=set(),
    )
    with caplog.at_level(logging.WARNING):
        assert view._check_auth(_interaction(11111)) is False
    assert any(
        "require_admin_for_exec_approval" in r.message for r in caplog.records
    )


def test_other_views_not_admin_gated():
    """Lower-stakes views never take the admin gate — they stay user-scope."""
    # SlashConfirmView/ModelPickerView/etc. construct without require_admin and
    # delegate straight to _component_check_auth.
    sc = SlashConfirmView(
        session_key="s", confirm_id="c", allowed_user_ids={"11111"}
    )
    assert sc._check_auth(_interaction(11111)) is True


@pytest.mark.asyncio
async def test_discord_group_approval_buttons_do_not_inherit_dm_admins(monkeypatch):
    """Regression for #151762: a DM-only admin cannot settle a group approval card."""
    from unittest.mock import patch

    from gateway.session_context import clear_session_vars, set_session_vars
    from tools import approval as approval_mod
    from tools.approval_gateway_wait import _ApprovalEntry

    monkeypatch.setattr("tools.approval_context._get_approval_config", lambda: {"approvers": []})
    key = "discord:group-approval-scope"
    tokens = set_session_vars(
        platform="discord", chat_type="group", user_id="requester",
        user_name="Requester", session_key=key,
    )
    try:
        entry = _ApprovalEntry({"command": "echo scoped"})
    finally:
        clear_session_vars(tokens)
    assert entry.authority["approvers"] == []
    assert entry.authority["chat_type"] == "group"
    approval_mod._gateway_queues.setdefault(key, []).append(entry)

    extra = {
        "require_admin_for_exec_approval": True,
        "allow_admin_from": ["dm-admin"],
        "group_allow_admin_from": ["group-admin"],
    }

    def interaction_for(user_id):
        interaction = _interaction(user_id)
        interaction.user.display_name = user_id
        interaction.response = SimpleNamespace(send_message=AsyncMock())
        return interaction

    def view_for(*, require_admin, admin_ids):
        view = ExecApprovalView(
            session_key=key,
            request_id=entry.data["request_id"],
            allowed_user_ids={"requester", "dm-admin", "group-admin"},
            require_admin=require_admin,
            admin_user_ids=admin_ids,
            approval_extra=extra,
        )
        view._gate = AsyncMock(return_value=True)
        view._finalize_embed = AsyncMock()
        return view

    try:
        dm_view = view_for(require_admin=True, admin_ids={"dm-admin"})
        dm_click = interaction_for("dm-admin")
        # The separate Discord admin click gate admits this user; the approval
        # actor must still refuse a DM-only admin on a GROUP approval.
        assert dm_view._check_auth(dm_click) is True
        await dm_view._resolve(dm_click, "once", None, "gateway.exec_approval.resolved_once")
        dm_click.response.send_message.assert_awaited_once()
        assert dm_click.response.send_message.await_args.kwargs["ephemeral"] is True
        assert entry.result is None and not entry.event.is_set()

        # Even when the pre-check is bypassed, the in-lock settlement check
        # must not accept the DM admin via an unscoped admin_ids union.
        with patch("gateway.approval_actor.approval_refusal", return_value=None):
            await view_for(require_admin=True, admin_ids={"dm-admin"})._resolve(
                interaction_for("dm-admin"), "once", None, "gateway.exec_approval.resolved_once",
            )
        assert entry.result is None and not entry.event.is_set()

        # With the independent Discord admin-click gate off, the actual group
        # admin may approve the same pending request.
        group_view = view_for(require_admin=False, admin_ids=set())
        await group_view._resolve(
            interaction_for("group-admin"), "once", None, "gateway.exec_approval.resolved_once",
        )
        assert entry.result == "once" and entry.event.is_set()
    finally:
        approval_mod._gateway_queues.pop(key, None)
