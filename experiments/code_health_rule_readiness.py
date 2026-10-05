#!/usr/bin/env python3
"""Fork-only readiness study for semantic code-health rules.

Freeze a deterministic corpus of merged PRs, replay the current checker, and emit
per-rule adoption cost plus source-context samples for manual true/false-positive labeling.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from scripts.code_health import gitio
from scripts.code_health.config import RULES_BY_ID
from scripts.code_health.compare import compare
from scripts.code_health.measure import Measurer
from scripts.code_health.replay import pr_range
from scripts.code_health.report import apply_allows
from scripts.code_health.ruff_runner import resolve_ruff

_QUERY = """
query($q: String!, $after: String) {
  search(query: $q, type: ISSUE, first: 50, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest {
      number title mergedAt url
      mergeCommit { oid }
      commits(last: 100) { totalCount nodes { commit { messageHeadline } } }
    } }
  }
}"""

SEMANTIC_PREFIXES = ("HX", "PS-")


def _gh_candidates(repo: Path, since: str, cap: int = 1000) -> list[dict]:
    prs: list[dict] = []
    after = None
    q = (
        "repo:NousResearch/hermes-agent is:pr is:merged base:main "
        f"merged:>={since} sort:updated-desc"
    )
    while len(prs) < cap:
        args = ["gh", "api", "graphql", "-f", f"query={_QUERY}", "-f", f"q={q}"]
        if after:
            args += ["-f", f"after={after}"]
        proc = subprocess.run(
            args, cwd=repo, capture_output=True, text=True, encoding="utf-8",
            timeout=120, check=True, stdin=subprocess.DEVNULL,
        )
        data = json.loads(proc.stdout)["data"]["search"]
        prs.extend(n for n in data["nodes"] if n.get("mergeCommit") and n.get("mergedAt"))
        if not data["pageInfo"]["hasNextPage"]:
            break
        after = data["pageInfo"]["endCursor"]
    # Search order can move when old PRs get comments. Freeze by actual merge timestamp.
    prs.sort(key=lambda p: (p["mergedAt"], p["number"]), reverse=True)
    return prs[:cap]


def freeze_sample(repo: Path, limit: int, since: str, out: Path) -> list[dict]:
    candidates = _gh_candidates(repo, since)
    if len(candidates) < limit:
        raise RuntimeError(f"only {len(candidates)} merged PRs found since {since}; need {limit}")
    sample = candidates[:limit]
    out.write_text(json.dumps(sample, indent=2) + "\n", encoding="utf-8")
    return sample


def replay_semantic_one(repo: Path, measurer: Measurer, base: str, head: str) -> list[dict]:
    changes = gitio.changed_files(repo, base, head)
    head_paths = sorted({
        c.new for c in changes
        if c.new and c.new.endswith(".py") and gitio.read_file(repo, head, c.new) is not None
    })
    base_paths = sorted({
        c.old for c in changes
        if c.old and c.old.endswith(".py") and gitio.read_file(repo, base, c.old) is not None
    })
    if not head_paths:
        return []
    measurer.ctx.known_env = gitio.known_env_names(repo, base)
    base_m = measurer.measure(base, base_paths)
    head_m = measurer.measure(head, head_paths)
    findings = compare(base_m, head_m, changes)
    apply_allows(findings, head_m)
    return [
        {
            "path": f.path, "rule": f.rule, "scope": f.scope, "line": f.line,
            "detail": f.detail, "blocking": f.blocking, "allowed_reason": f.allowed_reason,
        }
        for f in findings
        if f.allowed_reason is None and f.rule.startswith(SEMANTIC_PREFIXES)
    ]


def _context(repo: Path, head: str, path: str, line: int, radius: int = 3) -> str:
    try:
        text = gitio.git(repo, "show", f"{head}:{path}")
    except RuntimeError:
        return "<unavailable>"
    rows = text.splitlines()
    lo = max(1, line - radius)
    hi = min(len(rows), line + radius)
    return "\n".join(
        f"{n:>5} {'>' if n == line else ' '} {rows[n - 1]}"
        for n in range(lo, hi + 1)
    )


def _pick(items: list[dict], n: int) -> list[dict]:
    if len(items) <= n:
        return items
    if n <= 1:
        return [items[0]]
    # Deterministic spread across the full occurrence list.
    idxs = sorted({round(i * (len(items) - 1) / (n - 1)) for i in range(n)})
    return [items[i] for i in idxs]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=300)
    p.add_argument("--since", default="2026-09-01")
    p.add_argument("--examples-per-rule", type=int, default=12)
    p.add_argument("--out", default="rule-readiness")
    args = p.parse_args(argv)

    repo = gitio.repo_root(Path.cwd())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sample_path = out / "sample.json"
    sample = freeze_sample(repo, args.limit, args.since, sample_path)

    measurer = Measurer(repo, resolve_ruff(repo), known_env=set())
    per_rule_findings: Counter[str] = Counter()
    per_rule_prs: Counter[str] = Counter()
    occurrences: dict[str, list[dict]] = defaultdict(list)
    rows: list[dict] = []
    errors = 0

    for index, pr in enumerate(sample, start=1):
        try:
            base, head = pr_range(repo, pr)
            findings = replay_semantic_one(repo, measurer, base, head)
        except Exception as exc:
            errors += 1
            rows.append({
                "number": pr["number"], "title": pr["title"], "mergedAt": pr["mergedAt"],
                "error": f"{type(exc).__name__}: {exc}",
            })
            continue

        semantic = [
            f for f in findings
            if f.get("rule", "").startswith(SEMANTIC_PREFIXES)
        ]
        rules = {f["rule"] for f in semantic}
        per_rule_prs.update(rules)
        per_rule_findings.update(f["rule"] for f in semantic)

        for finding in semantic:
            item = {
                "number": pr["number"],
                "title": pr["title"],
                "mergedAt": pr["mergedAt"],
                "base": base,
                "head": head,
                "path": finding["path"],
                "line": finding["line"],
                "scope": finding["scope"],
                "detail": finding["detail"],
                "blocking": finding["blocking"],
            }
            occurrences[finding["rule"]].append(item)

        rows.append({
            "number": pr["number"], "title": pr["title"], "mergedAt": pr["mergedAt"],
            "base": base, "head": head, "semantic_findings": semantic,
        })
        if index % 25 == 0:
            print(f"replayed {index}/{len(sample)}", flush=True)

    for rule, items in occurrences.items():
        items.sort(key=lambda x: (x["mergedAt"], x["number"], x["path"], x["line"]))
        for item in _pick(items, args.examples_per_rule):
            item["context"] = _context(repo, item["head"], item["path"], item["line"])

    semantic_rules = [
        rule for rule in RULES_BY_ID.values()
        if rule.id.startswith(SEMANTIC_PREFIXES)
    ]
    summary = []
    for rule in semantic_rules:
        summary.append({
            "rule": rule.id,
            "title": rule.title,
            "currently_blocking": rule.blocking,
            "source": rule.source,
            "findings": per_rule_findings[rule.id],
            "prs": per_rule_prs[rule.id],
            "pr_rate": round(per_rule_prs[rule.id] / args.limit, 4),
            "examples": _pick(occurrences.get(rule.id, []), args.examples_per_rule),
        })

    report = {
        "checker_head": gitio.git(repo, "rev-parse", "HEAD"),
        "sample_size": len(sample),
        "since": args.since,
        "errors": errors,
        "summary": summary,
    }
    (out / "replay.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    (out / "readiness.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("\nsemantic rule adoption cost")
    print("rule       findings  PRs   PR-rate  title")
    for row in sorted(summary, key=lambda x: (-x["prs"], -x["findings"], x["rule"])):
        print(
            f"{row['rule']:<10} {row['findings']:>8} {row['prs']:>4} "
            f"{row['pr_rate'] * 100:>7.1f}%  {row['title']}"
        )
    print(f"\nreplay errors: {errors}/{len(sample)}")
    print("\n=== deterministic examples for manual labeling ===")
    for row in sorted(summary, key=lambda x: (-x["prs"], x["rule"])):
        if not row["examples"]:
            continue
        print(f"\n## {row['rule']} — {row['title']} ({row['findings']} findings / {row['prs']} PRs)")
        for ex in row["examples"]:
            print(f"\nPR #{ex['number']} {ex['title']} :: {ex['path']}:{ex['line']} [{ex['scope']}]")
            print(ex["context"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
