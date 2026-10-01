"""Line-coverage probe for FACTORY P4 (stdlib sys.settrace; coverage.py is not
installed in the test interpreter and nothing is installed into it).

usage (from the worktree root, hermetic env like scripts/run_tests.sh):
  python cov_probe.py <arm-label> <out.json> <pytest args...>

Records, per test id, every executed line of tools/fuzzy_match.py,
tools/file_operations.py and tools/patch_parser.py. Hits in fuzzy_match.py are
tagged "seam" when the call stack runs through file_operations.py or
patch_parser.py (the live patch_replace / patch_v4a path), else "direct" (the
test's own fuzzy_find_and_replace call that only feeds the failure message).
Then reports landmark lines (located by source text, so the same report works
on every arm) per test.
"""
import ast
import json
import os
import re
import sys
import threading

import pytest

ROOT = os.getcwd()
TARGETS = {os.path.join(ROOT, p): p for p in (
    "tools/fuzzy_match.py", "tools/file_operations.py", "tools/patch_parser.py")}
SEAM_FILES = {os.path.join(ROOT, "tools/file_operations.py"), os.path.join(ROOT, "tools/patch_parser.py")}
FM = os.path.join(ROOT, "tools/fuzzy_match.py")

current = {"test": "<collect>"}
hits = {}  # (test, relpath, line, via) -> count


def _via(frame):
    f = frame.f_back
    while f is not None:
        if f.f_code.co_filename in SEAM_FILES:
            return "seam"
        f = f.f_back
    return "direct"


def _global(frame, event, arg):
    fn = frame.f_code.co_filename
    rel = TARGETS.get(fn)
    if rel is None:
        return None
    via = _via(frame) if fn == FM else "seam"

    def _local(fr, ev, a):
        if ev == "line":
            k = (current["test"], rel, fr.f_lineno, via)
            hits[k] = hits.get(k, 0) + 1
        return _local
    return _local


class _Plugin:
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        current["test"] = item.nodeid
        yield
        current["test"] = "<between>"


def _line_of(rel, pattern, func=None, offset=0):
    src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    lines = src.split("\n")
    rx = re.compile(pattern)
    ranges = [(1, len(lines))]
    if func:
        # every definition with that name (a base class may declare an abstract one first);
        # the first one whose body contains the pattern wins
        ranges = [(node.lineno, node.end_lineno) for node in ast.walk(ast.parse(src))
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func]
    for lo, hi in sorted(ranges):
        found = [i for i in range(lo, hi + 1) if rx.search(lines[i - 1])]
        if found:
            return found[0] + offset
    return None


def main():
    label, out = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    sys.settrace(_global)
    threading.settrace(_global)
    rc = pytest.main(args, plugins=[_Plugin()])
    sys.settrace(None)
    threading.settrace(None)

    landmarks = {
        # fuzzy_match.py
        "fm.block_anchor.similar_ratio": ("tools/fuzzy_match.py", r"return SequenceMatcher\(None, content_middle, pattern_middle\)\.ratio\(\) >= threshold", "_strategy_block_anchor", 0),
        "fm.context_aware.single_line_guard": ("tools/fuzzy_match.py", r"^    if (n == 1|len\(pattern\.strip\(\)\.split\('\\n'\)\) == 1):", "_strategy_context_aware", 0),
        "fm.context_aware.single_line_guard.return": ("tools/fuzzy_match.py", r"^    if (n == 1|len\(pattern\.strip\(\)\.split\('\\n'\)\) == 1):", "_strategy_context_aware", None),
        "fm.context_aware.accept_all_lines": ("tools/fuzzy_match.py", r"return all\($", "_strategy_context_aware", 0),
        "fm.floor.check": ("tools/fuzzy_match.py", r"_normalized_similarity\(content\[start:end\], old_string\) >= _FUZZY_CONTENT_FLOOR", "fuzzy_find_and_replace", 0),
        "fm.floor.continue": ("tools/fuzzy_match.py", r"^                continue$", "fuzzy_find_and_replace", 0),
        "fm.replacement_applied": ("tools/fuzzy_match.py", r"return new_content, len\(matches\), strategy_name, None", "fuzzy_find_and_replace", 0),
        "fm.no_match_return": ("tools/fuzzy_match.py", r"Could not find a match for old_string in the file", "fuzzy_find_and_replace", 0),
        # file_operations.py (patch_replace seam)
        "fo.patch_replace.calls_matcher": ("tools/file_operations.py", r"fuzzy_find_and_replace\($", "patch_replace", 0),
        "fo.patch_replace.write_file": ("tools/file_operations.py", r"write_result = self\.write_file\(path, new_content", "patch_replace", 0),
        "fo.patch_replace.no_match_result": ("tools/file_operations.py", r"return self\._no_match_result\(", "patch_replace", 0),
        "fo.patch_v4a.apply": ("tools/file_operations.py", r"return apply_v4a_operations\(operations, self\)", "patch_v4a", 0),
        # patch_parser.py (patch_v4a seam)
        "pp.validate.calls_matcher": ("tools/patch_parser.py", r"fuzzy_find_and_replace\($", "_validate_operations", 0),
        "pp.apply_update.calls_matcher": ("tools/patch_parser.py", r"new_content, count, _strategy, error = fuzzy_find_and_replace\($", "_apply_update", 0),
        "pp.apply_update.fail_no_match": ("tools/patch_parser.py", r'return _fail\(f"Could not apply hunk: \{error\}"', "_apply_update", 0),
        "pp.apply_update.write_file": ("tools/patch_parser.py", r"write_result = file_ops\.write_file\(op\.file_path, new_content", "_apply_update", 0),
    }
    resolved = {}
    for name, (rel, pat, func, off) in landmarks.items():
        if off is None:
            ln = _line_of(rel, pat, func, 0)
            # the guard's "return []" is the first return after the comment block
            if ln:
                src = open(os.path.join(ROOT, rel), encoding="utf-8").read().split("\n")
                j = ln
                while j < len(src) and src[j].strip() != "return []":
                    j += 1
                ln = j + 1 if j < len(src) else None
        else:
            ln = _line_of(rel, pat, func, off)
        resolved[name] = {"file": rel, "line": ln}

    tests = sorted({k[0] for k in hits if not k[0].startswith("<")})
    per_test = {}
    for t in tests:
        row = {}
        for name, loc in resolved.items():
            if loc["line"] is None:
                row[name] = "absent"
                continue
            vias = sorted({k[3] for k in hits if k[0] == t and k[1] == loc["file"] and k[2] == loc["line"]})
            row[name] = "+".join(vias) if vias else "-"
        per_test[t] = row
    totals = {}
    for rel in TARGETS.values():
        seam_lines = {k[2] for k in hits if k[1] == rel and k[3] == "seam" and not k[0].startswith("<")}
        totals[rel] = {"distinct_lines_hit_via_seam": len(seam_lines)}
    json.dump({"arm": label, "pytest_rc": int(rc), "landmarks": resolved, "per_test": per_test,
               "totals": totals, "method": "stdlib sys.settrace line events; via=seam when the stack passes through tools/file_operations.py or tools/patch_parser.py"},
              open(out, "w"), indent=1, sort_keys=True)
    print(f"{label}: pytest rc={int(rc)}, {len(tests)} tests traced -> {out}")


if __name__ == "__main__":
    main()
