#!/usr/bin/env python3
"""Attribute egress-guard 'dns' lines to (test file, upstream source) from chs-egress.stacks dumps.

usage: chs_dns_attribution.py <stacks file>...   -> JSON on stdout (repo-relative names only)
"""
import json
import re
import sys

SOURCES = [("agent/model_metadata.py", "fetch_model_metadata", "OpenRouter model-metadata GET (agent init -> get_model_context_length)"),
           ("plugins/video_gen/openrouter/__init__.py", "_catalog", "OpenRouter video catalog GET (tool definitions build)")]
out = {}
for path in sys.argv[1:]:
    blocks = open(path, encoding="utf-8").read().split("----\n")
    per = {}
    for b in blocks:
        if not b.startswith("dns\t"):
            continue
        test = re.findall(r'File "(?:[^"]*?/)?((?:tests|evals)/[\w/]+\.py)"', b)
        src = next((label for f, fn, label in SOURCES if f in b and fn in b), "other")
        key = f"{test[0] if test else '?'} | {src}"
        per[key] = per.get(key, 0) + 1
    name = path.rsplit("/", 1)[-1]
    out[name] = {"total": sum(per.values()), "by_file_and_source": dict(sorted(per.items()))}
print(json.dumps(out, indent=1))
