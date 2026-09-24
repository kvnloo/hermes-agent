"""Fork-only verification: main fails, candidate passes, missing wiring fails.

Publishes nothing. The workflow may push the resulting commit to a fresh fork
candidate branch only after this script exits successfully.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

MAIN = "a25cf4d77d46733767b91d5a410e701f4596541e"
PR_HEAD = "eb442593b66a255f7f7789d4bf2e862d861cec61"
PR_BASE = "416a8177c25d87aa9929dfcf31f7964137d7fcdd"
CHANGED = {
    "agent/interrupt_control.py",
    "agent/turn_iteration_prep.py",
    "hermes_cli/cli_agent_setup_mixin.py",
    "hermes_cli/cli_loops_mixin.py",
    "hermes_cli/cli_tui_mixin.py",
    "tests/agent/test_steer.py",
}
NEW_TEST = "tests/hermes_cli/test_steer_observer_wiring.py"
NODE = NEW_TEST + "::test_external_acceptance_is_rendered_by_cli_setup"


def output(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def expect_missing_wiring(label: str, directory: Path) -> dict:
    xml = directory / f"{label}.xml"
    proc = subprocess.run([sys.executable, "-m", "pytest", NODE, "-q", f"--junitxml={xml}"], text=True, capture_output=True)
    print(proc.stdout, flush=True)
    print(proc.stderr, flush=True)
    if not xml.exists():
        raise RuntimeError(f"{label}: no test report; cannot treat setup failure as a regression witness")
    root = ET.parse(xml).getroot()
    cases = root.findall(".//testcase")
    failures = root.findall(".//failure")
    errors = root.findall(".//error")
    if proc.returncode != 1 or len(cases) != 1 or len(failures) != 1 or errors:
        raise RuntimeError(f"{label}: expected one assertion failure, not a collection/runtime error")
    if "accepted external steer must render through _init_agent wiring" not in (failures[0].text or ""):
        raise RuntimeError(f"{label}: failed for a different reason")
    return {"stage": label, "exit_code": proc.returncode, "expected_assertion_failure": True}


def main() -> None:
    harness = Path(sys.argv[1]).resolve()
    receipts = Path(os.environ["RUNNER_TEMP"]) / "steer-receipts"
    receipts.mkdir(exist_ok=True)
    assert output("git", "rev-parse", "HEAD") == MAIN
    assert not output("git", "status", "--porcelain")
    subprocess.run(["git", "fetch", "--depth=1", "origin", PR_HEAD, PR_BASE], check=True)
    changed = set(output("git", "diff", "--name-only", PR_BASE, PR_HEAD).splitlines())
    if changed != CHANGED:
        raise RuntimeError(f"Unexpected original PR footprint: {changed}")
    shutil.copyfile(harness / "test_steer_observer_wiring.py", NEW_TEST)
    baseline = expect_missing_wiring("unchanged-main", receipts)

    patch = subprocess.check_output(["git", "diff", "--binary", PR_BASE, PR_HEAD])
    result = subprocess.run(["git", "apply", "--3way", "-"], input=patch)
    if result.returncode:
        subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], check=True)
        subprocess.run(["git", "diff", "--cc"], check=True)
        raise RuntimeError("Current-main port needs explicit conflict resolution; no branch published")

    setup = Path("hermes_cli/cli_agent_setup_mixin.py")
    content = setup.read_text()
    old = "⏩ Steered: '{preview}'"
    if content.count(old) != 1:
        raise RuntimeError("Acknowledgement-copy anchor changed")
    setup.write_text(content.replace(old, "⏩ Steer queued: '{preview}'"))
    suites = [
        "tests/agent/test_steer.py", "tests/agent/test_interrupt_compat.py",
        "tests/hermes_cli/test_cli_steer_busy_path.py",
        "tests/hermes_cli/test_steer_inline_repaint.py",
        "tests/hermes_cli/test_status_lines_held_during_stream_box.py", NEW_TEST,
    ]
    subprocess.run(["scripts/run_tests.sh", *suites], check=True)
    subprocess.run([sys.executable, "-m", "ruff", "check", NEW_TEST], check=True)
    candidate = setup.read_text()
    wire = "            self.agent._steer_accepted_callback = self._on_steer_accepted\n"
    if candidate.count(wire) != 1:
        raise RuntimeError("Observer-wiring mutation anchor changed")
    try:
        setup.write_text(candidate.replace(wire, ""))
        mutation = expect_missing_wiring("wiring-removed", receipts)
    finally:
        setup.write_text(candidate)
    subprocess.run(["git", "add", "--", *sorted(CHANGED), NEW_TEST], check=True)
    subprocess.run(["git", "diff", "--cached", "--check"], check=True)
    final_changed = set(output("git", "diff", "--cached", "--name-only", MAIN).splitlines())
    if final_changed != CHANGED | {NEW_TEST}:
        raise RuntimeError(f"Unexpected candidate footprint: {final_changed}")
    tree = output("git", "write-tree")
    env = dict(os.environ, GIT_AUTHOR_NAME="Kevin Rajan", GIT_COMMITTER_NAME="Kevin Rajan",
               GIT_AUTHOR_EMAIL="7121943+kvnloo@users.noreply.github.com",
               GIT_COMMITTER_EMAIL="7121943+kvnloo@users.noreply.github.com")
    message = "fix(cli): refresh steer acknowledgement wiring on current main\n\nPreserve the original #112428 implementation and newer interrupt semantics.\nDescribe acceptance as queued, not consumed by the model. Exercise actual\nCLI setup and reject a removed-wiring mutation with the same regression.\n"
    commit = subprocess.check_output(["git", "commit-tree", tree, "-p", PR_HEAD, "-p", MAIN, "-m", message], env=env, text=True).strip()
    receipt = {"main_sha": MAIN, "original_pr_head": PR_HEAD, "candidate_commit": commit,
               "candidate_tree": tree, "tests": suites, "candidate_exit_code": 0,
               "baseline": baseline, "mutation": mutation,
               "limitations": ["No live interactive terminal or upstream CI acceptance.", "Provider construction isolated; no model requests."]}
    (receipts / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (receipts / "candidate.patch").write_bytes(subprocess.check_output(["git", "diff", "--cached", "--binary", MAIN]))
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
        summary.write("```json\n" + json.dumps(receipt, indent=2) + "\n```\n")
    with open(os.environ["GITHUB_OUTPUT"], "a") as summary:
        summary.write(f"candidate={commit}\n")
    print("VERIFIED_CANDIDATE", commit, json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
