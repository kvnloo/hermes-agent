"""F06-synthetic (T0): logcalls coverage and hit ratio, current vs patched parser, on seeded SYNTHETIC corpora.

No real state.db or agent.log is read. Line shapes are the ones the real producer (agent/turn_usage.py at
main) emitted in the round-trip receipt. Two corpora:
  * e19_shaped: a root plus 5 subagents; the root switches model mid-conversation (next call is a full
    miss with a cache write), every session has idle gaps past the cache TTL (full miss), and ~2% of
    responses carry no usage. Everything else reads the previous prefix from cache.
  * all_hit: same sizes, every call reads from cache, no usage-less responses.
state.db's sessions.api_call_count is set to the number of usage-bearing calls, which is what
agent/turn_usage.py queues (the usage=unavailable path returns before queue_token_counts).

    python f06_synth.py <repo> <main_logcalls.py> <patched_logcalls.py> <out_dir>
"""
import importlib.util
import io
import json
import random
import sqlite3
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

REPO, MAIN_PY, PATCHED_PY, OUT = sys.argv[1:5]
sys.path.insert(0, REPO)
OUT = Path(OUT)
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20261001


def build(corpus: str):
    rnd = random.Random(f"{SEED}:{corpus}")
    d = OUT / corpus
    d.mkdir(exist_ok=True)
    db, log = d / "state.db", d / "agent.log"
    for p in (db, log):
        if p.exists():
            p.unlink()
    c = sqlite3.connect(db)
    c.executescript("""
    CREATE TABLE sessions(id TEXT PRIMARY KEY, parent_session_id TEXT, source TEXT, started_at REAL, ended_at REAL,
        api_call_count INTEGER, input_tokens INTEGER, cache_read_tokens INTEGER, cache_write_tokens INTEGER,
        output_tokens INTEGER, estimated_cost_usd REAL, system_prompt_hash TEXT);
    CREATE TABLE system_prompts(hash TEXT PRIMARY KEY, prompt TEXT);
    CREATE TABLE messages(id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, tool_calls TEXT,
        tool_name TEXT, reasoning TEXT, timestamp REAL);
    CREATE TABLE state_meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    t0 = time.mktime((2026, 9, 6, 19, 0, 0, 0, 0, -1))
    lines, truth = [], {"metered": 0, "unavailable": 0, "zero_hit": 0, "hit_tokens": 0, "in_tokens": 0}
    sessions = [("s0", None, "cli", 120)] + [(f"s{i}", "s0", "subagent", 60) for i in range(1, 6)]
    for sid, parent, source, n_calls in sessions:
        prompt, prev_prompt, metered, cr_sum, cw_sum, in_sum, out_sum = 30_000, 0, 0, 0, 0, 0, 0
        model = "anthropic/claude-fable-5.1"
        switch_at = 60 if sid == "s0" else None
        ttl_gaps = set(rnd.sample(range(5, n_calls), 3))
        for n in range(1, n_calls + 1):
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0 + n * 7)) + f",{rnd.randrange(1000):03d}"
            head = f"{ts} INFO [{sid}] agent.conversation_loop: API call #{n}: "
            if corpus == "e19_shaped" and rnd.random() < 0.02:
                model_now = model if not (switch_at and n > switch_at) else "openai/gpt-6"
                lines.append(head + f"model={model_now} provider=nous in=? out=? total=? latency=4.1s usage=unavailable")
                truth["unavailable"] += 1
                continue
            appended = rnd.randrange(800, 6000)
            prompt += appended
            out = rnd.randrange(50, 900)
            miss = False
            if corpus == "e19_shaped":
                if n == 1 or (switch_at and n == switch_at + 1) or n in ttl_gaps:
                    miss = True
                if switch_at and n > switch_at:
                    model = "openai/gpt-6"
            elif n == 1:
                miss = False  # all_hit: even the first call reads a warm system-prompt prefix
            hit = 0 if miss else (prev_prompt if prev_prompt else 28_000)
            write = prompt - hit if (miss or rnd.random() < 0.7) else 0
            tail = f"model={model} provider=nous in={prompt} out={out} total={prompt + out} latency={rnd.uniform(1, 9):.1f}s"
            if hit:
                tail += f" cache={hit}/{prompt} ({100 * hit / prompt:.0f}%)"
            if write:
                tail += f" write={write}"
            tail += f" id=gen-{sid}-{n} upstream=Anthropic"
            lines.append(head + tail)
            metered += 1
            truth["metered"] += 1
            truth["zero_hit"] += int(hit == 0)
            truth["hit_tokens"] += hit
            truth["in_tokens"] += prompt
            cr_sum += hit; cw_sum += write; in_sum += max(0, prompt - hit - write); out_sum += out
            prev_prompt = prompt
        cost = cr_sum * 0.3e-6 + cw_sum * 3.75e-6 + in_sum * 3e-6 + out_sum * 15e-6
        start = t0 if parent is None else t0 + 30
        c.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (sid, parent, source, start, start + n_calls * 7, metered, in_sum, cr_sum, cw_sum, out_sum, cost, None))
    c.commit(); c.close()
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    truth["true_hit_ratio"] = round(truth["hit_tokens"] / truth["in_tokens"], 4)
    return db, log, truth


def run_parser(label, path, db, log, out):
    spec = importlib.util.spec_from_file_location(f"logcalls_{label}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.main(["--db", str(db), "--out", str(out), "--logs", str(log)])
    rep = json.loads((Path(out) / "logcalls.json").read_text(encoding="utf-8")) if rc == 0 else None
    return rc, buf.getvalue(), rep


result = {}
for corpus in ("e19_shaped", "all_hit"):
    db, log, truth = build(corpus)
    arms = {}
    for label, path in (("main", MAIN_PY), ("patched", PATCHED_PY)):
        rc, stdout, rep = run_parser(label, path, db, log, OUT / corpus / f"out_{label}")
        arms[label] = {"rc": rc, "stdout": stdout.strip().splitlines(), "report": rep}
    m, p = arms["main"]["report"], arms["patched"]["report"]
    summary = {
        "truth": truth,
        "coverage_fraction": {"main": m["coverage"]["fraction"], "patched": p["coverage"]["fraction"]},
        "calls_found": {"main": m["coverage"]["calls_found"], "patched": p["coverage"]["calls_found"]},
        "cache_hit_ratio_overall": {"main": m["observed"]["cache_hit_ratio_overall"], "patched": p["observed"]["cache_hit_ratio_overall"]},
        "hit_ratio_delta_pp": round(100 * (m["observed"]["cache_hit_ratio_overall"] - p["observed"]["cache_hit_ratio_overall"]), 2),
        "patched_new_fields": {k: p["coverage"].get(k) for k in ("zero_hit", "no_cache_field", "usage_unavailable")},
        "observed_block_identical": m["observed"] == p["observed"],
        "modeled_block_identical": m["modeled"] == p["modeled"],
        "coverage_identical_except_new_keys": {k: v for k, v in m["coverage"].items()} == {k: v for k, v in p["coverage"].items() if k not in ("zero_hit", "no_cache_field", "usage_unavailable")},
        "inputs_sha256": {},
    }
    import hashlib
    for f in (db, log):
        summary["inputs_sha256"][f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    result[corpus] = {"summary": summary, "arms": arms}
print(json.dumps({k: v["summary"] for k, v in result.items()}, indent=1))
(OUT / "f06_synth_full.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
