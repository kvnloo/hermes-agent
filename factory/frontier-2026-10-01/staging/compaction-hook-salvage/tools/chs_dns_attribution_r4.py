#!/usr/bin/env python3
"""Attribute r4 egress-guard 'dns'/'connect' lines to (thread, test file, upstream source) from chs-egress.stacks dumps.

usage: chs_dns_attribution_r4.py <stacks file>...   -> JSON on stdout (repo-relative names only)

r4 stack blocks start with "<kind>\t<detail>\tthread=<name>". A lookup on the openrouter-prewarm thread has no
test frame (the thread outlives the test that started it), so it is attributed to the thread, not a test file.
"""
import json
import re
import sys

SOURCES = [
    ("agent/model_metadata.py", "fetch_model_metadata", "OpenRouter model-metadata GET (fetch_model_metadata)"),
    ("plugins/video_gen/openrouter/__init__.py", "_catalog", "OpenRouter video catalog GET (tool definitions build)"),
]


def main(paths):
    out = {}
    for path in paths:
        try:
            blocks = open(path, encoding="utf-8").read().split("----\n")
        except FileNotFoundError:
            blocks = []
        per = {}
        for b in blocks:
            if not b.startswith(("dns\t", "connect\t")):
                continue
            head = b.split("\n", 1)[0].split("\t")
            kind = head[0]
            thread = next((p[7:] for p in head[1:] if p.startswith("thread=")), "?")
            test = re.findall(r'File "(?:[^"]*?/)?((?:tests|evals)/[\w/]+\.py)"', b)
            src = next((label for f, fn, label in SOURCES if f in b and fn in b), "other")
            where = test[0] if test else ("(no test frame: openrouter-prewarm thread)" if thread == "openrouter-prewarm" else "?")
            key = f"{kind} | thread={thread} | {where} | {src}"
            per[key] = per.get(key, 0) + 1
        name = path.rsplit("/", 1)[-1]
        out[name] = {"total": sum(per.values()), "by_thread_file_and_source": dict(sorted(per.items()))}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
