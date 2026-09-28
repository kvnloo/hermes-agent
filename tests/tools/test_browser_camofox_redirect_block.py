"""Invariant tests for the Camofox post-redirect metadata floor.

Companion to ``tests/tools/test_browser_camofox_private_page_guard.py`` (read-time
guards). These cover the navigate path: ``browser_navigate`` early-returns for
camofox mode before the main ``_post_redirect_block``, so the redirect-landing
check must live in ``camofox_navigate`` itself.
"""

import json

import pytest

from tools import browser_camofox


PUBLIC_URL = "https://public.example/redirector"
IMDS_LANDING = "http://169.254.169.254/latest/meta-data/iam/security-credentials/admin"


@pytest.fixture
def _session(monkeypatch):
    session = {"tab_id": "tab-1", "user_id": "user-1"}
    monkeypatch.setattr(browser_camofox, "_get_session", lambda task_id: session)
    return session


def _stub_navigate(monkeypatch, landings):
    """Stub _navigate_tab: each call pops a landing URL, then records the reset."""
    calls = []

    def fake_navigate(task_id, browser_url):
        calls.append(browser_url)
        landing = landings.pop(0) if landings else browser_url
        return {"tab_id": "tab-1", "user_id": "user-1"}, {"ok": True, "url": landing}

    monkeypatch.setattr(browser_camofox, "_navigate_tab", fake_navigate)
    return calls


def test_redirect_landing_on_metadata_is_blocked_and_tab_reset(monkeypatch, _session):
    """The always-blocked floor fires on the landing, not just the requested URL."""
    calls = _stub_navigate(monkeypatch, [IMDS_LANDING])

    raw = browser_camofox.camofox_navigate(PUBLIC_URL, task_id="t1")
    payload = json.loads(raw)

    assert payload["success"] is False
    assert "metadata" in payload["error"]
    assert "snapshot" not in payload  # blocked before the page content is read
    assert calls[-1] == "about:blank"  # tab reset so follow-up reads can't see it


def test_redirect_landing_on_ordinary_url_still_succeeds(monkeypatch, _session):
    """The floor is narrow: non-metadata landings (incl. private/local) still work."""
    calls = _stub_navigate(monkeypatch, ["http://localhost:8080/dashboard"])

    raw = browser_camofox.camofox_navigate(PUBLIC_URL, task_id="t1")
    payload = json.loads(raw)

    assert payload["success"] is True
    assert payload["url"] == "http://localhost:8080/dashboard"
    assert calls == [PUBLIC_URL]  # no reset navigation
