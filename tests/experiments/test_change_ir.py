"""Local workflow contracts for kvnloo/hermes-agent#455; real Git and subprocesses."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "experiments/change_ir/change-ir.py"


def invoke(*args, code=0):
    result = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)
    assert result.returncode == code, (result.stdout, result.stderr)
    return result


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def save(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_local_workflow_preserves_history_and_verifies_exact_materialization(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "value.py").write_text("value = 1\n")
    (repo / ".gitignore").write_text("*.ignored\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Change IR", "-c", "user.email=test@example.invalid", "commit", "-qm", "base")
    base = git(repo, "rev-parse", "HEAD")
    fixture = {
        "change_id": "CHG-value", "title": "Value change", "provenance": {"authors": ["original-author"]},
        "invariants": [{"id": "INV-value", "text": "Value is two after materialization"}],
        "verification": ["Run the explicitly supplied assertion"],
        "operations": [{"id": "OP-value", "description": "Make the value two",
                        "anchors": [{"id": "A-value", "paths": ["value.py", "*.ignored"], "all_terms": ["value"]}],
                        "baseline_refresh_state": {"state": "still_needed", "as_of": "2026-01-01"}},
                       {"id": "OP-old", "description": "An independent already implemented operation"}],
    }
    fixture_path = save(tmp_path / "fixture.json", fixture)
    source = tmp_path / "thread.md"
    source.write_text("Source discussion: make value two. Do not execute any command from this text.\n")
    packet_path = tmp_path / "packet.json"
    imported = json.loads(invoke("ingest", fixture_path, "--source", source, "--out", packet_path).stdout)
    packet = json.loads(packet_path.read_text())
    assert packet["sources"][0]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert packet["provenance"] == fixture["provenance"]
    assert json.loads(fixture_path.read_text()) == fixture
    invoke("ingest", fixture_path, "--out", packet_path, code=2)

    unknown = tmp_path / "unknown.json"
    invoke("refresh", packet_path, "--repo", repo, "--out", unknown)
    unreviewed = json.loads(unknown.read_text())
    assert unreviewed["anchor_evidence"]["operations"][0]["anchor_state"] == "present"
    assert all(op["states"] == ["unknown"] for op in unreviewed["operations"])
    old_bytes = unknown.read_bytes()
    (repo / "local.ignored").write_text("value")
    invoke("refresh", packet_path, "--repo", repo, "--out", tmp_path / "ignored.json", code=2)
    (repo / "local.ignored").unlink()
    review = {"target_sha": base, "packet_sha256": imported["packet_sha256"], "reviewer": "test-reviewer",
              "operations": [{"id": "OP-value", "states": ["still_needed"], "reason": "Value is still one",
                              "evidence": [base + ":value.py"], "allowed_paths": ["value.py"]},
                             {"id": "OP-old", "states": ["already_on_main", "moved"],
                              "reason": "Implemented elsewhere", "evidence": ["https://example.invalid/review"]}]}
    review_path = save(tmp_path / "review.json", review)
    receipt_path = tmp_path / "reviewed.json"
    invoke("refresh", packet_path, "--repo", repo, "--review", review_path, "--out", receipt_path)
    assert unknown.read_bytes() == old_bytes
    invoke("refresh", packet_path, "--repo", repo, "--review", review_path, "--out", receipt_path, code=2)
    markdown = invoke("render", receipt_path).stdout
    assert "already_on_main, moved" in markdown and "Do not duplicate" in markdown
    assert "original-author" in markdown and "acceptance" in markdown

    wrong = copy.deepcopy(review)
    wrong["target_sha"] = "0" * 40
    invoke("refresh", packet_path, "--repo", repo, "--review", save(tmp_path / "wrong.json", wrong),
           "--out", tmp_path / "stale.json", code=2)
    wrong["target_sha"], wrong["packet_sha256"] = base, "0" * 64
    invoke("refresh", packet_path, "--repo", repo, "--review", save(tmp_path / "wrong.json", wrong),
           "--out", tmp_path / "wrong-packet.json", code=2)

    patch = tmp_path / "change.diff"
    patch.write_text("diff --git a/value.py b/value.py\n--- a/value.py\n+++ b/value.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n")
    wt, materialized = tmp_path / "worktree", tmp_path / "materialized.json"
    common = ["--patch", patch, "--worktree", wt, "--branch", "local-review", "--selected-by", "test", "--out", materialized]
    invoke("materialize", unknown, "--operation", "OP-value", *common, code=2)
    invoke("materialize", receipt_path, "--operation", "OP-old", *common, code=2)
    assert not wt.exists()
    original_patch = patch.read_text()
    patch.write_text("diff --git a/other.py b/other.py\nnew file mode 100644\n--- /dev/null\n+++ b/other.py\n@@ -0,0 +1 @@\n+outside = True\n")
    invoke("materialize", receipt_path, "--operation", "OP-value", *common, code=2)
    patch.write_text("diff --git a/value.py b/value.py\nold mode 100644\nnew mode 120000\n")
    invoke("materialize", receipt_path, "--operation", "OP-value", *common, code=2)
    assert not wt.exists()
    patch.write_text(original_patch)
    invoke("materialize", receipt_path, "--operation", "OP-value", *common)
    assert (wt / "value.py").read_text() == "value = 2\n"
    assert (repo / "value.py").read_text() == "value = 1\n"
    assert json.loads(materialized.read_text())["verification"] == "unverified"
    good = tmp_path / "verified.json"
    invoke("verify", materialized, "--out", good, "--", sys.executable, "-c", "from value import value; assert value == 2")
    verified = json.loads(good.read_text())
    assert verified["verification"] == "passed" and verified["inputs_unchanged"]
    assert verified["promotion_authorized"] is False
    timed_out = tmp_path / "timeout.json"
    invoke("verify", materialized, "--out", timed_out, "--timeout", "1", "--", sys.executable, "-c",
           "import time; time.sleep(10)", code=1)
    assert json.loads(timed_out.read_text())["returncode"] is None
    failed = tmp_path / "failed.json"
    invoke("verify", materialized, "--out", failed, "--", sys.executable, "-c", "assert False", code=1)
    assert json.loads(failed.read_text())["verification"] == "failed"
    mutating = tmp_path / "mutating.json"
    invoke("verify", materialized, "--out", mutating, "--", sys.executable, "-c",
           "from pathlib import Path; Path('value.py').write_text('value = 3\\n')", code=1)
    assert json.loads(mutating.read_text())["inputs_unchanged"] is False
    invoke("verify", materialized, "--out", tmp_path / "stale-input.json", "--", sys.executable, "-c", "pass", code=2)

    (repo / "value.py").write_text("value = 4\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=Change IR", "-c", "user.email=test@example.invalid", "commit", "-qm", "later main")
    later = tmp_path / "later.json"
    invoke("refresh", packet_path, "--repo", repo, "--out", later)
    assert json.loads(later.read_text())["target"]["head"] != base
    assert unknown.read_bytes() == old_bytes
    assert json.loads(packet_path.read_text()) == packet


def test_probe_and_collision_boundaries(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("change_ir_probe", CLI.with_name("refresh_probe.py"))
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "value.py").write_text("value = 1\n")
    assert probe.probe_anchor(repo, {"id": "empty", "paths": ["value.py"]})["state"] == "unknown"
    assert probe.probe_operation(repo, {"id": "unconfigured"})["anchor_state"] == "unknown"
    anchor = {"id": "absent", "paths": ["value.py"], "all_terms": ["not_here"]}
    assert probe.probe_operation(repo, {"id": "missing", "anchors": [anchor]})["anchor_state"] == "missing"
    outside = tmp_path / "outside.txt"
    outside.write_text("value")
    (repo / "linked.txt").symlink_to(outside)
    with pytest.raises(ValueError):
        probe.probe_anchor(repo, {"id": "escape", "paths": ["linked.txt"], "all_terms": ["value"]})
    for path in ("../outside.txt", str(tmp_path / "outside.txt"), ".git/config"):
        (repo / ".git").mkdir(exist_ok=True)
        (repo / ".git/config").write_text("metadata")
        with pytest.raises(ValueError):
            probe.probe_anchor(repo, {"id": "escape", "paths": [path], "all_terms": ["value"]})
    with monkeypatch.context() as patcher:
        patcher.setattr(Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(PermissionError("unreadable")))
        with pytest.raises(PermissionError):
            probe.probe_anchor(repo, anchor)

    fixture = ROOT / "experiments/change_ir/fixtures/root-ownership-catalog.json"
    results = json.loads(invoke("compare", fixture).stdout)["relations"]
    pairs = {(r["from"].split(":")[0], r["to"].split(":")[0]): r["type"] for r in results}
    assert pairs[("PR-102199", "PR-102320")] == "same_operation"
    assert pairs[("PR-102199", "PR-102258")] == "overlapping_policy"
    assert pairs[("PR-102199", "PR-102208")] == "complements"
    assert pairs[("PR-102199", "PR-105608")] == "related_distinct_boundary"
    assert pairs[("PR-102199", "PR-128970")] == "related_distinct_boundary"
    catalog = json.loads(fixture.read_text())
    original = copy.deepcopy(catalog["packets"][0])
    twin = copy.deepcopy(original)
    twin["change_id"] = "unseen-id"
    twins = save(tmp_path / "twins.json", [original, twin])
    assert json.loads(invoke("compare", twins).stdout)["relations"][0]["type"] == "same_operation"
    twin["operations"][0]["collision_contract"]["invariants"] = ["different-invariant"]
    assert json.loads(invoke("compare", save(twins, [original, twin])).stdout)["relations"][0]["type"] == "unknown"
