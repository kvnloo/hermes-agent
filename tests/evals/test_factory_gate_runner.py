"""Behaviour contract for the downstream promotion-gate runner (evals/_factory/gate_runner.py)."""

import hashlib
import json
import subprocess
import sys

import pytest

if sys.platform == "win32":
    pytest.skip("the gate runner is POSIX-only", allow_module_level=True)

from evals._factory import gate_runner as gr  # noqa: E402

CONTRACT = "import calc\nassert calc.add(2, 2) == 4, 'add(2, 2) must be 4'\nprint('CALC_OK')\n"


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def _commit(repo, files, message):
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", message)
    return _git(repo, "rev-parse", "HEAD")


def _work_order(tmp_path, name, base, head, tests_from=None, sabotage=None, reps=2):
    spec = tmp_path / f"{name}.toml"
    inject = f'[inject]\ntests_from = "{tests_from}"\n' if tests_from else ""
    recorded = ""
    if sabotage:  # a recorded sabotage patch, named relative to the spec
        sha = hashlib.sha256((tmp_path / sabotage).read_bytes()).hexdigest()
        recorded = f'sabotage = "{sabotage}"\nsabotage_sha256 = "{sha}"\n'
    spec.write_text(
        f'xf_spec = 1\nid = "{name}"\nkind = "redgreen"\n[base]\npin = "{base}"\n[head]\ncommit = "{head}"\n{inject}'
        f'[probe]\nkind = "script"\nfiles = ["tests/test_calc.py"]\nreps = {json.dumps(reps)}\ntimeout_s = 60\n'
        '[oracle]\nred_markers = ["add(2, 2) must be 4"]\ngreen_markers = ["CALC_OK"]\nadjacent = ["tests/test_adjacent.py"]\n'
        f'{recorded}[ownership]\nverdict = "clear"\n',
        encoding="utf-8",
    )
    order = {"id": f"wo-{name}", "kind": "work_order", "project": "hermes-agent", "from": "owner", "to": ["factory"],
             "status": "claimed", "civ": {"city_id": "oss:hermes-agent"}, "spec": spec.name,
             "spec_sha256": hashlib.sha256(spec.read_bytes()).hexdigest()}
    path = tmp_path / f"{name}.wo.json"
    path.write_text(json.dumps(order), encoding="utf-8")
    return path


def test_gate_keeps_a_pinned_fix_and_refuses_known_bad_candidates(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    base = _commit(repo, {"calc.py": "def add(a, b):\n    return a - b\n", "version.py": "VERSION = 1\n",
                          "tests/test_adjacent.py": "import calc\nassert callable(calc.add)\n"}, "base")
    fix = _commit(repo, {"calc.py": "def add(a, b):\n    return a + b\n", "version.py": "VERSION = 2\n",
                         "tests/test_calc.py": CONTRACT}, "fix add, bump version")
    _git(repo, "checkout", "-q", "-b", "already-fixed", base)
    fixed_base = _commit(repo, {"calc.py": "def add(a, b):\n    return a + b\n"}, "add was fixed elsewhere")
    late = _commit(repo, {"version.py": "VERSION = 2\n", "tests/test_calc.py": CONTRACT}, "test only")
    _git(repo, "checkout", "-q", "-b", "review", base)
    partial = _commit(repo, {"calc.py": "def add(a, b):\n    return 2 * a\n", "tests/test_calc.py": CONTRACT}, "first cut")
    reviewed = _commit(repo, {"calc.py": "def add(a, b):\n    return a + b\n",
                              "tests/test_calc.py": CONTRACT + "assert calc.add(2, 3) == 5, 'add(2, 3) must be 5'\n"}, "review fix")

    keep = gr.run_gate(_work_order(tmp_path, "good", base, fix), repo, tmp_path / "runs", sys.executable)

    assert keep["verdict"] == "KEEP", keep["refusal_reasons"]
    assert {g: keep["gates"][g]["result"] for g in gr.FOUR_COLUMNS} == dict.fromkeys(gr.FOUR_COLUMNS, "PASS")
    assert keep["gates"]["red"]["reps_agree"] == "2/2"
    reverted = {h["hunk"].split(" ")[0]: h["red_again"] for h in keep["gates"]["sabotage"]["per_hunk"]}
    assert reverted == {"calc.py": True, "version.py": False}  # the bump is surface the test does not pin
    assert keep["outcome"]["verified_success"] is None
    assert keep["safety"]["hermes_home_isolated"] and keep["safety"]["canary"]["passed"]
    assert gr.validate_receipt(keep) == []
    assert gr.validate_receipt({**keep, "limitations": ["see /srv/run/arms/head"]}) == ["receipt contains an absolute local path"]

    (tmp_path / "break-add.patch").write_text(_git(repo, "diff", fix, base, "--", "calc.py") + "\n", encoding="utf-8")
    recorded = gr.run_gate(_work_order(tmp_path, "recorded", base, fix, sabotage="break-add.patch"), repo,
                           tmp_path / "runs", sys.executable)

    assert recorded["verdict"] == "KEEP", recorded["refusal_reasons"]
    assert recorded["gates"]["sabotage"]["per_hunk"] == [{"hunk": "break-add.patch", "red_again": True}]

    stale = gr.run_gate(_work_order(tmp_path, "late", fixed_base, late), repo, tmp_path / "runs", sys.executable)

    assert stale["verdict"] == "DISCARD" and stale["refused"]
    assert stale["gates"]["red"] == {"result": "FAIL", "reps_agree": "0/2", "reason": "no_repro_on_base"}
    assert gr.validate_receipt(stale) == []

    # A first cut graded on the reviewer's later tests: head gets them too, so it cannot pass on its own weaker test.
    first_cut = gr.run_gate(_work_order(tmp_path, "first-cut", base, partial, tests_from=reviewed), repo,
                            tmp_path / "runs", sys.executable)

    assert first_cut["verdict"] == "DISCARD"
    assert first_cut["gates"]["red"]["result"] == "PASS"
    assert first_cut["gates"]["green"] == {"result": "FAIL", "reps_agree": "0/2", "reason": "not_fixed"}


RELAY_RUNTIME = (  # head code run by the Relay pin probe: it swallows the guard's refusal, so only the guard log shows it
    "import os, socket, types\nRUNTIME_SCHEMA_VERSION = 'toy.v1'\n\n\ndef resolve_plugin_sources():\n"
    "    try:\n        socket.getaddrinfo('relay.example', 443)\n    except OSError:\n        pass\n"
    "    return types.SimpleNamespace(config_paths=[os.path.join(os.getcwd(), 'plugins.toml'), '/opt/relay/system.toml',\n"
    "                                               os.path.join(os.environ['HERMES_HOME'], 'relay.toml')])\n"
)


def test_a_blocked_attempt_in_the_relay_pin_cell_taints_the_run(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    base = _commit(repo, {"calc.py": "def add(a, b):\n    return a - b\n",
                          "tests/test_adjacent.py": "import calc\nassert callable(calc.add)\n"}, "base")
    head = _commit(repo, {"calc.py": "def add(a, b):\n    return a + b\n", "tests/test_calc.py": CONTRACT,
                          "nemo_relay.py": "", "agent/__init__.py": "", "agent/relay_runtime.py": RELAY_RUNTIME}, "fix add")

    tainted = gr.run_gate(_work_order(tmp_path, "pin", base, head), repo, tmp_path / "runs", sys.executable)

    assert {g: tainted["gates"][g]["result"] for g in gr.FOUR_COLUMNS} == dict.fromkeys(gr.FOUR_COLUMNS, "PASS")
    assert tainted["verdict"] == "INFRA" and tainted["refusal_reasons"] == ["infra cells: relay-pin"]
    assert tainted["safety"]["egress_blocked"] == 1 and tainted["denominators"]["infra"] == 1
    assert tainted["env"]["relay"]["config_paths"] == ["./plugins.toml", "<abs>/system.toml", "$HERMES_HOME/relay.toml"]
    assert gr.validate_receipt(tainted) == []


def test_cell_guard_blocks_egress_live_home_and_hermes_exec_but_allows_loopback(tmp_path):
    run = gr.new_run(tmp_path / "runs", "guard", sys.executable)

    canary = gr.canary(run)

    assert canary["passed"], canary["checks"]
    probe = tmp_path / "egress.py"
    probe.write_text(
        "import socket, sys\nsrv = socket.socket(); srv.bind(('0.0.0.0', 0)); srv.listen(1)\n"
        "s = socket.socket(); s.settimeout(1)\n"
        "try:\n    s.connect((sys.argv[1], srv.getsockname()[1])); print('CONNECTED')\n"
        "except OSError as exc:\n    print('REFUSED', exc)\n",
        encoding="utf-8",
    )
    cell = gr.run_cell(run, "egress", [sys.executable, str(probe), gr._local_nonloopback_ip()], tmp_path)
    assert "REFUSED" in cell["output"] and "factory guard" in cell["output"]
    assert cell["infra"] and [b["event"] for b in cell["blocked"]] == ["socket.connect"]

    # A shell string names hermes too: shell=True must not slip past the argv check.
    shell = gr.run_cell(run, "shell-exec", [sys.executable, "-c", "import subprocess, sys\ntry:\n"
                                            "    subprocess.run(sys.argv[1] + ' update', shell=True)\n"
                                            "except PermissionError as exc:\n    print(exc)\n", str(run.decoy_hermes)], tmp_path)
    assert not (run.decoy_hermes.parent / "EXECUTED").exists(), "the decoy hermes ran"
    assert shell["infra"] and [b["event"] for b in shell["blocked"]] == ["subprocess.Popen"]


@pytest.mark.parametrize("reps", [0, -1, False, True, 0.5, "2"])
def test_gate_refuses_invalid_repetitions_before_running_cells(tmp_path, reps):
    # The existing field is a count, never a truth value or coercible string.
    # Full SHAs satisfy the unrelated checks; invalid specs must stop before Git.
    order = _work_order(tmp_path, "invalid-reps", "1" * 40, "2" * 40, reps=reps)
    scratch = tmp_path / "runs"
    with pytest.raises(gr.Refused, match="probe.reps must be a positive integer"):
        gr.run_gate(order, tmp_path / "repo-not-needed", scratch, sys.executable)
    assert not scratch.exists(), "invalid counts must not create or run probe cells"


@pytest.mark.parametrize("reps", [1, 2, None])
def test_positive_and_default_repetitions_preserve_valid_receipts(tmp_path, reps):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    base = _commit(repo, {"calc.py": "def add(a, b):\n    return a - b\n",
                          "tests/test_adjacent.py": "import calc\nassert callable(calc.add)\n"}, "base")
    head = _commit(repo, {"calc.py": "def add(a, b):\n    return a + b\n",
                          "tests/test_calc.py": CONTRACT}, "fix")
    order = _work_order(tmp_path, "valid-reps", base, head, reps=reps or 2)
    if reps is None:
        work_order = json.loads(order.read_text())
        spec = order.parent / work_order["spec"]
        spec.write_text(spec.read_text().replace("reps = 2\n", ""))
        work_order["spec_sha256"] = hashlib.sha256(spec.read_bytes()).hexdigest()
        order.write_text(json.dumps(work_order))
    receipt = gr.run_gate(order, repo, tmp_path / "runs", sys.executable)
    count = 3 if reps is None else reps
    assert receipt["verdict"] == "KEEP"
    for name in ("red", "green"):
        assert receipt["gates"][name]["reps_agree"] == f"{count}/{count}"
    assert gr.validate_receipt(receipt) == []

    # Reuse an actually generated valid receipt to test its consumer boundary.
    # No extra probe execution or new receipt schema is needed for corruptions.
    import copy
    for gate in ("red", "green"):
        for agreement in ("0/0", "1/2", "", None, True, "garbled"):
            damaged = copy.deepcopy(receipt)
            damaged["gates"][gate]["reps_agree"] = agreement
            assert gr.validate_receipt(damaged), (gate, agreement)
        observations = [m for m in receipt["measurements"] if m["name"].startswith(gate + "-")]
        mutations = {
            "missing": lambda rows, item: rows.remove(item),
            "duplicate": lambda rows, item: rows.append(copy.deepcopy(item)),
            "bool": lambda rows, item: item.update(value=bool(item["value"])),
            "wrong_exit": lambda rows, item: item.update(value=0 if gate == "red" else 1),
            "modeled": lambda rows, item: item.update(label="MODELED"),
            "bad_index": lambda rows, item: item.update(name=gate + "-999_exit"),
            "noninteger": lambda rows, item: item.update(value="0"),
            "malformed_label": lambda rows, item: item.update(label=[]),
        }
        for mutation, apply in mutations.items():
            damaged = copy.deepcopy(receipt)
            observation = next(m for m in damaged["measurements"] if m["name"] == observations[0]["name"])
            apply(damaged["measurements"], observation)
            assert gr.validate_receipt(damaged), (gate, mutation)
    for mutation in ("missing", "duplicate", "contradictory"):
        damaged = copy.deepcopy(receipt)
        headline = next(m for m in damaged["measurements"] if m["name"] == "red_reps_failing_with_marker")
        if mutation == "missing":
            damaged["measurements"].remove(headline)
        elif mutation == "duplicate":
            damaged["measurements"].append(copy.deepcopy(headline))
        else:
            headline["value"] = "0/0"
        assert gr.validate_receipt(damaged), mutation
    for malformed in ([None], "not a list"):
        damaged = copy.deepcopy(receipt)
        damaged["measurements"] = malformed
        assert gr.validate_receipt(damaged)
    for verdict in ("DISCARD", "PARTIAL", "INFRA", "BLOCKED", "FLAKY"):
        other = copy.deepcopy(receipt)
        other["verdict"] = verdict
        other["gates"]["red"]["reps_agree"] = "0/0"
        other["gates"]["green"]["reps_agree"] = "0/0"
        assert gr.validate_receipt(other) == [], verdict
