#!/usr/bin/env python3
"""Linux privilege broker daemon entry point.

This helper is packaged and installed separately from Hermes.  It does not
consume Hermes approval assertions; only its operator socket can decide.
"""

import argparse
import json
import signal
import threading
from pathlib import Path

from .broker import PrivilegeBroker
from .socket_server import SocketServer


def _credential(path):
    value = Path(path).read_text(encoding="utf-8").strip()
    if len(value) < 16:
        raise ValueError("credential file is empty or too short")
    return value


def build_server(config):
    required = {
        "catalog", "ledger", "request_socket", "operator_socket",
        "requester_uids", "operator_uids", "requester_credential_file",
        "operator_credential_file",
    }
    if set(config) - (required | {"ttl_seconds", "decision_timeout_seconds"}) or not required <= set(config):
        raise ValueError("invalid daemon configuration fields")
    broker = PrivilegeBroker(
        catalog_path=Path(config["catalog"]), ledger_path=Path(config["ledger"]),
        requester_uids={int(uid) for uid in config["requester_uids"]},
        operator_uids={int(uid) for uid in config["operator_uids"]},
        requester_credential=_credential(config["requester_credential_file"]),
        operator_credential=_credential(config["operator_credential_file"]),
        ttl_seconds=int(config.get("ttl_seconds", 15)),
    )
    return SocketServer(
        broker, Path(config["request_socket"]), Path(config["operator_socket"]),
        decision_timeout=float(config.get("decision_timeout_seconds", 15)),
    )


def main():
    parser = argparse.ArgumentParser(description="Typed single-execution privilege broker")
    parser.add_argument("--config", required=True, help="root-owned JSON configuration")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    server = build_server(config)
    stopped = threading.Event()

    def stop(_signum, _frame):
        stopped.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.start()
    try:
        stopped.wait()
    finally:
        server.stop()


if __name__ == "__main__":
    main()
