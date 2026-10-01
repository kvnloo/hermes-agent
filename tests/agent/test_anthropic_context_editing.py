"""Anthropic server-side context editing, ``compression.anthropic_context_editing`` (#526).

The real ``AIAgent`` turn loop runs on the production native route (``api.anthropic.com``) against
the SDK-oracle Messages fake: an ``HTTPS_PROXY`` terminates TLS for that host with a throwaway CA,
so only the vendor HTTP boundary is faked and every request body is validated against the
installed SDK's beta request types.
"""

import pytest

from tests.fakes.providers.anthropic_messages import AnthropicMessagesServer, ApiError, Reply, Text
from tests.fakes.providers.oauth_token_server import TLSInterceptProxy, make_test_ca

BETA = "context-management-2025-06-27"
HOST = "api.anthropic.com"
ON = "anthropic_context_editing: true"


@pytest.fixture
def native_agent(tmp_path, monkeypatch):
    """``build(responder, compression, ...)`` -> ``(agent, server)``; config.yaml in a temp HERMES_HOME."""
    started = []

    def build(responder, compression, *, model="claude-sonnet-4-5", native=True):
        srv = AnthropicMessagesServer(responder).start()
        ca = make_test_ca(tmp_path / "ca", [HOST])
        started.extend([srv, TLSInterceptProxy(srv, ca, [HOST]).start()])
        for var in ("HTTPS_PROXY", "https_proxy"):
            monkeypatch.setenv(var, started[-1].url)
        for var in ("NO_PROXY", "no_proxy"):
            monkeypatch.setenv(var, "127.0.0.1,localhost")
        monkeypatch.setenv("SSL_CERT_FILE", str(ca.ca_pem))
        home = tmp_path / ".hermes"
        home.mkdir()
        (home / "config.yaml").write_text(f"compression:\n  {compression}\n", encoding="utf-8")
        monkeypatch.setenv("HERMES_HOME", str(home))
        from run_agent import AIAgent

        agent = AIAgent(
            api_key="sk-ant-api03-fake-key", base_url=f"https://{HOST}" if native else srv.base_url,
            provider="anthropic", model=model, quiet_mode=True, skip_context_files=True, skip_memory=True,
            enabled_toolsets=["file"], max_iterations=3,
        )
        return agent, srv

    yield build
    for item in reversed(started):
        item.stop()


@pytest.mark.parametrize(("compression", "route", "sent"), [
    ("anthropic_context_editing: false", {}, False),
    (ON, {}, True),
    (ON + "\n  enabled: false", {}, False),
    (ON + "\n  checkpoint_required: true", {}, False),
    (ON, {"model": "glm-4.6"}, False),
    (ON, {"native": False}, False),
], ids=["off", "on", "compression-disabled", "checkpoint-required", "non-claude-model", "third-party-endpoint"])
def test_opt_in_sends_clear_tool_uses_with_its_beta_ahead_of_local_compression(native_agent, compression, route, sent):
    agent, srv = native_agent(lambda _record: Reply([Text("ok")]), compression, **route)

    assert agent.run_conversation("hi")["completed"]

    main = srv.main_requests()
    assert main and srv.schema_errors() == []
    for record in main:
        payload = record["body"].get("context_management")
        betas = record["headers"].get("anthropic-beta", "").split(",")
        if not sent:
            assert payload is None and BETA not in betas
            continue
        assert BETA in betas
        [edit] = payload["edits"]
        assert edit["type"] == "clear_tool_uses_20250919"
        # The server clears first; local compression keys on the reported post-clear size and fires later.
        assert edit["trigger"]["value"] < agent.context_compressor.threshold_tokens
        assert 0 < edit["clear_at_least"]["value"] < edit["trigger"]["value"]


def test_structured_rejection_disables_it_for_the_session_and_retries_once(native_agent):
    def responder(record):
        if "context_management" in record["body"]:
            return ApiError(400, "invalid_request_error", "context_management: Extra inputs are not permitted")
        return Reply([Text("ok")])

    agent, srv = native_agent(responder, ON)
    first = agent.run_conversation("hi")
    second = agent.run_conversation("again", conversation_history=first["messages"])

    assert first["completed"] and second["completed"]
    assert ["context_management" in r["body"] for r in srv.main_requests()] == [True, False, False]
