"""Tern browser ownership and legacy routing (#554), using only a fake native interface."""
import json
from unittest.mock import Mock

import pytest

from tools import browser_tern as tern


class FakeTern:
    def __init__(self):
        self.calls = []
        self.entries = {7: {"block": 7, "url": "https://example.org/", "title": "User page",
                            "owner": None, "driven": False}}

    def __call__(self, op):
        self.calls.append(op)
        name = op["op"]
        if name == "blocks":
            return {"blocks": list(self.entries.values())}
        if name == "open":
            self.entries[8] = {"block": 8, "url": "about:blank", "title": "", "owner": op["owner"], "driven": True}
            return {"block": 8}
        entry = self.entries[op["block"]]
        if name == "goto":
            entry.update(url=op["url"], title="Agent page")
        if name == "snapshot":
            return {"text": '- button "Continue" [ref=e1]', "url": entry["url"], "title": entry["title"]}
        if name == "close":
            del self.entries[op["block"]]
        return dict(entry)


@pytest.fixture
def native():
    fake = FakeTern()
    focus = Mock()
    return tern.TernBrowserProvider(fake, 3, focus), fake, focus


def test_list_does_not_grant_drive_permission(native):
    provider, fake, _ = native
    assert provider.listing("agent") == [{"target_id": "7", "url": "https://example.org/", "title": "User page",
                                          "owner": None, "owned": False, "available": True}]
    with pytest.raises(tern.TernBrowserError, match="not owned"):
        provider.command("agent", "click", ["@e1"])
    assert [call["op"] for call in fake.calls] == ["blocks"]


def test_open_uses_own_pip_and_never_user_block(native):
    provider, fake, _ = native
    result = provider.command("agent", "open", ["https://example.net/"])
    assert result["tern_target"] == {"target_id": "8", "url": "https://example.net/", "title": "Agent page", "in_tern": True}
    assert fake.calls[0] == {"op": "open", "owner": 3, "url": "about:blank"}
    assert not any(c.get("block") == 7 for c in fake.calls)
    provider.close("agent")
    assert fake.calls[-1] == {"op": "close", "block": 8}


def test_only_explicit_user_adoption_grants_access_and_cleanup_releases(native):
    provider, fake, focus = native
    assert provider.adopt_by_user("agent", "7")["target_id"] == "7"
    provider.command("agent", "click", ["@e1"])
    assert {"op": "act", "block": 7, "action": "click", "ref": "e1"} in fake.calls
    provider.focus("agent", "7")
    focus.assert_called_once_with(7)
    provider.close("agent")
    assert fake.calls[-1] == {"op": "release", "block": 7}
    assert 7 in fake.entries


def test_foreign_tasks_cannot_adopt_drive_or_focus_owned_block(native):
    provider, fake, focus = native
    provider.adopt_by_user("a", "7")
    before = list(fake.calls)
    for operation in (lambda: provider.command("b", "click", ["@e1"]), lambda: provider.focus("b", "7")):
        with pytest.raises(tern.TernBrowserError):
            operation()
    assert fake.calls == before
    with pytest.raises(tern.TernBrowserError):
        provider.adopt_by_user("b", "7")
    focus.assert_not_called()


@pytest.mark.parametrize("target", ["07", " 7", "+7", "7x", 7, True])
def test_exact_target_ids_only(native, target):
    provider, fake, _ = native
    with pytest.raises(tern.TernBrowserError):
        provider.adopt_by_user("agent", target)
    assert fake.calls == []


def test_already_driven_and_old_tern_blocks_refused(native):
    provider, fake, _ = native
    for driven in (True, None):
        fake.entries[7]["driven"] = driven
        with pytest.raises(tern.TernBrowserError):
            provider.adopt_by_user("agent", "7")
    assert not any(c["op"] == "snapshot" for c in fake.calls)


def test_outside_tern_does_not_probe_or_change_old_backend(monkeypatch):
    from tools import browser_tool_session as session
    monkeypatch.delenv("TERN_PANE", raising=False)
    monkeypatch.delenv("TERN_WINDOW_KEY", raising=False)
    probe = Mock(side_effect=AssertionError("must not spawn Tern"))
    monkeypatch.setattr(tern.subprocess, "run", probe)
    assert tern.get_provider() is None
    legacy = {"success": False, "error": "legacy preflight sentinel"}
    monkeypatch.setattr(session, "_browser_command_preflight", lambda: legacy)
    assert session._run_browser_command("agent", "snapshot", []) is legacy
    probe.assert_not_called()


def test_unavailable_interface_keeps_legacy_dispatch(monkeypatch):
    from tools import browser_tool_session as session
    monkeypatch.setattr(tern, "get_provider", lambda: None)
    legacy = {"success": False, "error": "old backend selected"}
    monkeypatch.setattr(session, "_browser_command_preflight", lambda: legacy)
    assert session._run_browser_command("agent", "open", ["https://example.org/"]) is legacy


def test_existing_browser_tools_use_native_adapter_and_emit_identity(native, monkeypatch):
    from tools import browser_tool as browser
    provider, fake, _ = native
    monkeypatch.setattr(tern, "get_provider", lambda: provider)
    monkeypatch.setattr(browser, "_is_camofox_mode", lambda: False)
    monkeypatch.setattr(browser, "_url_policy_error", lambda *a, **k: None)
    monkeypatch.setattr(browser, "_navigation_session_key", lambda task, url: task)
    monkeypatch.setattr(browser, "_post_redirect_block", lambda *a: None)
    result = json.loads(browser.browser_navigate("https://example.org/", task_id="agent"))
    assert result["success"]
    assert result["tern_target"]["target_id"] == "8"
    assert "Continue" in result["snapshot"]
    result = json.loads(browser.browser_snapshot(task_id="agent"))
    assert result["tern_target"]["target_id"] == "8"


def test_cleanup_retains_claim_on_failure(native):
    provider, fake, _ = native
    provider.adopt_by_user("agent", "7")
    provider.request = Mock(side_effect=tern.TernBrowserError("temporarily unavailable"))
    with pytest.raises(tern.TernBrowserError):
        provider.close("agent")
    assert provider.owned("agent").adopted


def test_initial_headless_capability_failure_closes_only_new_blank_block_and_falls_back(native, monkeypatch):
    provider, fake, _ = native
    def request(op):
        if op["op"] == "snapshot":
            raise tern.TernBrowserError("headless page calls unavailable", "unsupported")
        return fake(op)
    provider.request = request
    monkeypatch.setattr(tern, "get_provider", lambda: provider)
    assert tern.run_command("agent", "open", ["https://example.org/"]) is None
    assert not provider.targets
    assert 7 in fake.entries and 8 not in fake.entries
    assert not any(c["op"] == "goto" for c in fake.calls)


def test_owned_failure_does_not_select_an_unrelated_backend(native, monkeypatch):
    provider, _, _ = native
    provider.adopt_by_user("agent", "7")
    provider.request = Mock(side_effect=tern.TernBrowserError("page went away", "not_found"))
    monkeypatch.setattr(tern, "get_provider", lambda: provider)
    assert tern.run_command("agent", "snapshot", [])["success"] is False
    assert provider.owned("agent").block == 7


def test_another_pane_or_profile_cannot_reclaim_an_owned_block(native, monkeypatch):
    provider, fake, _ = native
    scope = ("window-owned", "socket-owned")
    provider.ownership_scope = scope
    peer = tern.TernBrowserProvider(fake, 4, ownership_scope=scope)
    monkeypatch.setattr(tern, "_providers", {("profile-a",): provider, ("profile-b",): peer})
    provider.adopt_by_user("agent", "7")
    assert not peer.listing("other")[0]["available"]
    with pytest.raises(tern.TernBrowserError):
        peer.adopt_by_user("other", "7")


def test_cleanup_never_releases_another_profiles_target(native, monkeypatch):
    provider, fake, _ = native
    provider.adopt_by_user("default", "7")
    monkeypatch.setattr(tern, "_providers", {("other-profile",): provider})
    before = list(fake.calls)
    tern.cleanup("default")
    assert fake.calls == before
    assert provider.owned("default").block == 7


def test_cli_uses_exact_window_and_scrubbed_environment(native, monkeypatch):
    from types import SimpleNamespace
    _, fake, _ = native
    env = {"PATH": "/owned/bin", "TERN_DAEMON_SOCKET": "/owned/daemon.sock", "TERN_CONFIG_DIR": "/owned/config"}
    monkeypatch.setattr(tern, "_context", lambda: (env, "/owned/tern", 3, "owned-window"))
    monkeypatch.setattr(tern, "_providers", {})
    def run(argv, **kwargs):
        assert kwargs["env"] is env
        assert argv[-2:] == ["--window", "owned-window"]
        assert argv[0] == "/owned/tern"
        answer = fake(json.loads(argv[2]))
        return SimpleNamespace(returncode=0, stdout=json.dumps({"ok": answer}))
    monkeypatch.setattr(tern.subprocess, "run", run)
    def popen(argv, **kwargs):
        result = run(argv, **kwargs)
        return SimpleNamespace(returncode=result.returncode, communicate=lambda **kw: (result.stdout, ""))
    monkeypatch.setattr(tern.subprocess, "Popen", popen)
    provider = tern.get_provider()
    assert provider.listing("agent")[0]["target_id"] == "7"
    assert provider.command("agent", "open", ["https://example.net/"])["tern_target"]["target_id"] == "8"


def test_screenshot_uses_full_flag_but_writes_only_explicit_image_path(native, tmp_path):
    provider, fake, _ = native
    provider.adopt_by_user("agent", "7")
    def request(op):
        if op["op"] == "capture":
            assert op["full"] is True
            return {"data": "aW1hZ2U="}
        return fake(op)
    provider.request = request
    path = tmp_path / "page.png"
    result = provider.command("agent", "screenshot", ["--full", str(path)])
    assert result["data"]["path"] == str(path)
    assert path.read_bytes() == b"image"
    with pytest.raises(tern.TernBrowserError, match="Annotated"):
        provider.command("agent", "screenshot", ["--annotate", "--full", str(path)])


def test_trusted_keys_use_documented_input_steps():
    assert tern.press_events("Control+a") == [
        {"type": "key", "action": "down", "key": "Control", "mods": []},
        {"type": "key", "action": "down", "key": "a", "mods": ["ctrl"]},
        {"type": "key", "action": "up", "key": "a", "mods": ["ctrl"]},
        {"type": "key", "action": "up", "key": "Control", "mods": []}]

