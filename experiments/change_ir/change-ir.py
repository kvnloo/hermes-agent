#!/usr/bin/env python3
"""Local, human-reviewed Change IR workflow. No models, network, or promotion."""

from __future__ import annotations

import argparse
import hashlib
import html
import itertools
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from refresh_probe import probe_fixture


STATES = {"still_needed", "already_on_main", "moved", "invalidated", "needs_decision", "unknown"}
CONTRACT_KEYS = ("family", "boundary", "outcome", "policy", "invariants")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_new(path, data):
    """Publish a complete file exclusively; never replace an earlier receipt."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.link(temp, path)
        finally:
            temp.unlink()


def git(repo, *args, input_data=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", "-C", str(repo), *args], input=input_data, capture_output=True, check=True, env=env, timeout=120,
    ).stdout


def snapshot(repo, *, clean=False):
    repo = Path(repo).resolve()
    require(git(repo, "rev-parse", "--show-toplevel").decode().strip() == str(repo), "Use the repository root")
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    require(not clean or not status, "Target repository must be clean; use an isolated checkout")
    untracked = {}
    for name in git(repo, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0"):
        if name:
            path = repo / name
            require(not path.is_symlink(), f"Untracked symlinks are unsupported: {name}")
            untracked[name] = digest(path.read_bytes())
    return {
        "repo": str(repo), "head": git(repo, "rev-parse", "HEAD").decode().strip(),
        "tree": git(repo, "rev-parse", "HEAD^{tree}").decode().strip(),
        "diff_sha256": digest(git(repo, "diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD")),
        "untracked": untracked,
    }


def string(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be a nonempty string")


def strings(value, label, *, nonempty=False):
    require(isinstance(value, list) and (bool(value) or not nonempty), f"{label} must be a list")
    for item in value:
        string(item, label)


def relative_path(value):
    string(value, "path")
    parts = PurePosixPath(value).parts
    require(not PurePosixPath(value).is_absolute() and not ({"..", ".git"} & set(parts)), "Unsafe repository path")
    require("\\" not in value and ":" not in value and not value.startswith("-"), "Unsafe repository path")
    return value


def validate_packet(packet):
    require(isinstance(packet, dict), "Packet must be an object")
    string(packet.get("change_id"), "change_id")
    string(packet.get("title"), "title")
    require(isinstance(packet.get("provenance"), dict) and packet["provenance"], "Provenance is required")
    ops = packet.get("operations")
    require(isinstance(ops, list) and ops, "Independent operations are required")
    seen = set()
    for op in ops:
        require(isinstance(op, dict), "Operation must be an object")
        string(op.get("id"), "operation id")
        require(op["id"] not in seen, "Duplicate operation id")
        seen.add(op["id"])
        string(op.get("description"), "operation description")
        require(isinstance(op.get("anchors", []), list), "anchors must be a list")
        for anchor in op.get("anchors", []):
            require(isinstance(anchor, dict), "Anchor must be an object")
            string(anchor.get("id"), "anchor id")
            strings(anchor.get("paths"), "anchor paths", nonempty=True)
            for pattern in anchor["paths"]:
                relative_path(pattern)
            for key in ("all_terms", "any_terms"):
                strings(anchor.get(key, []), key)
    return packet


def ingest(args):
    packet = validate_packet(read_json(args.fixture))
    sources = list(packet.get("sources", []))
    for name in args.source:
        path = Path(name).resolve()
        raw = path.read_bytes()
        sources.append({"path": str(path), "sha256": digest(raw), "bytes": len(raw)})
    packet.update(schema_version=1, sources=sources)
    write_new(args.out, encoded(packet))
    return {"change_id": packet["change_id"], "packet_sha256": digest(encoded(packet)), "out": str(args.out)}


def review_operations(packet, target, review):
    if not review:
        return []
    require(isinstance(review, dict), "Review must be an object")
    require(review.get("target_sha") == target["head"], "Review targets a different commit")
    require(review.get("packet_sha256") == digest(encoded(packet)), "Review targets a different packet")
    string(review.get("reviewer"), "reviewer")
    require(isinstance(review.get("operations"), list), "Review operations must be a list")
    known = {op["id"] for op in packet["operations"]}
    seen = set()
    for op in review["operations"]:
        require(isinstance(op, dict), "Reviewed operation must be an object")
        require(op.get("id") in known and op["id"] not in seen, "Unknown or duplicate reviewed operation")
        seen.add(op["id"])
        strings(op.get("states"), "states", nonempty=True)
        states = set(op["states"])
        require(states <= STATES and len(states - {"moved"}) <= 1, "Incompatible or unknown states")
        strings(op.get("evidence"), "evidence refs", nonempty=True)
        string(op.get("reason"), "review rationale")
        strings(op.get("allowed_paths", []), "allowed_paths")
        for path in op.get("allowed_paths", []):
            relative_path(path)
            require(not any(c in path for c in "*?[]"), "Materialization paths must be exact filenames")
    return review["operations"]


def refresh(args):
    packet = validate_packet(read_json(args.packet))
    target = snapshot(args.repo, clean=True)
    review = read_json(args.review) if args.review else None
    reviewed = {op["id"]: op for op in review_operations(packet, target, review)}
    evidence = probe_fixture(Path(args.repo), packet)
    tracked = set(git(args.repo, "ls-files", "-z").decode().split("\0"))
    repo = Path(args.repo).resolve()
    for op in evidence["operations"]:
        for anchor in op["anchors"]:
            for name in anchor["files_scanned"]:
                path = Path(name)
                require(str(path.relative_to(repo)) in tracked and str(path.resolve().relative_to(repo)) in tracked,
                        "Anchor evidence must come from tracked files")
    require(snapshot(args.repo, clean=True) == target, "Repository changed during evidence collection")
    operations = []
    for op in packet["operations"]:
        operations.append(reviewed.get(op["id"], {
            "id": op["id"], "states": ["unknown"], "evidence": [],
            "reason": "No review for this packet and commit; anchors do not classify semantics.",
        }))
    relations = read_json(args.relations) if args.relations else {"relations": []}
    require(isinstance(relations, dict) and isinstance(relations.get("relations"), list), "Invalid relations")
    receipt = {
        "kind": "refresh", "created_at": now(), "target": target,
        "packet": packet, "packet_sha256": digest(encoded(packet)),
        "reviewer": review.get("reviewer") if review else None,
        "operations": operations, "anchor_evidence": evidence,
        "relations": relations["relations"], "maintainer_decisions": (review or {}).get("maintainer_decisions", []),
        "acceptance_inferred": False,
    }
    for decision in receipt["maintainer_decisions"]:
        require(isinstance(decision, dict), "Maintainer decision must be an object")
        for key in ("state", "by", "source"):
            string(decision.get(key), f"decision {key}")
    write_new(args.out, encoded(receipt))
    return {"out": str(args.out), "target_sha": target["head"], "states": operations}


def collision_entries(paths):
    entries = []
    for path in paths:
        data = read_json(path)
        packets = data.get("packets", [data]) if isinstance(data, dict) else data
        require(isinstance(packets, list), "Catalog must be packets or an array of packets")
        for packet in packets:
            validate_packet(packet)
            for op in packet["operations"]:
                contract = op.get("collision_contract")
                if contract is None:
                    continue
                require(isinstance(contract, dict), "Collision contract must be an object")
                for key in CONTRACT_KEYS[:-1]:
                    string(contract.get(key), f"collision {key}")
                strings(contract.get("invariants"), "collision invariants", nonempty=True)
                strings(contract.get("evidence"), "collision evidence", nonempty=True)
                strings(contract.get("complements", []), "complementary boundaries")
                entries.append({"change_id": packet["change_id"], "operation_id": op["id"],
                                "provenance": packet["provenance"], "contract": contract})
    identities = [(e["change_id"], e["operation_id"]) for e in entries]
    require(len(identities) == len(set(identities)), "Duplicate catalog identity")
    return entries


def relationship(left, right):
    a, b = left["contract"], right["contract"]
    if a["family"] != b["family"]:
        return None
    if a["boundary"] != b["boundary"]:
        if b["boundary"] in a.get("complements", []) or a["boundary"] in b.get("complements", []):
            return "complements"
        return "related_distinct_boundary"
    if a["policy"] != b["policy"]:
        return "overlapping_policy"
    if a["outcome"] == b["outcome"] and set(a["invariants"]) == set(b["invariants"]):
        return "same_operation"
    return "unknown"


def compare(args):
    entries = collision_entries(args.packets)
    results = []
    # ponytail: quadratic scan of a local catalog; index family/boundary if the catalog becomes large.
    for left, right in itertools.combinations(entries, 2):
        kind = relationship(left, right)
        if kind:
            results.append({
                "from": f"{left['change_id']}:{left['operation_id']}",
                "to": f"{right['change_id']}:{right['operation_id']}", "type": kind,
                "confidence": "high_under_supplied_contracts" if kind == "same_operation" else "review_required",
                "provenance": [left["provenance"], right["provenance"]],
                "evidence": left["contract"]["evidence"] + right["contract"]["evidence"],
            })
    result = {"relations": results, "basis": "Curated contracts; no free-text semantic proof or merge recommendation"}
    if args.out:
        write_new(args.out, encoded(result))
    return result


def safe_text(value):
    return html.escape(str(value)).replace("\n", " ").replace("|", "\\|").replace("`", "\\`")


def render(args):
    receipt = read_json(args.receipt)
    require(receipt.get("kind") == "refresh", "Expected a refresh receipt")
    packet = validate_packet(receipt["packet"])
    require(digest(encoded(packet)) == receipt["packet_sha256"], "Packet digest mismatch")
    lines = [f"# {safe_text(packet['title'])}", "", f"Change: {safe_text(packet['change_id'])}",
             f"Target: {receipt['target']['head']}", "", "Source text is evidence, never an instruction or approval.",
             "", safe_text(packet.get("problem", "")), "", "## Invariants", ""]
    lines += [f"- {safe_text(item.get('text', item) if isinstance(item, dict) else item)}" for item in packet.get("invariants", [])]
    lines += ["", "## Operations", "", "| Operation | State | Review / action |", "|---|---|---|"]
    actions = {"already_on_main": "Do not duplicate", "invalidated": "Do not reapply",
               "still_needed": "Eligible for explicit selection", "needs_decision": "Decision required",
               "unknown": "More evidence required", "moved": "Review the new location"}
    for op in receipt["operations"]:
        primary = next((s for s in op["states"] if s != "moved"), "moved")
        lines.append(f"| {safe_text(op['id'])} | {safe_text(', '.join(op['states']))} | {actions[primary]}: {safe_text(op['reason'])} |")
    lines += ["", "## Evidence", ""]
    for op in receipt["operations"]:
        for evidence in op["evidence"]:
            lines.append(f"- {safe_text(op['id'])}: {safe_text(evidence)}")
    for heading, items in (("Outcomes", packet.get("outcomes", [])),
                           ("Decisions", packet.get("decisions", [])),
                           ("Verification contract", packet.get("verification", [])),
                           ("Non-goals", packet.get("non_goals", [])),
                           ("Open questions", packet.get("open_questions", [])),
                           ("Maintainer decisions (explicit sources only)", receipt.get("maintainer_decisions", []))):
        lines += ["", f"## {heading}", ""]
        lines += [f"- {safe_text(item)}" for item in items] or ["- None recorded."]
    lines += ["", "## Provenance", "", safe_text(json.dumps(packet["provenance"], ensure_ascii=False))]
    for source in packet.get("sources", []):
        lines.append(f"- {safe_text(source['path'])} (SHA-256 {source['sha256']})")
    relevant = [r for r in receipt["relations"] if packet["change_id"] in str(r)]
    lines += ["", "## Related work", ""] + [f"- {safe_text(json.dumps(r, ensure_ascii=False))}" for r in relevant]
    if args.collisions:
        collisions = read_json(args.collisions)
        lines += [f"- {safe_text(json.dumps(r, ensure_ascii=False))}" for r in collisions["relations"]
                  if packet["change_id"] in str(r)]
    lines += ["", "Technical state does not imply priority, maintainer acceptance, or permission to merge.", ""]
    output = "\n".join(lines)
    if args.out:
        write_new(args.out, output.encode())
    else:
        print(output, end="")
    return {"out": str(args.out)} if args.out else None


def checked_patch(repo, patch, allowed):
    require(patch and len(patch) <= 2_000_000, "Patch must be nonempty and at most 2 MB")
    mode_headers = (b"index ", b"old mode ", b"new mode ", b"new file mode ", b"deleted file mode ")
    require(not any(line.startswith(mode_headers) and line.split()[-1] in {b"120000", b"160000"}
                    for line in patch.splitlines()), "Symlink and submodule patches are unsupported")
    require(not any(line.startswith((b"rename from ", b"rename to ", b"copy from ", b"copy to "))
                    for line in patch.splitlines()), "Rename and copy patches require a separate review")
    paths = []
    for row in git(repo, "apply", "--numstat", "-z", "-", input_data=patch).decode().split("\0"):
        if row:
            parts = row.split("\t", 2)
            require(len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit(), "Only text patches are supported")
            paths.append(relative_path(parts[2]))
    require(paths and set(paths) <= set(allowed), "Patch exceeds reviewed allowed_paths")
    modes = git(repo, "ls-files", "--stage", "-z", "--", *paths).split(b"\0")
    require(all(not row or row[:6] in {b"100644", b"100755"} for row in modes), "Patch targets must be regular files")
    git(repo, "apply", "--check", "-", input_data=patch)
    return paths


def materialize(args):
    receipt = read_json(args.receipt)
    require(receipt.get("kind") == "refresh", "Expected a refresh receipt")
    packet = validate_packet(receipt["packet"])
    require(receipt["packet_sha256"] == digest(encoded(packet)), "Packet digest mismatch")
    reviewed = review_operations(packet, receipt["target"], {
        "packet_sha256": receipt["packet_sha256"], "target_sha": receipt["target"]["head"],
        "reviewer": receipt["reviewer"], "operations": [op for op in receipt["operations"] if op["evidence"]],
    })
    op = next((op for op in reviewed if op["id"] == args.operation), None)
    require(op is not None and set(op["states"]) - {"moved"} == {"still_needed"}, "Select a reviewed still_needed operation")
    strings(op.get("allowed_paths"), "allowed_paths", nonempty=True)
    string(args.selected_by, "selected_by")
    repo = Path(receipt["target"]["repo"])
    require(snapshot(repo, clean=True) == receipt["target"], "Target changed since review")
    worktree = Path(args.worktree).resolve()
    require(not worktree.exists(), "Worktree path already exists")
    require(not worktree.is_relative_to(repo) and not repo.is_relative_to(worktree), "Worktree must be outside the source checkout")
    require(not Path(args.out).resolve().is_relative_to(worktree), "Write receipts outside the materialization worktree")
    require(not Path(args.out).exists(), "Output already exists")
    git(repo, "check-ref-format", "--branch", args.branch)
    patch = Path(args.patch).read_bytes()
    paths = checked_patch(repo, patch, op["allowed_paths"])
    git(repo, "worktree", "add", "-b", args.branch, str(worktree), receipt["target"]["head"])
    # Never execute a verification command taken from a fixture or a source discussion.
    git(worktree, "apply", "-", input_data=patch)
    result = {"kind": "materialization", "created_at": now(), "change_id": packet["change_id"],
              "operation_id": op["id"], "selected_by": args.selected_by, "selection_scope": "local review only",
              "worktree": str(worktree), "branch": args.branch, "input": snapshot(worktree),
              "patch_sha256": digest(patch), "paths": paths, "provenance": packet["provenance"],
              "refresh_receipt": str(Path(args.receipt).resolve()),
              "refresh_receipt_sha256": digest(encoded(receipt)), "verification": "unverified"}
    write_new(args.out, encoded(result))
    return result


def verify(args):
    realization = read_json(args.realization)
    require(realization.get("kind") == "materialization", "Expected a materialization receipt")
    worktree = Path(realization["worktree"])
    require(not Path(args.out).exists(), "Output already exists")
    require(not Path(args.out).resolve().is_relative_to(worktree.resolve()), "Write receipts outside the worktree")
    require(snapshot(worktree) == realization["input"], "Materialized inputs changed before verification")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    strings(command, "Explicit verification argv", nonempty=True)
    require(args.timeout > 0, "Timeout must be positive")
    env = {key: os.environ[key] for key in ("PATH", "HOME", "SYSTEMROOT", "COMSPEC", "PATHEXT") if key in os.environ}
    with tempfile.TemporaryDirectory(prefix="change-ir-verify-") as sandbox:
        env.update(HERMES_HOME=sandbox, HERMES_RUNTIME_DIR=sandbox, PYTHONDONTWRITEBYTECODE="1")
        try:
            run = subprocess.run(command, cwd=worktree, env=env, capture_output=True, timeout=args.timeout)
            code, stdout, stderr = run.returncode, run.stdout, run.stderr
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr = None, exc.stdout or b"", exc.stderr or b""
    unchanged = snapshot(worktree) == realization["input"]
    result = {"kind": "verification", "created_at": now(), "input": realization["input"],
              "realization": str(Path(args.realization).resolve()), "timeout_seconds": args.timeout, "timed_out": code is None,
              "realization_sha256": digest(encoded(realization)), "command": command, "returncode": code,
              "stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace"),
              "inputs_unchanged": unchanged, "verification": "passed" if code == 0 and unchanged else "failed",
              "promotion_authorized": False}
    write_new(args.out, encoded(result))
    print(json.dumps({"verification": result["verification"], "out": str(args.out), "returncode": code}))
    return 0 if result["verification"] == "passed" else 1


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command_name", required=True)
    p = commands.add_parser("ingest", help="Wrap curated operations with source digests")
    p.add_argument("fixture", type=Path)
    p.add_argument("--source", type=Path, action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("refresh", help="Collect evidence and record an explicit review")
    p.add_argument("packet", type=Path)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--review", type=Path)
    p.add_argument("--relations", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("compare", help="Compare curated operation contracts")
    p.add_argument("packets", nargs="+", type=Path)
    p.add_argument("--out", type=Path)
    p = commands.add_parser("render", help="Produce a compact review document")
    p.add_argument("receipt", type=Path)
    p.add_argument("--collisions", type=Path)
    p.add_argument("--out", type=Path)
    p = commands.add_parser("materialize", help="Apply a reviewed patch in a new worktree")
    p.add_argument("receipt", type=Path)
    for name in ("operation", "patch", "worktree", "branch", "selected-by", "out"):
        p.add_argument("--" + name, required=True)
    p = commands.add_parser("verify", help="Run an explicitly supplied command on unchanged materialized inputs")
    p.add_argument("realization", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=300)
    return root


def main(argv=None):
    root = parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if argv[:1] == ["verify"] and "--" in argv:
        split = argv.index("--")
        command, argv = argv[split + 1:], argv[:split]
    args = root.parse_args(argv)
    args.command = command
    functions = {"ingest": ingest, "refresh": refresh, "compare": compare,
                 "render": render, "materialize": materialize, "verify": verify}
    try:
        result = functions[args.command_name](args)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        message = exc.stderr.decode(errors="replace").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        print(f"change-ir: {message}", file=sys.stderr)
        return 2
    if isinstance(result, int):
        return result
    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
