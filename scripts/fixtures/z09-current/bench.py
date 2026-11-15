"""Measure rtk (pipe filters) and headroom (compress) on real terminal outputs from corpus.jsonl.

Run with the headroom tool venv:  HEADROOM_OFFLINE=1 ~/.local/share/uv/tools/headroom-ai/bin/python bench.py
Writes results.jsonl + prints a summary. Neither tool sees the network (HEADROOM_OFFLINE=1, rtk telemetry off).
"""
import json, os, re, shlex, subprocess, sys, time
from pathlib import Path

os.environ["HEADROOM_OFFLINE"] = "1"
HERE = Path(__file__).parent
rows = [json.loads(l) for l in (HERE / "corpus.jsonl").read_text().splitlines()]

try:
    import tiktoken
    enc = tiktoken.get_encoding("o200k_base")
    ntok = lambda s: len(enc.encode(s, disallowed_special=()))
except Exception:
    ntok = lambda s: len(s) // 4

def first_cmd(cmd):
    seg = re.split(r"&&|\|\||;|\n", cmd)
    for s in seg:
        s = s.strip()
        if not s or s.startswith(("cd ", "export ", "source ", ". ")):
            continue
        try:
            w = shlex.split(s)
        except Exception:
            w = s.split()
        w = [x for x in w if "=" not in x.split("/")[0] or x.startswith("-")]  # drop VAR=val prefixes
        return w
    return []

def rtk_filter(cmd):
    w = first_cmd(cmd)
    if not w:
        return None
    a = os.path.basename(w[0]); b = w[1] if len(w) > 1 else ""
    if a == "git" and b in ("log", "diff", "status"):
        return f"git-{b}"
    if a in ("rg", "grep", "find", "fd", "tsc", "mypy", "vitest", "pytest"):
        return a
    if a == "cargo" and b == "test":
        return "cargo-test"
    if a == "go" and b in ("test", "build"):
        return f"go-{b}"
    if a == "ruff":
        return "ruff-check"
    if "run_tests.sh" in a or "pytest" in cmd:
        return "pytest"
    return None

from headroom import compress

out = []
t0 = time.time()
for i, r in enumerate(rows):
    o = r["output"]; base = ntok(o)
    rec = {"i": i, "cmd": r["cmd"][:200], "base_tok": base}
    f = rtk_filter(r["cmd"])
    rec["rtk_filter"] = f
    for name, filt in (("rtk", f), ("rtk_log", "log")):
        if not filt:
            continue
        t = time.time()
        p = subprocess.run(["rtk", "pipe", "-f", filt], input=o, capture_output=True, text=True, timeout=30)
        rec[f"{name}_tok"] = ntok(p.stdout) if p.returncode == 0 and p.stdout.strip() else base
        rec[f"{name}_ms"] = int((time.time() - t) * 1000)
        if name == "rtk":
            rec["rtk_out"] = p.stdout[:3000]
    t = time.time()
    msgs = [{"role": "user", "content": "run it"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function",
             "function": {"name": "terminal", "arguments": json.dumps({"command": r["cmd"]})}}]},
            {"role": "tool", "tool_call_id": "c1", "content": o}]
    try:
        res = compress(msgs, model="claude-opus-4-20250514", protect_recent=0, mode=os.environ.get("HR_MODE") or None)
        c = res.messages[-1]["content"]
        c = c if isinstance(c, str) else json.dumps(c)
        rec["hr_tok"] = ntok(c); rec["hr_out"] = c[:3000]
    except Exception as e:
        rec["hr_tok"] = base; rec["hr_err"] = repr(e)[:200]
    rec["hr_ms"] = int((time.time() - t) * 1000)
    out.append(rec)
    if i % 100 == 0:
        print(i, f"{time.time()-t0:.0f}s", flush=True)

(HERE / "results.jsonl").write_text("".join(json.dumps(x) + "\n" for x in out))
B = sum(x["base_tok"] for x in out)
def tot(k, alt="base_tok"): return sum(x.get(k, x[alt]) for x in out)
print(f"samples={len(out)} base_tok={B}")
print(f"rtk(command-matched, {sum(1 for x in out if x['rtk_filter'])} matched): {1-tot('rtk_tok')/B:.1%} saved")
print(f"rtk log filter on everything: {1-tot('rtk_log_tok')/B:.1%} saved")
print(f"headroom: {1-tot('hr_tok')/B:.1%} saved, errors={sum(1 for x in out if 'hr_err' in x)}, "
      f"p50 ms={sorted(x['hr_ms'] for x in out)[len(out)//2]}")
best = sum(min(x.get('rtk_tok', x['base_tok']), x['hr_tok']) for x in out)
print(f"best-of(rtk matched, headroom): {1-best/B:.1%} saved")
