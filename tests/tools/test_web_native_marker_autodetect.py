"""A Codex login alone must not make ``openai-native`` the web backend (#137475, #135684).

``openai-native`` is a marker: it only works when the Codex Responses transport swaps the client
``web_search`` function for the server-side built-in. Autodetect runs through two resolvers, the
legacy ladder (``tools.web_tools._get_backend``, used by ``web_search``/``web_extract`` dispatch) and the
registry (``agent.web_search_registry.get_active_search_provider``, used by the Codex transport's
swap decision and by ``hermes doctor``). Both must skip the marker on a never-configured install;
an explicit pin must still reach it.
"""

import json

import pytest

_WEB_KEYS = (
    "TAVILY_API_KEY", "PERPLEXITY_API_KEY", "EXA_API_KEY", "PARALLEL_API_KEY", "KEENABLE_API_KEY",
    "FIRECRAWL_API_KEY", "FIRECRAWL_API_URL", "SEARXNG_URL", "BRAVE_SEARCH_API_KEY",
)


@pytest.fixture
def codex_login_only(monkeypatch):
    """Never-configured install: no ``web:`` section, no web keys, no ddgs, one Codex login."""
    from hermes_constants import get_hermes_home

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "auth.json").write_text(json.dumps(
        {"providers": {"openai-codex": {"tokens": {"access_token": "tok"}}}}
    ))
    for key in _WEB_KEYS:
        monkeypatch.delenv(key, raising=False)
    from tools import web_tools

    monkeypatch.setattr(web_tools, "_ddgs_package_importable", lambda: False)
    monkeypatch.setattr(web_tools, "_is_tool_gateway_ready", lambda: False)
    web_tools._ensure_web_plugins_loaded()
    return home


def test_web_dispatch_skips_native_marker(codex_login_only):
    from tools.web_tools import _get_extract_backend, _get_search_backend

    assert _get_search_backend() != "openai-native"
    assert _get_extract_backend() != "openai-native"


def test_registry_autodetect_skips_native_marker(codex_login_only):
    from agent.web_search_registry import get_active_search_provider

    provider = get_active_search_provider()
    assert getattr(provider, "name", None) != "openai-native"


@pytest.mark.parametrize("config", ["", "web:\n  keyless_fallback: false\n"], ids=["keyless-on", "keyless-off"])
def test_codex_transport_keeps_client_search_without_a_pin(codex_login_only, config):
    # Keyless off: the registry resolves nothing, so the swap falls back to the legacy ladder.
    (codex_login_only / "config.yaml").write_text(config)
    from agent.transports.codex import _openai_prefers_native_web_search

    assert _openai_prefers_native_web_search() is False


def test_explicit_pin_still_selects_native(codex_login_only):
    (codex_login_only / "config.yaml").write_text("web:\n  search_backend: openai-native\n")
    from agent.transports.codex import _openai_prefers_native_web_search
    from agent.web_search_registry import get_active_search_provider
    from tools.web_tools import _get_search_backend

    assert _get_search_backend() == "openai-native"
    assert get_active_search_provider().name == "openai-native"
    assert _openai_prefers_native_web_search() is True
