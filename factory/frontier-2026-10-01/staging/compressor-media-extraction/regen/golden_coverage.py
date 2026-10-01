#!/usr/bin/env python3
"""Corpus coverage for golden_parity.py: how often the moved code does real work.

Replays the exact seeded corpus of ``golden_parity.py`` (same generator, same RNG draws in the
same order) and counts, per conversation, whether each moved entry point changed anything.
It answers "did the parity run exercise the rewrite paths, or only their no-op branches?".

    PYTHONPATH=<tree> HOME=<tmp> HERMES_HOME=<tmp>/.hermes $PY golden_coverage.py --n 400 --out coverage.json

Counters (all per conversation unless noted):

* ``with_images``: some dict message has image content (``_content_has_images`` or
  ``_tool_content_has_images`` is true).
* ``strip_historical_changed``: ``_strip_historical_media`` returned a list whose canonical JSON
  differs from the input.
* ``retire_rewrote``: ``_retire_stale_tool_result_images`` returned a count > 0.
* ``outbound_evicted``: ``evict_stale_outbound_tool_images`` returned a count > 0.
* ``outbound_messages_rewritten``: the sum of those counts over all conversations (equal to the
  number of messages whose canonical JSON changed; the script asserts this).

Run it on base and head: the counts must be identical, because the digests are.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import golden_parity as g  # noqa: E402  (same corpus generator and loopback socket guard)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--out")
    a = ap.parse_args()
    _src, f = g.resolve()
    rng = random.Random(a.seed)

    def safe(fn, *args, **kw):
        try:
            return fn(*args, **kw)
        except Exception as exc:  # mirror golden_parity: errors are values, not crashes
            return ("EXC", type(exc).__name__, str(exc))

    cov = {"conversations": 0, "with_images": 0, "strip_historical_changed": 0, "retire_rewrote": 0,
           "outbound_evicted": 0, "outbound_messages_rewritten": 0}
    changed_messages = 0
    for _ in range(a.n):
        # The RNG draws below must stay in the same order as golden_parity.main().
        msgs = g.conversation(rng)
        dicts = [m for m in msgs if isinstance(m, dict)]
        k = rng.randint(0, len(msgs))
        spared = range(k, min(len(msgs), k + rng.randint(0, 3)))
        out = safe(f["_strip_historical_media"], copy.deepcopy(msgs), spared=spared)
        n2 = safe(f["_retire_stale_tool_result_images"], copy.deepcopy(msgs), keep_newest=rng.randint(0, 4),
                  spared=spared)
        m3 = copy.deepcopy(dicts)
        n3 = safe(f["evict_stale_outbound_tool_images"], m3)

        cov["conversations"] += 1
        cov["with_images"] += any(
            safe(f["_content_has_images"], m.get("content")) is True
            or safe(f["_tool_content_has_images"], m.get("content")) is True
            for m in dicts
        )
        cov["strip_historical_changed"] += g.canon(out) != g.canon(msgs)
        cov["retire_rewrote"] += isinstance(n2, int) and n2 > 0
        if isinstance(n3, int) and n3 > 0:
            cov["outbound_evicted"] += 1
            cov["outbound_messages_rewritten"] += n3
        changed_messages += sum(g.canon(x) != g.canon(y) for x, y in zip(m3, dicts))

    if changed_messages != cov["outbound_messages_rewritten"]:
        print(f"inconsistent: evict counted {cov['outbound_messages_rewritten']} rewrites, "
              f"{changed_messages} messages changed", file=sys.stderr)
        return 1
    text = json.dumps(cov)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
