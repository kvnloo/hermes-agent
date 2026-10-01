import json, os, subprocess, sys
from pathlib import Path
# run from the worktree root: negative_controls.py <raw_out_dir>; TESTHOME = isolated HOME for run_tests.sh
TH = os.environ["TESTHOME"]
RAW = Path(sys.argv[1])
F = Path("agent/context_compressor.py")
orig = F.read_text(encoding="utf-8")
ERR_BLOCK = ('    ("error messages", re.compile(\n'
             '        r"(?:(?:^|(?<=[`\\"])|(?<=\\\\n))(?:fatal|[Ee]rror)|\\berror TS\\d{4,5}|\\bGraphQL|\\bBlocked): "\n'
             '        r"(?![%{])(?:(?!\\\\n)[^\\n]){8,110}", re.M), 20),\n')
assert ERR_BLOCK in orig, "error block not found"
TASK = '    ("task ids", re.compile(r"\\b(?:sa-\\d+-[0-9a-f]{8}|t_[0-9a-f]{8})\\b"), 40),  # delegate_tool / kanban_db ids\n'
DOT = '    ("dotted keys", re.compile(r"\\b[a-z][a-z0-9_]*(?:\\.[a-z][a-z0-9_]*)*\\.[a-z][a-z0-9]*_[a-z0-9_]*[a-z0-9](?!\\.?\\w)"), 40),\n'
assert TASK in orig and DOT in orig
muts = [
    ("drop row 'task ids'", TASK, ""),
    ("drop row 'dotted keys'", DOT, ""),
    ("drop row 'error messages'", ERR_BLOCK, ""),
    ("dotted keys: last segment no longer needs '_'", "\\.[a-z][a-z0-9]*_[a-z0-9_]*[a-z0-9](?!\\.?\\w)", "\\.[a-z][a-z0-9_]*[a-z0-9](?!\\.?\\w)"),
    ("error messages: fatal:/error: anywhere (\\b instead of line-start anchor)", '(?:^|(?<=[`\\"])|(?<=\\\\n))(?:fatal|[Ee]rror)', '\\b(?:fatal|[Ee]rror)'),
    ("error messages: drop the escaped-newline anchor (?<=\\\\n)", '|(?<=\\\\n))', ')'),
    ("error messages: drop the quote/backtick anchor (?<=[`\"])", '|(?<=[`\\"])', ''),
    ("error messages: drop re.M", '{8,110}", re.M), 20)', '{8,110}"), 20)'),
    ("error messages: drop the %s/{} placeholder guard", '(?![%{])', ''),
    ("error messages: value no longer stops at an escaped newline", '(?:(?!\\\\n)[^\\n]){8,110}', '[^\\n]{8,110}'),
]
out = []
try:
    for name, old, new in muts:
        assert orig.count(old) == 1, (name, orig.count(old))
        F.write_text(orig.replace(old, new), encoding="utf-8")
        env = {**os.environ, "HOME": TH, "HERMES_HOME": f"{TH}/.hermes",
               "HERMES_PYTHON": os.environ["HERMES_PYTHON"]}
        p = subprocess.run(["bash", "scripts/run_tests.sh", "-j", "2", "tests/agent/test_context_compressor_anchor_index.py", "-q"],
                           env=env, capture_output=True, text=True, timeout=600)
        txt = p.stdout + p.stderr
        summ = next((l for l in txt.splitlines() if "Summary:" in l), "")
        failed = [l.split("::")[-1].strip() for l in txt.splitlines() if l.startswith("FAILED ")]
        first_err = next((l.strip()[:200] for l in txt.splitlines() if l.strip().startswith("E ") and "Error" in l), "")
        import re as _re
        exec(compile(F.read_text(encoding="utf-8").split("_ANCHOR_NOISE")[0].split("_LEAN_ANCHOR_BUDGET_CHARS = 7_000")[1], "m", "exec"), {"re": _re})  # mutated table must compile
        out.append({"mutation": name, "rc": p.returncode, "summary": summ.strip("= ").strip(), "failed": sorted(set(failed)), "first_assertion": first_err})
        print(name, "->", summ, failed)
finally:
    F.write_text(orig, encoding="utf-8")
(RAW / "negative_controls.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
