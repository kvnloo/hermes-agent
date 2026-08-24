import importlib
import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest


HARNESS = Path(__file__).parents[2] / "contrib" / "privilege-harness"
sys.path.insert(0, str(HARNESS))

broker = importlib.import_module("daemon.broker")
executor_module = importlib.import_module("daemon.executor")


@pytest.fixture
def executable(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    path = bin_dir / "inert-executable"
    path.write_text("inert", encoding="utf-8")
    path.chmod(0o555)
    bin_dir.chmod(0o555)
    return path


@pytest.fixture
def catalog_file(tmp_path, executable):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({
        "version": 1,
        "operations": [{
            "id": "service.restart",
            "executable": str(executable),
            "argv": ["--unit", "{unit}"],
            "slots": {"unit": {"type": "enum", "values": ["alpha", "beta"]}},
            "timeout_seconds": 2,
        }],
    }), encoding="utf-8")
    path.chmod(0o444)
    return path


def make_broker(tmp_path, catalog_file, *, clock=None, runner=None):
    return broker.PrivilegeBroker(
        catalog_path=catalog_file,
        ledger_path=tmp_path / "ledger.jsonl",
        requester_uids={1001},
        operator_uids={2001},
        requester_credential="requester-secret",
        operator_credential="operator-secret",
        ttl_seconds=5,
        clock=clock,
        runner=runner,
    )


def request_args(**overrides):
    values = {
        "operation_id": "service.restart",
        "slots": {"unit": "alpha"},
        "reason": "recover service",
        "profile": "default",
        "session": "session-1",
    }
    values.update(overrides)
    return values


def test_request_builds_typed_immutable_plan_without_accepting_process_inputs(tmp_path, catalog_file):
    service = make_broker(tmp_path, catalog_file)

    pending = service.request(peer=broker.PeerIdentity(uid=1001, pid=10, start_time=20),
                              credential="requester-secret", **request_args())

    assert pending["status"] == "pending"
    assert "grant" not in pending
    plan = pending["plan"]
    assert plan["operation_id"] == "service.restart"
    assert plan["argv"] == [str(catalog_file.parent / "bin" / "inert-executable"), "--unit", "alpha"]
    assert "credential" not in json.dumps(plan)
    with pytest.raises(broker.InvalidRequest):
        service.request(peer=broker.PeerIdentity(uid=1001, pid=10, start_time=20),
                        credential="requester-secret", shell="id", **request_args())


def test_requester_and_wrong_identity_cannot_approve(tmp_path, catalog_file):
    service = make_broker(tmp_path, catalog_file)
    pending = service.request(peer=broker.PeerIdentity(1001, 10, 20),
                              credential="requester-secret", **request_args())

    for peer, credential in [
        (broker.PeerIdentity(1001, 10, 20), "operator-secret"),
        (broker.PeerIdentity(2001, 11, 21), "requester-secret"),
        (broker.PeerIdentity(2999, 12, 22), "operator-secret"),
    ]:
        with pytest.raises(broker.Unauthorized):
            service.decide(pending["request_id"], "approve", peer=peer, credential=credential)

    decision = service.decide(pending["request_id"], "approve",
                              peer=broker.PeerIdentity(2001, 11, 21),
                              credential="operator-secret")
    assert decision["status"] == "approved"


def test_internal_grant_is_one_use_under_concurrent_claims(tmp_path, catalog_file):
    calls = []
    gate = threading.Barrier(2)

    def runner(plan):
        calls.append(plan)
        return {"exit_code": 0, "stdout": "ok", "stderr": "", "truncated": False}

    service = make_broker(tmp_path, catalog_file, runner=runner)
    pending = service.request(peer=broker.PeerIdentity(1001, 10, 20),
                              credential="requester-secret", **request_args())
    service.decide(pending["request_id"], "approve",
                   peer=broker.PeerIdentity(2001, 11, 21), credential="operator-secret")
    results = []

    def consume():
        gate.wait()
        try:
            results.append(service.await_result(pending["request_id"], timeout=1))
        except broker.AmbiguousExecution:
            results.append({"status": "ambiguous"})

    threads = [threading.Thread(target=consume) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(calls) == 1
    assert len(results) == 2
    assert {result["status"] for result in results} <= {"ambiguous", "completed"}
    assert "completed" in {result["status"] for result in results}


def test_expiry_mutation_restart_and_crash_ambiguity_fail_closed(tmp_path, catalog_file):
    now = [100.0]
    service = make_broker(tmp_path, catalog_file, clock=lambda: now[0])
    pending = service.request(peer=broker.PeerIdentity(1001, 10, 20),
                              credential="requester-secret", **request_args())
    service.decide(pending["request_id"], "approve",
                   peer=broker.PeerIdentity(2001, 11, 21), credential="operator-secret")

    now[0] = 106.0
    with pytest.raises(broker.Expired):
        service.await_result(pending["request_id"], timeout=0)

    restarted = make_broker(tmp_path, catalog_file, clock=lambda: 101.0)
    with pytest.raises(broker.AmbiguousExecution):
        restarted.await_result(pending["request_id"], timeout=0)


def test_catalog_or_executable_mutation_after_approval_is_rejected(tmp_path, catalog_file, executable):
    service = make_broker(tmp_path, catalog_file)
    pending = service.request(peer=broker.PeerIdentity(1001, 10, 20),
                              credential="requester-secret", **request_args())
    service.decide(pending["request_id"], "approve",
                   peer=broker.PeerIdentity(2001, 11, 21), credential="operator-secret")
    executable.chmod(0o755)
    executable.write_text("changed", encoding="utf-8")
    executable.chmod(0o555)

    with pytest.raises(broker.IntegrityError):
        service.await_result(pending["request_id"], timeout=0)


def test_approval_view_is_inert_and_bounded(tmp_path, catalog_file):
    service = make_broker(tmp_path, catalog_file)
    pending = service.request(peer=broker.PeerIdentity(1001, 10, 20),
                              credential="requester-secret",
                              **request_args(reason="<b>approve</b>\x1b[31m" + "x" * 1000))

    view = service.operator_view(pending["request_id"], peer=broker.PeerIdentity(2001, 11, 21),
                                 credential="operator-secret")

    assert "<b>" not in view["reason"]
    assert "\x1b" not in view["reason"]
    assert len(view["reason"]) <= 260


def test_executor_uses_direct_argv_fixed_environment_and_combined_output_limit():
    executor = executor_module.Executor(timeout=2, max_output=1024)

    result = executor.execute_plan({
        "argv": ["/usr/bin/yes", "bounded"],
        "cwd": "/",
        "timeout_seconds": 2,
    })

    assert result["exit_code"] != 0
    assert result["truncated"] is True
    assert len(result["stdout"].encode()) + len(result["stderr"].encode()) <= 1100
    assert result["timed_out"] is False


def test_catalog_rejects_interpreters_and_scripts(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "version": 1,
        "operations": [{
            "id": "unsafe",
            "executable": sys.executable,
            "argv": ["-c", "print('no')"],
            "slots": {},
        }],
    }), encoding="utf-8")

    with pytest.raises(broker.InvalidRequest):
        broker.Catalog(catalog)


def test_separate_unix_endpoints_require_role_identity_and_credentials(tmp_path, catalog_file):
    socket_server = importlib.import_module("daemon.socket_server")
    service = make_broker(
        tmp_path, catalog_file,
        runner=lambda plan: {"exit_code": 0, "stdout": "done", "stderr": "", "truncated": False},
    )
    identities = {
        "requester": broker.PeerIdentity(1001, 10, 20),
        "operator": broker.PeerIdentity(2001, 11, 21),
    }
    server = socket_server.SocketServer(
        service, tmp_path / "request.sock", tmp_path / "operator.sock",
        decision_timeout=2, identity=lambda _client, role: identities[role],
    )
    server.start()
    request_message = {"credential": "requester-secret", "request": {
        "type": "request", **request_args(),
    }}
    response = {}

    def submit():
        response.update(socket_server.call(server.request_path, request_message))

    thread = threading.Thread(target=submit)
    thread.start()
    deadline = time.monotonic() + 2
    pending = []
    while not pending and time.monotonic() < deadline:
        pending = socket_server.call(server.operator_path, {
            "credential": "operator-secret", "request": {"type": "list"},
        }).get("pending", [])
    assert pending
    wrong = socket_server.call(server.operator_path, {
        "credential": "requester-secret",
        "request": {"type": "decide", "request_id": pending[0]["request_id"], "decision": "approve"},
    })
    assert wrong["status"] == "error"
    approved = socket_server.call(server.operator_path, {
        "credential": "operator-secret",
        "request": {"type": "decide", "request_id": pending[0]["request_id"], "decision": "approve"},
    })
    assert approved["status"] == "approved"
    thread.join(timeout=2)
    server.stop()
    assert response["status"] == "completed"
    assert response["result"]["stdout"] == "done"


def test_daemon_build_requires_disjoint_accounts_and_credential_files(tmp_path, catalog_file):
    vipd = importlib.import_module("daemon.vipd")
    requester_token = tmp_path / "requester.token"
    operator_token = tmp_path / "operator.token"
    requester_token.write_text("requester-secret-long", encoding="utf-8")
    operator_token.write_text("operator-secret-long", encoding="utf-8")
    config = {
        "catalog": str(catalog_file), "ledger": str(tmp_path / "ledger.jsonl"),
        "request_socket": str(tmp_path / "request.sock"),
        "operator_socket": str(tmp_path / "operator.sock"),
        "requester_uids": [1001], "operator_uids": [2001],
        "requester_credential_file": str(requester_token),
        "operator_credential_file": str(operator_token),
    }

    server = vipd.build_server(config)
    assert server.broker.requester_uids == frozenset({1001})
    assert server.broker.operator_uids == frozenset({2001})
    config["operator_uids"] = [1001]
    with pytest.raises(broker.InvalidRequest):
        vipd.build_server(config)
