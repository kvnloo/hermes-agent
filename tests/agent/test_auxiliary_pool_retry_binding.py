"""Pool recovery must attempt the replacement key, not replay the main snapshot.

Real auxiliary routing, credential stores and SDK requests against a loopback
server. No credential, pool, routing or transport functions are mocked.
"""

import asyncio
from contextlib import contextmanager
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from openai import APIStatusError

import agent.auxiliary_client as aux
from agent.credential_pool import load_pool
from agent.secret_scope import (
    reset_multiplex_context, reset_secret_scope, set_multiplex_context, set_secret_scope,
)
from hermes_constants import reset_hermes_home_override, set_hermes_home_override

MODEL = "deepseek-v3.2"


@pytest.fixture
def endpoint(tmp_path, monkeypatch, request):
    quota = getattr(request, "param", False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    resolve_address = socket.getaddrinfo

    def loopback_only(host, *args, **kwargs):
        if host not in ("127.0.0.1", b"127.0.0.1"):
            raise AssertionError(f"Non-loopback request refused: {host}")
        return resolve_address(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    aux.shutdown_cached_clients()
    aux._reset_aux_unhealthy_cache()
    requests, rejected = [], set()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            key = self.headers.get("Authorization", "").removeprefix("Bearer ")
            requests.append((key, self.path, payload))
            status = (429 if quota else 402) if key in rejected else 200
            response = {"error": {"type": "server_error", "message": (
                "You reached your Pro weekly limit." if quota else "Insufficient account funds")}}
            if status == 200:
                response = {
                    "id": "chatcmpl-pool-test", "object": "chat.completion", "created": 1,
                    "model": payload["model"],
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
            body = json.dumps(response).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests, rejected
    finally:
        aux.shutdown_cached_clients()
        aux._reset_aux_unhealthy_cache()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _write_home(home, base, prefix, replacement_base=None):
    home.mkdir()
    keys = [f"{prefix}-A", f"{prefix}-B"]
    rows = [{"id": key, "label": key, "auth_type": "api_key", "priority": i,
             "source": "manual", "access_token": key, "base_url": base}
            for i, key in enumerate(keys)]
    rows[1]["base_url"] = replacement_base or base
    (home / "auth.json").write_text(json.dumps({"version": 1, "providers": {},
                                               "credential_pool": {"opencode-go": rows}}))
    config = {
        "model": {"provider": "opencode-go", "default": MODEL, "base_url": base},
        "auxiliary": {"approval": {"provider": "auto", "model": MODEL}},
    }
    (home / "config.yaml").write_text(json.dumps(config))
    return keys


def _call(async_mode, runtime):
    kwargs = dict(task="approval", main_runtime=runtime,
                  messages=[{"role": "user", "content": "Return ok."}],
                  temperature=0, max_tokens=8, timeout=5)
    if async_mode:
        return asyncio.run(aux.async_call_llm(**kwargs))
    return aux.call_llm(**kwargs)


@contextmanager
def _profile(home):
    home_token = set_hermes_home_override(home)
    secret_token = set_secret_scope({}, profile_home=str(home))
    multiplex_token = set_multiplex_context(True)
    try:
        yield
    finally:
        reset_multiplex_context(multiplex_token)
        reset_secret_scope(secret_token)
        reset_hermes_home_override(home_token)


@pytest.mark.parametrize("async_mode", [False, True], ids=["sync", "async"])
@pytest.mark.parametrize("both_fail", [False, True], ids=["healthy-replacement", "both-exhausted"])
@pytest.mark.parametrize("different_endpoint", [False, True], ids=["same-endpoint", "entry-endpoint"])
def test_auto_recovery_attempts_both_keys_before_exhaustion(
        tmp_path, endpoint, async_mode, both_fail, different_endpoint):
    base, requests, rejected = endpoint
    home = tmp_path / "pool"
    replacement_base = base.removesuffix("/v1") + "/replacement/v1" if different_endpoint else base
    keys = _write_home(home, base, "pool", replacement_base)
    rejected.update(keys if both_fail else keys[:1])
    runtime = {"provider": "opencode-go", "model": MODEL, "base_url": base,
               "api_key": keys[0], "api_mode": "chat_completions"}
    original_runtime = dict(runtime)
    with _profile(home):
        if both_fail:
            with pytest.raises(APIStatusError):
                _call(async_mode, runtime)
        else:
            response = _call(async_mode, runtime)
            assert response.choices[0].message.content == "ok"
        assert [key for key, _, _ in requests] == keys
        expected_paths = ["/v1/chat/completions",
                          "/replacement/v1/chat/completions" if different_endpoint else "/v1/chat/completions"]
        assert [path for _, path, _ in requests] == expected_paths
        assert all(body["model"] == MODEL and body["messages"] == [{"role": "user", "content": "Return ok."}]
                   for _, _, body in requests)
        entries = {entry.id: entry for entry in load_pool("opencode-go").entries()}
        assert entries[keys[0]].last_status == "exhausted"
        assert (entries[keys[1]].last_status == "exhausted") is both_fail
        if not both_fail:
            assert load_pool("opencode-go").has_available()
            assert not aux._is_provider_unhealthy("opencode-go")
        assert runtime == original_runtime


@pytest.mark.parametrize("async_mode", [False, True], ids=["sync", "async"])
def test_retry_binding_stays_in_its_profile_and_preserves_standalone_keys(tmp_path, endpoint, async_mode):
    base, requests, rejected = endpoint
    homes = [tmp_path / name for name in ("first", "second")]
    profile_keys = [_write_home(home, base, home.name) for home in homes]
    rejected.update(keys[0] for keys in profile_keys)
    # Re-enter the first profile after another profile uses the same provider.
    for i in (0, 1, 0):
        with _profile(homes[i]):
            response = _call(async_mode, {"provider": "opencode-go", "model": MODEL,
                                         "base_url": base, "api_key": profile_keys[i][0]})
            assert response.choices[0].message.content == "ok"
            assert requests[-1][0] == profile_keys[i][1]
    assert [key for key, _, _ in requests] == [*profile_keys[0], *profile_keys[1], *profile_keys[0]]
    # An unrelated explicitly supplied key must not rotate or consume this pool.
    with _profile(homes[0]):
        before = [(e.id, e.last_status, e.last_status_at) for e in load_pool("opencode-go").entries()]
        rejected.add("standalone")
        with pytest.raises(APIStatusError):
            _call(async_mode, {"provider": "opencode-go", "model": MODEL,
                               "base_url": base, "api_key": "standalone"})
        assert requests[-1][0] == "standalone"
        assert [(e.id, e.last_status, e.last_status_at) for e in load_pool("opencode-go").entries()] == before


@pytest.mark.parametrize("endpoint", [True], indirect=True, ids=["weekly-quota-429"])
@pytest.mark.parametrize("both_fail", [False, True], ids=["healthy-B", "both-quota"])
def test_ollama_auto_title_quota_preserves_wire_identity_and_saved_health(
        tmp_path, monkeypatch, endpoint, both_fail):
    """Supplement Dinkum #133565; reported/requested by vgm-agente-ia.

    AI authored by OpenAI Codex. Real SDK transport and profile auth reload;
    synthetic credentials only, no deployed gateway or main-agent turn.
    """
    base, requests, rejected = endpoint
    model = "deepseek-v4.1-flash"
    home = tmp_path / ".hermes" / "profiles" / "quota-title"
    home.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    keys = ["synthetic-ollama-A", "synthetic-ollama-B"]
    rows = [{"id": key, "label": key, "auth_type": "api_key", "priority": i,
             "source": "manual", "access_token": key, "base_url": base}
            for i, key in enumerate(keys)]
    rows.append({"id": "env-A", "label": "env-A", "auth_type": "api_key",
                 "priority": 2, "source": "env:OLLAMA_API_KEY", "base_url": base})
    (home / "auth.json").write_text(json.dumps({"version": 1, "providers": {},
                                               "credential_pool": {"ollama-cloud": rows}}))
    (home / "config.yaml").write_text(json.dumps({
        "model": {"provider": "ollama-cloud", "default": model, "base_url": base},
        "credential_pool_strategies": {"ollama-cloud": "fill_first"},
        "auxiliary": {"title_generation": {"provider": "auto"}},
    }))
    runtime = {"provider": "ollama-cloud", "model": model, "base_url": base,
               "api_key": keys[0], "api_mode": "chat_completions"}
    original_runtime = dict(runtime)
    rejected.update(keys if both_fail else keys[:1])
    with _profile(home):
        token = set_secret_scope({"OLLAMA_API_KEY": keys[0], "OLLAMA_BASE_URL": base},
                                 profile_home=str(home))
        try:
            initial = load_pool("ollama-cloud")
            assert len(initial.entries()) == 3
            assert [e.runtime_api_key for e in initial.entries()] == [*keys, keys[0]]
            assert initial.select(model=model).runtime_api_key == keys[0]
            kwargs = dict(task="title_generation", main_runtime=runtime,
                          messages=[{"role": "user", "content": "Return ok."}],
                          temperature=0, max_tokens=8, timeout=5)
            response, error = None, None
            try:
                response = aux.call_llm(**kwargs)
            except APIStatusError as exc:
                error = exc
            observed = {e.id: {"status": e.last_status, "code": e.last_error_code}
                        for e in load_pool("ollama-cloud").entries()}
            print("synthetic quota receipt:", {"wire": [k for k, _, _ in requests],
                  "models": [body["model"] for _, _, body in requests], "saved": observed})
            assert [key for key, _, _ in requests] == keys
            assert [path for _, path, _ in requests] == ["/v1/chat/completions"] * 2
            assert requests[0][2]["model"] == model
            assert all(not body.get("stream", False) for _, _, body in requests)
            if both_fail:
                assert error is not None and error.status_code == 429
                assert "You reached your Pro weekly limit." in str(error)
            else:
                assert error is None
                assert response.choices[0].message.content == "ok"
            assert runtime == original_runtime
            # Reload and rehydrate the unchanged environment twice. Duplicate A
            # must retain exhaustion rather than resurrect the failed credential.
            for _ in range(2):
                reloaded = load_pool("ollama-cloud")
                entries = {e.id: e for e in reloaded.entries()}
                for entry_id in (keys[0], "env-A"):
                    assert entries[entry_id].last_status == "exhausted"
                    assert entries[entry_id].last_error_code == 429
                assert (entries[keys[1]].last_status == "exhausted") is both_fail
                selected = reloaded.select(model=model)
                if both_fail:
                    assert entries[keys[1]].last_error_code == 429
                    assert selected is None
                else:
                    assert selected.runtime_api_key == keys[1]
                    assert not aux._is_provider_unhealthy("ollama-cloud")
        finally:
            reset_secret_scope(token)
