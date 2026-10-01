#!/usr/bin/env python3
"""Differential output parity for the moved media functions (no model, no network).

Runs a deterministic fixture corpus through the media functions of one tree and prints the
sha256 of the canonical JSON of every output. Run it once per tree with that tree on
PYTHONPATH and compare the digests:

    PYTHONPATH=<tree> HOME=<tmp> HERMES_HOME=<tmp>/.hermes $PY golden_parity.py --n 400 --out tree.json

The functions are resolved from ``agent.context_compressor_media`` when it exists, else from
``agent.context_compressor``. Identical digests mean every call returned the same value and left
its (copied) input mutated the same way on both trees, i.e. the bytes the send path and the
compactor hand to the provider are unchanged for this corpus.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import random
import socket
import sys

_real_connect = socket.socket.connect


def _guard(self, addr):  # loopback-only: the corpus never needs the network
    host = addr[0] if isinstance(addr, tuple) else addr
    if host not in ("127.0.0.1", "::1", "localhost") and not str(host).startswith("/"):
        raise OSError(f"egress blocked: {addr!r}")
    return _real_connect(self, addr)


socket.socket.connect = _guard

NAMES = (
    "_strip_historical_media", "_retire_stale_tool_result_images", "evict_stale_outbound_tool_images",
    "_summary_part_text", "_image_part_label", "_content_has_images", "_tool_content_has_images",
    "_image_payload", "_strip_images_from_tool_msg", "_strip_images_from_content", "_is_image_part",
    "_tool_result_parts", "_replace_image_parts", "_rewritten",
)


def resolve():
    try:
        mod = importlib.import_module("agent.context_compressor_media")
        src = "agent.context_compressor_media"
    except ModuleNotFoundError:
        mod = importlib.import_module("agent.context_compressor")
        src = "agent.context_compressor"
    return src, {n: getattr(mod, n) for n in NAMES}


def image_part(rng: random.Random):
    kind = rng.choice(["image_url_dict", "image_url_str", "input_image", "image_source", "image_url_http"])
    blob = "data:image/png;base64," + "A" * rng.choice([16, 400, 5000])
    if kind == "image_url_dict":
        return {"type": "image_url", "image_url": {"url": blob}}
    if kind == "image_url_str":
        return {"type": "image_url", "image_url": blob}
    if kind == "input_image":
        return {"type": "input_image", "image_url": blob}
    if kind == "image_source":
        return {"type": "image", "source": {"type": "base64", "data": "B" * rng.choice([10, 300])}}
    return {"type": "image_url", "image_url": {"url": f"https://example.invalid/{rng.randint(0, 99)}.png"}}


def content(rng: random.Random, role: str):
    r = rng.random()
    if r < 0.35:
        return f"{role} text {rng.randint(0, 999)}"
    if r < 0.45 and role == "tool":
        return {"_multimodal": True, "content": [{"type": "text", "text": "shot"}, image_part(rng)],
                "text_summary": rng.choice(["", "a screenshot of a page", None])}
    if r < 0.5:
        return None if role != "tool" else "ok"
    parts = []
    for _ in range(rng.randint(1, 4)):
        p = rng.random()
        if p < 0.45:
            parts.append(image_part(rng))
        elif p < 0.85:
            parts.append({"type": rng.choice(["text", "input_text"]), "text": f"t{rng.randint(0, 99)}"})
        elif p < 0.95:
            parts.append(f"bare string {rng.randint(0, 9)}")
        else:
            parts.append({"type": "file", "file": {"id": "f"}})
    return parts


def conversation(rng: random.Random):
    msgs = []
    # One in six conversations is long and image-heavy so the send-path eviction (provider
    # limit: 20 image blocks / 24 MB) actually fires, not just its no-op path.
    long_mode = rng.random() < 1 / 6
    for i in range(rng.randint(24, 48) if long_mode else rng.randint(1, 18)):
        if long_mode and i and rng.random() < 0.6:
            imgs = [image_part(rng) for _ in range(rng.randint(1, 3))]
            msgs.append({"role": "tool", "tool_call_id": f"c{i}", "content": [{"type": "text", "text": "shot"}, *imgs]})
            continue
        role = rng.choice(["user", "assistant", "tool", "tool", "system"]) if i else rng.choice(["user", "system"])
        m = {"role": role, "content": content(rng, role)}
        if role == "tool":
            m["tool_call_id"] = f"c{i}"
        if role == "assistant" and rng.random() < 0.3:
            m["tool_calls"] = [{"id": f"c{i + 1}", "type": "function", "function": {"name": "vision_analyze", "arguments": "{}"}}]
        if rng.random() < 0.2:
            m["api_content"] = "sidecar"
        msgs.append(m)
    if rng.random() < 0.1:
        msgs.insert(rng.randint(0, len(msgs)), "not-a-dict")
    return msgs


def canon(x):
    return json.dumps(x, sort_keys=True, default=repr, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261001)
    ap.add_argument("--out")
    a = ap.parse_args()
    src, f = resolve()
    rng = random.Random(a.seed)
    acc = {n: hashlib.sha256() for n in NAMES}
    calls = {n: 0 for n in NAMES}

    def rec(name, value):
        acc[name].update(canon(value).encode())
        acc[name].update(b"\n")
        calls[name] += 1

    def safe(fn, *args, **kw):
        try:
            return fn(*args, **kw)
        except Exception as exc:  # parity covers error behaviour too
            return ("EXC", type(exc).__name__, str(exc))

    for _ in range(a.n):
        msgs = conversation(rng)
        dicts = [m for m in msgs if isinstance(m, dict)]
        k = rng.randint(0, len(msgs))
        spared = range(k, min(len(msgs), k + rng.randint(0, 3)))
        m1 = copy.deepcopy(msgs)
        out = safe(f["_strip_historical_media"], m1, spared=spared)
        rec("_strip_historical_media", [out is m1, out, m1])
        m2 = copy.deepcopy(msgs)
        n2 = safe(f["_retire_stale_tool_result_images"], m2, keep_newest=rng.randint(0, 4), spared=spared)
        rec("_retire_stale_tool_result_images", [n2, m2])
        m3 = copy.deepcopy(dicts)
        n3 = safe(f["evict_stale_outbound_tool_images"], m3)
        rec("evict_stale_outbound_tool_images", [n3, m3])
        for m in dicts:
            c = m.get("content")
            rec("_content_has_images", safe(f["_content_has_images"], c))
            rec("_tool_content_has_images", safe(f["_tool_content_has_images"], c))
            rec("_tool_result_parts", safe(f["_tool_result_parts"], c))
            rec("_image_payload", list(safe(f["_image_payload"], m)))
            rec("_strip_images_from_content", safe(f["_strip_images_from_content"], copy.deepcopy(c)))
            rec("_replace_image_parts", safe(f["_replace_image_parts"], copy.deepcopy(c), "[x]"))
            rec("_rewritten", safe(f["_rewritten"], copy.deepcopy(m), "new"))
            if m.get("role") == "tool":
                rec("_strip_images_from_tool_msg", safe(f["_strip_images_from_tool_msg"], copy.deepcopy(m)))
            if isinstance(c, list):
                for p in c:
                    rec("_is_image_part", safe(f["_is_image_part"], p))
                    if isinstance(p, (dict, str)):
                        rec("_summary_part_text", safe(f["_summary_part_text"], p))
                    if safe(f["_is_image_part"], p):
                        rec("_image_part_label", safe(f["_image_part_label"], p))
    digests = {n: acc[n].hexdigest() for n in NAMES}
    overall = hashlib.sha256(canon(digests).encode()).hexdigest()
    res = {"resolved_from": src, "n": a.n, "seed": a.seed, "calls": calls, "digests": digests, "overall": overall,
           "python": sys.version.split()[0]}
    text = json.dumps(res, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
