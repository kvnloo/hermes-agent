"""Build receipts/F01-r20261001-04.json from the round-4 runs (rebased head on main 44a1ce9724).

Copies sanitized raw files into receipts/raw/*-r04/ and hashes them. No network.
usage: WT=<worktree> HERMES_PYTHON=<test interpreter> make_receipt_r04.py <scratch dir> <staging dir>
"""
import hashlib
import json
import os
import re
import socket
import sys
from pathlib import Path

S = Path(sys.argv[1])
D = Path(sys.argv[2])
WT_ABS = os.environ["WT"]                 # the worktree (absolute), replaced by $WT
VENV_PY = os.environ["HERMES_PYTHON"]     # the test interpreter, replaced by <venv-python>
HOST = socket.gethostname()               # replaced by <local-workstation>
HOME_DIR = os.path.expanduser("~")       # replaced by <home>
P = S / "st-edit-fuzzy"
RAW = D / "receipts" / "raw"

SUBS = [
    (re.compile(r"/var/tmp/hermes-pytest-\d+/r-[A-Za-z0-9_]+/pytest-of-[^/\s]+"), "<pytest-tmp>"),
    (re.compile(re.escape(WT_ABS)), "$WT"),
    (re.compile(re.escape(str(S))), "$S"),
    (re.compile(re.escape(VENV_PY) + r"[0-9.]*"), "<venv-python>"),
    (re.compile(r"\b" + re.escape(HOST) + r"\b"), "<local-workstation>"),
    (re.compile(re.escape(HOME_DIR) + r"\b"), "<home>"),
]
LEAK = re.compile("|".join([re.escape(x) for x in (str(S), WT_ABS, VENV_PY, HOME_DIR)]
                           + [r"\b" + re.escape(HOST) + r"\b", r"/var/tmp/hermes-pytest-\d", r"pytest-of-[a-z]",
                              r"@gmail\.", r"@protonmail\."]))


def sanitize(text):
    for rx, rep in SUBS:
        text = rx.sub(rep, text)
    return text


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def keep(src, rel):
    dst = RAW / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = sanitize(Path(src).read_text(encoding="utf-8"))
    leak = LEAK.search(text)
    if leak:
        raise SystemExit(f"leak in {src}: {leak.group(0)!r}")
    dst.write_text(text, encoding="utf-8")
    return {"path": f"receipts/raw/{rel}", "sha256": sha256(dst)}


FILE_RE = re.compile(r"\] [✓✗] (\S+) \((\d+)✓(?: (\d+)s)?(?: (\d+)✗)?")
CONTRACT = "tests/tools/test_fuzzy_match_wrong_region.py"
# count the pytest failure lines only (the live progress preview repeats the first one)
MARKER = re.compile(r"(?m)^E\s+AssertionError: wrong region replaced via (block_anchor|context_aware): count=1, error=None")


def parse_log(path):
    text = Path(path).read_text(encoding="utf-8")
    head = text.splitlines()[0]
    meta = dict(kv.split("=", 1) for kv in head[2:].split() if "=" in kv)
    files = {}
    for m in FILE_RE.finditer(text):
        files[m.group(1)] = {"passed": int(m.group(2)), "failed": int(m.group(4) or 0),
                             "skipped": int(m.group(3) or 0)}
    failed = sorted({re.sub(r" - .*", "", l[len("FAILED "):]) for l in text.splitlines()
                     if l.startswith("FAILED ")})
    rc = re.search(r"^# rc=(\d+)", text, re.M)
    summ = re.search(r"^=== Summary: (.*) ===$", text, re.M)
    markers = {}
    for m in MARKER.finditer(text):
        markers[m.group(1)] = markers.get(m.group(1), 0) + 1
    return {"meta": meta, "files": files, "failed_ids": failed,
            "rc": int(rc.group(1)) if rc else None, "summary": summ.group(1) if summ else None,
            "marker_lines": markers}


runs = {}
for log in sorted((P / "runs-v4").rglob("*.log")):
    arm = log.parent.name
    rel = f"runs-r04/{arm}/{log.name}"
    runs[rel] = {**parse_log(log), "log": keep(log, rel)}

fresh = {}
for log in sorted((P / "fresh-v4").rglob("*.log")):
    rel = f"fresh-r04/{log.parent.name}/{log.name}"
    fresh[rel] = {**parse_log(log), "log": keep(log, rel)}


def contract(r):
    return r["files"].get(CONTRACT)


def run(arm, name):
    return runs[f"runs-r04/{arm}/{name}.log"]


ARMS = ["base", "c54575", "c125376-leaf", "both", "leaf+fold", "both+fold", "c126502", "c126502+leaf+fold"]
ab = {}
for arm in ARMS:
    reps = []
    for rep in (1, 2, 3):
        r = run(arm, f"proof.rep{rep}")
        reps.append({"rep": rep, "contract": contract(r),
                     "carrier_tests": {k: v for k, v in r["files"].items() if k != CONTRACT},
                     "fuzzy_match_sha256_16": r["meta"].get("fuzzy_match.py"),
                     "failed_ids": r["failed_ids"], "log": r["log"]})
    first = reps[0]["contract"]
    ab[arm] = {"contract_passed_of_10": first["passed"], "contract_failed_of_10": first["failed"],
               "reps_agree": all(x["contract"] == first for x in reps)
               and all(x["carrier_tests"] == reps[0]["carrier_tests"] for x in reps),
               "carrier_tests_cross_applied": arm not in ("c126502", "c126502+leaf+fold"),
               "reps": reps}

red_c = run("base", "commit-only.rep1")
sab = {}
for m in ("floor", "single_line", "foldin"):
    r = run("both+fold", f"sabotage-{m}.rep1")
    sab[m] = {"files": r["files"], "failed_ids": r["failed_ids"],
              "fuzzy_match_sha256_16": r["meta"].get("fuzzy_match.py"), "log": r["log"]}
adj = {}
for arm in ("base", "c54575", "c125376-leaf", "both+fold", "c126502"):
    r = run(arm, "adjacent.rep1")
    tot = {"passed": sum(v["passed"] for v in r["files"].values()),
           "failed": sum(v["failed"] for v in r["files"].values()),
           "skipped": sum(v["skipped"] for v in r["files"].values())}
    adj[arm] = {"files": r["files"], "total": tot, "failed_ids": r["failed_ids"], "summary": r["summary"], "log": r["log"]}

aux = {}
for sub, names in (("e01-v4", None), ("m01-v4", None), ("probes-v4", None), ("cov-v4", None)):
    d = P / sub
    if not d.exists():
        continue
    for f in sorted(d.iterdir()):
        if f.suffix in (".json", ".txt"):
            rel = f"{sub.replace('-v4', '-r04')}/{f.name}"
            aux[rel] = keep(f, rel)

scripts = {}
for name in ("build_overlay_v4.sh", "run_arm_v4.sh", "run_all_v4.sh", "run_e01_m01_v4.sh", "make_receipt_r04.py", "write_r04.py", "run_arm_fresh_v4.sh"):
    scripts[name] = keep(P / name, f"scripts/{name}")

out = {"fresh": fresh, "runs": runs, "ab": ab, "red_contract_only": red_c, "sabotage": sab, "adjacent": adj,
       "aux": aux, "scripts": scripts}
json.dump(out, open(P / "r04_parsed.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps({a: (v["contract_passed_of_10"], v["contract_failed_of_10"], v["reps_agree"]) for a, v in ab.items()}))
print("red commit-only", contract(red_c), red_c["marker_lines"])
print("sabotage", {m: (v["files"].get(CONTRACT), len(v["failed_ids"])) for m, v in sab.items()})
print("adjacent", {a: v["total"] for a, v in adj.items()})
print("adjacent failed", {a: v["failed_ids"] for a, v in adj.items() if v["failed_ids"]})
