#!/usr/bin/env python3
"""F13: observer-hook kwargs at their emitters vs the documented field lists.

Static, stdlib only, no import or exec of Hermes code. Every input is read from a
git object (``git cat-file --batch`` on ``<rev>:<path>``), so a run is pinned by
the revisions passed in and the blob SHAs recorded in the receipt.

Code side: every ``*invoke_hook("<hook>", k=...)`` call in non-test Python whose
first argument is a member of ``hermes_cli.plugins.VALID_HOOKS``.

Doc side:
  - website/docs/developer-guide/observer-hooks.md: the per-hook "includes" /
    "fields include" paragraphs and their bullet lists, plus the Correlation IDs
    table (documented once for every hook). "same identity/runtime fields"
    inherits the identity: and runtime: bullets of the pre_api_request list.
  - website/docs/user-guide/features/hooks.md: the payload-field column of the
    plugin hook table (informational only).

A bullet of the form "- `name`: text" documents only `name`; any other bullet or
paragraph documents every backticked lowercase identifier in it.

Gate (pre-registered in the staging manifest): on base, the undocumented set for
post_api_request in observer-hooks.md contains first_chunk_at, context_length and
moa_references; on the branch it is empty. Negative controls: dropping each new
bullet from the branch text re-reports exactly that field, and injecting a
synthetic kwarg into the emitter is reported.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)

OBS = "website/docs/developer-guide/observer-hooks.md"
HOOKS_MD = "website/docs/user-guide/features/hooks.md"
PLUGINS_PY = "hermes_cli/plugins.py"
EMITTER = "agent/turn_response_intake.py"
TARGET_HOOK = "post_api_request"
EXPECTED_RED = {"first_chunk_at", "context_length", "moa_references"}
IDENT = re.compile(r"`([a-z_][a-z0-9_]*)`")
DEF_BULLET = re.compile(r"^- `([a-z_][a-z0-9_]*)`:")
START = re.compile(r"^(?:Common )?`([a-z_][a-z0-9_]*)`(?: fields)? includes?\b")
EXCLUDED_DIRS = ("tests/", "evals/", "website/", "optional-skills/", "skills/")


def git(repo: str, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", repo, *args], input=data, capture_output=True, check=True).stdout


def blobs(repo: str, rev: str, paths: list[str]) -> dict[str, tuple[str, bytes]]:
    """path -> (blob sha, content) for every path at rev, via one cat-file --batch."""
    req = "".join(f"{rev}:{p}\n" for p in paths).encode()
    out = git(repo, "cat-file", "--batch", data=req)
    res, i = {}, 0
    for p in paths:
        nl = out.index(b"\n", i)
        header = out[i:nl].decode().split()
        if header[-1] == "missing":
            i = nl + 1
            continue
        sha, size = header[0], int(header[2])
        res[p] = (sha, out[nl + 1 : nl + 1 + size])
        i = nl + 1 + size + 1
    return res


def valid_hooks(src: str) -> set[str]:
    for node in ast.parse(src).body:
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == "VALID_HOOKS" and isinstance(node.value, ast.Set):
            return {e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    raise SystemExit("VALID_HOOKS not found")


def scan_calls(path: str, src: str, hooks: set[str]) -> list[dict]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
        first = node.args[0]
        if not name.endswith("invoke_hook") or not (isinstance(first, ast.Constant) and first.value in hooks):
            continue
        sites.append({
            "hook": first.value, "file": path, "line": node.lineno,
            "keys": sorted(k.arg for k in node.keywords if k.arg),
            "star_kwargs": any(k.arg is None for k in node.keywords),
        })
    return sites


def blocks(text: str) -> list[list[str]]:
    """Blank-line separated blocks, ignoring fenced code."""
    out, cur, fence = [], [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if line.strip():
            cur.append(line)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def bullet_keys(lines: list[str]) -> tuple[set[str], set[str]]:
    """(all keys, identity+runtime keys) from a bullet list, joining continuation lines."""
    items, keys, inherit = [], set(), set()
    for line in lines:
        if line.startswith("- "):
            items.append(line)
        elif items:
            items[-1] += " " + line.strip()
    for item in items:
        m = DEF_BULLET.match(item)
        found = {m.group(1)} if m else set(IDENT.findall(item))
        keys |= found
        if re.match(r"^- (identity|runtime):", item):
            inherit |= found
    return keys, inherit


def observer_doc_keys(text: str) -> tuple[dict[str, set[str]], set[str]]:
    """hook -> documented keys from observer-hooks.md, and the Correlation IDs keys."""
    bl = blocks(text)
    correlation: set[str] = set()
    in_corr = False
    for b in bl:
        if b[0].startswith("## "):
            in_corr = b[0].strip() == "## Correlation IDs"
            continue
        if in_corr and b[0].startswith("|"):
            for row in b[2:]:
                cell = row.split("|")[1]
                correlation |= set(IDENT.findall(cell))
    per: dict[str, set[str]] = {}
    raw: dict[str, tuple[str, set[str], set[str]]] = {}
    for idx, b in enumerate(bl):
        m = START.match(b[0])
        if not m:
            continue
        hook = m.group(1)
        para = " ".join(b)
        keys = set(IDENT.findall(para)) - {hook}
        inherit: set[str] = set()
        if para.rstrip().endswith(":") and idx + 1 < len(bl) and bl[idx + 1][0].startswith("- "):
            k2, inherit = bullet_keys(bl[idx + 1])
            keys |= k2
        raw[hook] = (para, keys, inherit)
    for hook, (para, keys, _inherit) in raw.items():
        if "same identity/runtime fields" in para and "pre_api_request" in raw:
            keys = keys | raw["pre_api_request"][2]
        elif "same identity fields" in para:
            pre = hook.replace("post_", "pre_", 1)
            if pre in raw:
                keys = keys | raw[pre][1]
        per[hook] = keys
    return per, correlation


def hooks_md_keys(text: str, hooks: set[str]) -> dict[str, set[str]]:
    per = {}
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        names = IDENT.findall(cells[0])
        if names and names[0] in hooks and names[0] not in per:
            per[names[0]] = set(IDENT.findall(cells[3]))
    return per


def code_keys(sites: list[dict]) -> dict[str, set[str]]:
    per: dict[str, set[str]] = {}
    for s in sites:
        per.setdefault(s["hook"], set()).update(s["keys"])
    return per


def evaluate(code: dict[str, set[str]], obs_text: str) -> dict:
    per, corr = observer_doc_keys(obs_text)
    target = per.get(TARGET_HOOK, set()) | corr
    return {
        "undocumented": sorted(code.get(TARGET_HOOK, set()) - target),
        "documented_section_keys": sorted(per.get(TARGET_HOOK, set())),
    }


def drop_bullet(text: str, field: str) -> str:
    out, skip = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith(f"- `{field}`:"):
            skip = True
            continue
        if skip and line.startswith("  "):
            continue
        skip = False
        out.append(line)
    return "".join(out)


def inject_kwarg(src: str) -> str:
    return src.replace('"post_api_request",\n', '"post_api_request",\n                zz_f13_probe=1,\n', 1)


def portable(arg: str) -> str:
    """Receipts carry no absolute local paths: paths under the cwd become relative,
    the scratch repo becomes <scratch>/h.git, anything else <local>/<basename>."""
    if not os.path.isabs(arg):
        return arg
    cwd = os.getcwd()
    if arg == cwd or arg.startswith(cwd + os.sep):
        return os.path.relpath(arg, cwd)
    base = os.path.basename(arg.rstrip(os.sep))
    return "<scratch>/" + base if base.endswith(".git") else "<local>/" + base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default="F13/r20261001-01")
    ap.add_argument("--supersedes", default=None)
    ap.add_argument("--reps", type=int, default=1,
                    help="repeat the full read+evaluate pass N times (deterministic check: all N must agree)")
    a = ap.parse_args()
    t0 = time.time()
    rep_fingerprints = []
    for _rep in range(max(1, a.reps)):
        base = git(a.repo, "rev-parse", a.base).decode().strip()
        head = git(a.repo, "rev-parse", a.head).decode().strip()

        py = [p for p in git(a.repo, "ls-tree", "-r", "--name-only", base).decode().splitlines()
              if p.endswith(".py") and not p.startswith(EXCLUDED_DIRS) and "/tests/" not in p]
        base_files = blobs(a.repo, base, py + [OBS, HOOKS_MD])
        head_docs = blobs(a.repo, head, [OBS, HOOKS_MD])
        changed = git(a.repo, "diff", "--name-only", base, head).decode().split()
        hooks = valid_hooks(base_files[PLUGINS_PY][1].decode())

        sites = []
        for p in py:
            if p in base_files:
                sites += scan_calls(p, base_files[p][1].decode("utf-8", "replace"), hooks)
        code = code_keys(sites)
        target_sites = [s for s in sites if s["hook"] == TARGET_HOOK]

        obs_base = base_files[OBS][1].decode()
        obs_head = head_docs[OBS][1].decode()
        red = evaluate(code, obs_base)
        green = evaluate(code, obs_head)

        negatives = []
        for f in sorted(EXPECTED_RED):
            r = evaluate(code, drop_bullet(obs_head, f))
            negatives.append({"mutation": f"drop the `{f}` bullet from the branch page",
                              "undocumented": r["undocumented"], "re_red": r["undocumented"] == [f]})
        inj_src = inject_kwarg(base_files[EMITTER][1].decode())
        inj_sites = [s for s in sites if s["file"] != EMITTER] + scan_calls(EMITTER, inj_src, hooks)
        r = evaluate(code_keys(inj_sites), obs_head)
        negatives.append({"mutation": f"inject kwarg zz_f13_probe into the {EMITTER} post_api_request call",
                          "undocumented": r["undocumented"], "re_red": r["undocumented"] == ["zz_f13_probe"]})

        rep_fingerprints.append(json.dumps({"sites": sites, "red": red, "green": green, "negatives": negatives},
                                           sort_keys=True))
    reps_identical = len(set(rep_fingerprints)) == 1

    # Informational: the whole matrix (not gated).
    obs_per_base, corr = observer_doc_keys(obs_base)
    hm_base = hooks_md_keys(base_files[HOOKS_MD][1].decode(), hooks)
    hm_head = hooks_md_keys(head_docs[HOOKS_MD][1].decode(), hooks)
    matrix = {}
    for hook in sorted(code):
        row = {"emitter_sites": [f'{s["file"]}:{s["line"]}' for s in sites if s["hook"] == hook],
               "code_keys": sorted(code[hook])}
        if hook in obs_per_base:
            row["observer_hooks_md_undocumented"] = sorted(code[hook] - obs_per_base[hook] - corr)
        if hook in hm_base:
            row["hooks_md_table_undocumented_base"] = sorted(code[hook] - hm_base[hook])
            row["hooks_md_table_undocumented_head"] = sorted(code[hook] - hm_head.get(hook, set()))
        matrix[hook] = row

    red_pass = EXPECTED_RED <= set(red["undocumented"])
    green_pass = green["undocumented"] == [] and reps_identical
    neg_pass = all(n["re_red"] for n in negatives)
    n_reps = len(rep_fingerprints)
    reps_note = f"{n_reps if green_pass else 0}/{n_reps}"
    receipt = {
        "schema": "xf.receipt.v1",
        "id": a.run_id,
        "supersedes": a.supersedes,
        "spec": {"kind": "static", "tier": "T0", "cost": "$0", "lane": "cpu",
                 "question": "Does every kwarg the post_api_request emitter passes appear in observer-hooks.md?",
                 "falsifier": "base already documents all three fields (no need) or the branch still leaves any emitted kwarg undocumented",
                 "observer_effect": "none: static read of git blobs, no Hermes import or exec"},
        "staging": "observer-hooks-doc-drift",
        "origin_refs": ["NousResearch/hermes-agent#64231", "NousResearch/hermes-agent#16106"],
        "base_revision": base,
        "head_revision": head,
        "changed_files": changed,
        "command": " ".join(["python3"] + [portable(x) for x in sys.argv]),
        "inputs": {
            "base": {p: base_files[p][0] for p in (OBS, HOOKS_MD, PLUGINS_PY, EMITTER)},
            "head": {p: head_docs[p][0] for p in (OBS, HOOKS_MD)},
            "python_files_scanned": len(py),
            "checker_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        },
        "env": {"python": platform.python_version(), "network": "none used", "hermes_home": "not read"},
        "valid_hooks": len(hooks),
        "target_hook": {"hook": TARGET_HOOK, "emitter_sites": [f'{s["file"]}:{s["line"]}' for s in target_sites],
                        "code_keys": sorted(code.get(TARGET_HOOK, set())),
                        "correlation_table_keys": sorted(corr)},
        "gates": {
            "red": {"arm": "base", "result": "PASS" if red_pass else "FAIL", "expected_subset": sorted(EXPECTED_RED),
                    "observed_undocumented": red["undocumented"], "label": "OBSERVED"},
            "green": {"arm": "head", "result": "PASS" if green_pass else "FAIL",
                      "observed_undocumented": green["undocumented"], "reps": reps_note,
                      "reps_identical": reps_identical, "label": "OBSERVED"},
            "negative_control": {"result": "PASS" if neg_pass else "FAIL", "cases": negatives, "label": "OBSERVED"},
        },
        "measurements": [
            {"name": "post_api_request_undocumented_keys", "arm": "base", "value": len(red["undocumented"]), "unit": "count", "label": "OBSERVED"},
            {"name": "post_api_request_undocumented_keys", "arm": "head", "value": len(green["undocumented"]), "unit": "count", "label": "OBSERVED"},
            {"name": "hooks_with_detected_invoke_hook_site", "value": len(code), "of": len(hooks), "unit": "count", "label": "OBSERVED"},
        ],
        "informational_matrix": matrix,
        "informational_matrix_note": "Not gated. Token matching only: prose mentions (e.g. api_request_error `error = {...}`, subagent_stop role/status fields, Payload Safety legacy fields) show up as undocumented. Each entry needs a source read before any doc claim.",
        "not_tested": [
            "hook dispatch through helpers other than *invoke_hook (stream observers, fire_pre_command_hook, shell hooks): not scanned; the matrix lists only hooks with a detected invoke_hook site",
            "runtime payload values (types, None cases): the doc text was checked by source reading, not by a running agent",
            "Docusaurus build (no website node_modules in the sandbox)",
        ],
        "resource_usage": {"wall_s": round(time.time() - t0, 2), "api_cost_usd": 0.0},
        "verdict": "KEEP" if (red_pass and green_pass and neg_pass) else "DISCARD",
        "ai_assistance": "Claude Code (Opus 5.5) wrote this checker and the doc edit",
        "privacy": "public-aggregate",
    }
    with open(a.out, "w") as fh:
        json.dump(receipt, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(json.dumps({"verdict": receipt["verdict"], "red": receipt["gates"]["red"]["observed_undocumented"],
                      "green": receipt["gates"]["green"]["observed_undocumented"],
                      "negatives": [n["re_red"] for n in negatives], "green_reps": reps_note,
                      "wall_s": receipt["resource_usage"]["wall_s"]}))
    return 0 if receipt["verdict"] == "KEEP" else 1


if __name__ == "__main__":
    sys.exit(main())
