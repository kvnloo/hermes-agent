"""A concurrent background review must not bypass stage_write's deduplication."""

import threading

from tools import write_approval as wa


def test_overlapping_reworded_replace_stages_once(monkeypatch):
    """Force both reviews to inspect the queue before the first record appears."""
    first_at_publish = threading.Event()
    second_scanned = threading.Event()
    original_find = wa._find_duplicate_pending
    original_replace = wa.os.replace

    def mark_second_scan(subsystem, payload):
        found = original_find(subsystem, payload)
        if threading.current_thread().name == "review-2":
            second_scanned.set()
        return found

    def hold_first_publish(src, dst):
        if threading.current_thread().name == "review-1":
            first_at_publish.set()
            second_scanned.wait(3)
        return original_replace(src, dst)

    monkeypatch.setattr(wa, "_find_duplicate_pending", mark_second_scan)
    monkeypatch.setattr(wa.os, "replace", hold_first_publish)

    records = {}
    errors = []

    def review(label, content):
        try:
            records[label] = wa.stage_write(
                wa.MEMORY,
                {"action": "replace", "target": "memory",
                 "old_text": "existing fact", "content": content},
                summary=label,
                origin="background_review",
            )
        except Exception as exc:
            errors.append(exc)

    first = threading.Thread(
        target=review, args=("first", "wording A"), name="review-1", daemon=True
    )
    second = threading.Thread(
        target=review, args=("second", "wording B"), name="review-2", daemon=True
    )
    first.start()
    assert first_at_publish.wait(10), errors
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not first.is_alive() and not second.is_alive(), "staging deadlocked"
    assert not errors, errors
    assert records["first"]["id"] == records["second"]["id"]
    assert len(wa.list_pending(wa.MEMORY)) == 1
