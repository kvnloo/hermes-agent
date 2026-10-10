"""Unshipping IRC-only registry seam for the narrow owner-review composition.

Mirrors the native standalone sender's existing nonempty single-token preflight,
not a full IRC grammar or production repair. It retains nick destinations as
well as channels. No shared resolver flag or Telegram registration is changed.
"""

import pytest


def _native_single_token(ref):
    return bool(ref) and not any(char in ref for char in ("\r", "\n", "\x00", " "))


def _parse_native_single_token(ref):
    return (ref, None) if _native_single_token(ref) else None


@pytest.fixture(autouse=True)
def _irc_native_parser_seam(request, monkeypatch, _hermetic_environment):
    # The owner's existing Telegram-negative test runs completely unchanged.
    if request.node.path.name != "test_cron_target_boundary.py":
        return
    request.getfixturevalue("delivery_home")
    from gateway.platform_registry import platform_registry
    from tools.send_message_tool import prepare_send_message_platforms

    prepare_send_message_platforms()
    entry = platform_registry.get("irc")
    assert entry is not None, "the real enabled IRC plugin must be discovered"
    monkeypatch.setattr(entry, "parse_target_ref_fn", _parse_native_single_token)
    monkeypatch.setattr(entry, "validate_target_ref_fn", _native_single_token)

    def no_transport(*args, **kwargs):
        pytest.fail("target validation must not construct an IRC adapter")

    monkeypatch.setattr(entry, "adapter_factory", no_transport)
