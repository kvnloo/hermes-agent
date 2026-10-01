"""F09 gate probe for compression.anthropic_context_editing (T1, $0, loopback only).

Runs the REAL ``AIAgent`` turn loop of the checkout given by ``--repo`` against the SDK-oracle
Anthropic Messages fake (``tests/fakes/providers/anthropic_messages.py`` of that checkout). Native
cells reach it through an in-process TLS-intercepting ``HTTPS_PROXY`` for ``api.anthropic.com``;
the third-party cell talks to the fake's loopback ``/anthropic`` URL directly. Nothing leaves
127.0.0.1: a loopback-only ``socket.connect`` guard (lifted from
``evals/provider_fallback/probe_104260.py``) records and refuses anything else, and the process
environment is cleared and re-seeded with a throwaway HOME/HERMES_HOME before any import.

Usage: python f09_gate_probe.py --repo <checkout> --arm <name> --out <json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", required=True)
ap.add_argument("--arm", required=True)
ap.add_argument("--out", required=True)
ARGS = ap.parse_args()
REPO = str(Path(ARGS.repo).resolve())

sys.dont_write_bytecode = True
SANDBOX = tempfile.TemporaryDirectory(prefix="f09-ace-")
os.environ.clear()
os.environ.update(
    HOME=SANDBOX.name, HERMES_HOME=SANDBOX.name + "/hermes", PATH="/usr/bin:/bin",
    PYTHONDONTWRITEBYTECODE="1", HERMES_DISABLE_MODEL_METADATA_FETCH="1",
    HERMES_DISABLE_LAZY_INSTALLS="1", TIRITH_ENABLED="false", AWS_EC2_METADATA_DISABLED="true",
    TZ="UTC", LANG="C.UTF-8",
)
Path(os.environ["HERMES_HOME"]).mkdir()
os.chdir(SANDBOX.name)
sys.path.insert(0, REPO)

import socket  # noqa: E402

_original_connect = socket.socket.connect
BLOCKED: list[str] = []


def _loopback_only(self, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
        BLOCKED.append(str(address))
        raise RuntimeError("F09 probe blocks non-loopback network")
    return _original_connect(self, address)


socket.socket.connect = _loopback_only

import logging  # noqa: E402
import subprocess  # noqa: E402

logging.basicConfig(level=logging.ERROR)

from tests.fakes.providers.anthropic_messages import (  # noqa: E402
    AnthropicMessagesServer, ApiError, Reply, Text,
)
from tests.fakes.providers.oauth_token_server import TLSInterceptProxy, make_test_ca  # noqa: E402

HOST = "api.anthropic.com"
BETA = "context-management-2025-06-27"
REJECTION = "context_management: Extra inputs are not permitted"
HOME = Path(os.environ["HERMES_HOME"])


def _write_config(lines: list[str]) -> None:
    (HOME / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _agent(base_url: str | None, model: str = "claude-sonnet-4-5"):
    from run_agent import AIAgent

    return AIAgent(api_key="sk-ant-api03-fake-key", base_url=base_url, provider="anthropic", model=model,
                   quiet_mode=True, skip_context_files=True, skip_memory=True, enabled_toolsets=["file"],
                   max_iterations=3)


class Wire:
    def __init__(self) -> None:
        self.responder = lambda _r: Reply([Text("ok")])
        self.srv = AnthropicMessagesServer(lambda r: self.responder(r)).start()
        ca = make_test_ca(Path(SANDBOX.name) / "ca", [HOST])
        self.proxy = TLSInterceptProxy(self.srv, ca, [HOST]).start()
        for var in ("HTTPS_PROXY", "https_proxy"):
            os.environ[var] = self.proxy.url
        for var in ("NO_PROXY", "no_proxy"):
            os.environ[var] = "127.0.0.1,localhost"
        os.environ["SSL_CERT_FILE"] = str(ca.ca_pem)

    def reset(self, responder=None) -> int:
        self.responder = responder or (lambda _r: Reply([Text("ok")]))
        return len(self.srv.requests)

    def facts(self, start: int) -> list[dict]:
        out = []
        for r in self.srv.requests[start:]:
            if r["kind"] != "main":
                continue
            body = r["body"]
            out.append({
                "context_management": body.get("context_management"),
                "beta_header": r["headers"].get("anthropic-beta", ""),
                "beta_present": BETA in r["headers"].get("anthropic-beta", "").split(","),
                "schema_errors": r["schema_errors"],
                "body_sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(),
                "body_minus_system_sha256": hashlib.sha256(json.dumps(
                    {k: v for k, v in body.items() if k != "system"}, sort_keys=True).encode()).hexdigest(),
                "system_sha256": hashlib.sha256(json.dumps(body.get("system"), sort_keys=True).encode()).hexdigest(),
                "headers_sha256": hashlib.sha256(json.dumps(
                    {k: v for k, v in sorted(r["headers"].items()) if k not in ("content-length", "host", "x-stainless-retry-count", "x-stainless-read-timeout")},
                    sort_keys=True).encode()).hexdigest(),
            })
        return out

    def close(self) -> None:
        self.proxy.stop()
        self.srv.stop()


def gate_cell(wire: Wire, name: str, config: list[str], *, base_url: str | None, model: str = "claude-sonnet-4-5",
              expect_payload: bool) -> dict:
    _write_config(config)
    start = wire.reset()
    agent = _agent(base_url, model)
    result = agent.run_conversation("hi")
    facts = wire.facts(start)
    sent = [f["context_management"] is not None for f in facts]
    return {"cell": name, "completed": bool(result.get("completed")), "requests": len(facts),
            "payload_sent": sent, "beta_present": [f["beta_present"] for f in facts],
            "payload": facts[0]["context_management"] if facts else None,
            "schema_errors": [f["schema_errors"] for f in facts if f["schema_errors"]],
            "local_threshold_tokens": getattr(agent.context_compressor, "threshold_tokens", None),
            "expect_payload": expect_payload,
            "pass": bool(result.get("completed") and facts and all(s == expect_payload for s in sent)
                         and all(b == expect_payload for b in [f["beta_present"] for f in facts]))}


def rejection_cell(wire: Wire) -> dict:
    _write_config(["compression:", "  anthropic_context_editing: true"])

    def responder(record):
        if "context_management" in record["body"]:
            return ApiError(400, "invalid_request_error", REJECTION)
        return Reply([Text("ok")])

    start = wire.reset(responder)
    agent = _agent(f"https://{HOST}")
    first = agent.run_conversation("hi")
    second = agent.run_conversation("again", conversation_history=first["messages"])
    sent = [f["context_management"] is not None for f in wire.facts(start)]
    return {"cell": "structured_400_disable_and_retry_once", "turn1_completed": bool(first.get("completed")),
            "turn2_completed": bool(second.get("completed")), "payload_sent_per_request": sent,
            "flag_after": getattr(agent, "anthropic_context_editing", None),
            "pass": bool(first.get("completed") and second.get("completed") and sent == [True, False, False])}


def over_threshold_cell(wire: Wire, *, enabled: bool) -> dict:
    """Real usage above the local trigger: local compression must still fire on the next turn."""
    _write_config(["compression:", f"  anthropic_context_editing: {'true' if enabled else 'false'}"])
    replies = [Reply([Text("big")], input_tokens=60_000), Reply([Text("ok")], input_tokens=9_000),
               Reply([Text("ok")], input_tokens=9_000)]
    start = wire.reset(lambda _r: replies.pop(0) if replies else Reply([Text("ok")]))
    agent = _agent(f"https://{HOST}")
    agent.compression_enabled = True
    cc = agent.context_compressor
    cc.threshold_tokens = 50_000
    calls: list[int] = []

    def counting(messages, system_message, **kw):
        calls.append(len(wire.srv.requests))
        sys_prompt = system_message.get("content") if isinstance(system_message, dict) else system_message
        return messages, kw.get("active_system_prompt") or sys_prompt

    agent._compress_context = counting  # type: ignore[method-assign]
    r1 = agent.run_conversation("first")
    before_t2 = len(calls)
    r2 = agent.run_conversation("second", conversation_history=r1["messages"])
    facts = wire.facts(start)
    return {"cell": f"over_threshold_local_fallback_{'on' if enabled else 'off'}",
            "turn1_completed": bool(r1.get("completed")), "turn2_completed": bool(r2.get("completed")),
            "local_threshold_tokens": cc.threshold_tokens, "turn1_real_input_tokens": 60_000,
            "local_compress_calls_turn1": before_t2, "local_compress_calls_turn2": len(calls) - before_t2,
            "payload_sent_per_request": [f["context_management"] is not None for f in facts],
            "trigger_sent": [f["context_management"]["edits"][0]["trigger"]["value"]
                             for f in facts if f["context_management"]],
            "pass": bool(r1.get("completed") and r2.get("completed") and len(calls) - before_t2 >= 1)}


def flag_off_wire_cell(wire: Wire) -> dict:
    """Default config (key absent): record the exact wire for byte comparison across arms."""
    _write_config(["model:", "  context_length: 200000"])
    start = wire.reset()
    agent = _agent(f"https://{HOST}")
    r1 = agent.run_conversation("hello there")
    r2 = agent.run_conversation("and again", conversation_history=r1["messages"])
    main = [r for r in wire.srv.requests[start:] if r["kind"] == "main"]
    system = json.dumps(main[0]["body"].get("system")) if main else None
    return {"cell": "flag_absent_wire", "completed": bool(r1.get("completed") and r2.get("completed")),
            "requests": wire.facts(start),
            # The system prompt is synthetic, but it embeds host facts (temp HOME path, kernel string,
            # python version). Only the sha256 of its host-normalised form is kept, never the text.
            "system_normalised_sha256": hashlib.sha256(_normalise_host(system).encode()).hexdigest() if system else None,
            "system_host_substitutions": _host_substitutions(system) if system else []}


_HOST_PATTERNS = [
    ("<SANDBOX>", lambda: re.escape(SANDBOX.name)),
    ("Host: <HOST>", lambda: r"Host: [^\\\n\"]*"),
    ("python3=<PY>", lambda: r"python3=[0-9][0-9.]*"),
]


def _normalise_host(text: str) -> str:
    for placeholder, pattern in _HOST_PATTERNS:
        text = re.sub(pattern(), placeholder, text)
    return text


def _host_substitutions(text: str) -> list[dict]:
    return [{"placeholder": placeholder, "count": len(re.findall(pattern(), text))}
            for placeholder, pattern in _HOST_PATTERNS]


def main() -> int:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    wire = Wire()
    native = f"https://{HOST}"
    try:
        cells = [
            gate_cell(wire, "native_claude_flag_false", ["compression:", "  anthropic_context_editing: false"],
                      base_url=native, expect_payload=False),
            gate_cell(wire, "native_claude_flag_true", ["compression:", "  anthropic_context_editing: true"],
                      base_url=native, expect_payload=True),
            gate_cell(wire, "native_claude_flag_true_compression_disabled",
                      ["compression:", "  enabled: false", "  anthropic_context_editing: true"],
                      base_url=native, expect_payload=False),
            gate_cell(wire, "native_claude_flag_true_checkpoint_required",
                      ["compression:", "  checkpoint_required: true", "  anthropic_context_editing: true"],
                      base_url=native, expect_payload=False),
            gate_cell(wire, "native_non_claude_flag_true", ["compression:", "  anthropic_context_editing: true"],
                      base_url=native, model="glm-4.6", expect_payload=False),
            gate_cell(wire, "third_party_endpoint_flag_true", ["compression:", "  anthropic_context_editing: true"],
                      base_url=wire.srv.base_url, expect_payload=False),
            rejection_cell(wire),
            over_threshold_cell(wire, enabled=True),
            over_threshold_cell(wire, enabled=False),
            flag_off_wire_cell(wire),
        ]
    finally:
        wire.close()
    out = {"schema": "f09.gate_probe.v1", "arm": ARGS.arm, "repo_head": head, "cells": cells,
           "egress_blocked": BLOCKED, "sdk_schema_errors_total": sum(
               len(c.get("schema_errors") or []) for c in cells)}
    Path(ARGS.out).write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({c["cell"]: c.get("pass") for c in cells}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
