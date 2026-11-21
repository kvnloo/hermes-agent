"""Stdlib AB/BA connection-open benchmark; run on groot, not in ChatGPT."""
from __future__ import annotations

import json
import statistics
import time
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from gateway import hosted_room_connection_reuse as reuse
from gateway import hosted_rooms as rooms
from gateway.hosted_room_policy_checkpoint import HostedRoomPolicyCheckpoint
from hermes_cli.sqlite_util import open_db


def _calls(path, checkpoint, n):
    errors = 0
    for index in range(n):
        try:
            if index % 2:
                if checkpoint.publication_exists(
                    room_id="room-1", task_id="absent", status="settled", execution_generation=1
                ):
                    errors += 1
            elif rooms.list_room_link_records(path):
                errors += 1
        except Exception:
            errors += 1
    return errors, n


def main():
    with TemporaryDirectory(prefix="dsa-conn-reuse-") as directory:
        path = Path(directory) / "shared-state.db"
        rooms.create_room(path, room_id="room-1", name="Bench", members=[],
                          authority_gateway_id="gateway-a", now=1)
        checkpoint = HostedRoomPolicyCheckpoint(path)
        try:
            for n in (100, 1000, 5000):
                times = {"old": [], "new": []}
                errors = {"old": 0, "new": 0}
                work = {"old": 0, "new": 0}
                for run in range(7):
                    for arm in (("old", "new") if run % 2 == 0 else ("new", "old")):
                        context = patch.object(reuse, "open_reused", open_db) if arm == "old" else nullcontext()
                        with context:
                            start = time.perf_counter_ns()
                            bad, done = _calls(path, checkpoint, n)
                            times[arm].append(time.perf_counter_ns() - start)
                        errors[arm] += bad
                        work[arm] += done
                print(json.dumps({
                    "case": "hosted_rooms_and_policy", "calls_per_run": n, "runs": 7,
                    "old": {"median_ns_7": int(statistics.median(times["old"])),
                            "error_count": errors["old"], "work_count": work["old"]},
                    "new": {"median_ns_7": int(statistics.median(times["new"])),
                            "error_count": errors["new"], "work_count": work["new"]},
                }, sort_keys=True))
        finally:
            reuse.close_all()


if __name__ == "__main__":
    main()
