"""Writes the F11 / E30 gate specs and their work-order envelopes (pre-registration: expected verdicts are fixed here)."""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"  # upstream main, fetched 2026-10-01
COMMON = 'issue = "kvnloo/hermes-agent#322"\nai_assistance = "Spec and runner written with Claude Code (Opus 5.5); disclosed per repository policy"\n'

def toml_list(xs):
    return "[" + ", ".join(json.dumps(x) for x in xs) + "]"

SPECS = [
    # id, expected, base, head, merge, files, markers, adjacent, ownership, extra
    dict(id="F11-P1-fork50", expect="KEEP (4 columns PASS)", base=MAIN, head="4d0e03c8a152e5122d158446e1f564b0ec9b6abd", merge=True,
         files=["tests/test_trajectory_compressor.py"], markers=["assert ['over', 'under'] == ['under']"],
         adjacent=["tests/test_trajectory_compressor.py", "tests/test_trajectory_compressor_async.py"],
         ownership=("clear", "2026-09-30", ["save_over_limit"]), refs=["kvnloo/hermes-agent#50"]),
    dict(id="F11-P2-fork112", expect="KEEP (4 columns PASS)", base=MAIN, head="83190e3859755602629b06017891152788e3d728", merge=True,
         files=["tests/tools/test_process_registry.py"],
         markers=["assert ('exited', '', 0) == ('killed', 'process.kill', -15)", "assert ('exited', '', -15) == ('killed', 'kill_all', -15)"],
         adjacent=["tests/tools/test_notify_on_complete.py", "tests/tools/test_kill_verify_tree_death.py", "tests/tools/test_process_registry_list_exit.py"],
         ownership=("clear", "2026-09-30", ["completion_queue stale killed", "kill_all exited completion_reason"]), refs=["kvnloo/hermes-agent#112"]),
    dict(id="F11-P3-fork47v2", expect="KEEP (4 columns PASS)", base=MAIN, head="1d31fe5193e1ee964e611bba6340ab2919c3192c", merge=True,
         files=["tests/agent/test_rate_limit_tracker.py", "tests/agent/test_nous_rate_guard.py"], markers=["assert 100.0 == 0.0", "assert True is False"],
         adjacent=["tests/gateway/test_usage_command.py", "tests/hermes_cli/test_cli_status_bar.py"],
         ownership=("clear", "2026-09-30", ["x-ratelimit-remaining missing", "rate_limit_tracker remaining default"]), refs=["kvnloo/hermes-agent#47"]),
    # Known-bad: the reasoning half of a PR that 658e6c885d reverted as a no-op ("its tests pinned main's existing continuation").
    dict(id="F11-N1-noop-revert", expect="refused at RED (no_repro_on_base)", base="658e6c885d40a2b27a5c3f35bb6276fa5801daf8",
         head="354d499511adc75769cafd9224de8b0ac6ea16ec", merge=False,
         files=["tests/agent/test_length_continuation_thinking_exhaustion.py"], markers=["AssertionError"], adjacent=[],
         ownership=("unknown", None, []), refs=["rework:revert 658e6c885d"]),
    # Known-bad: #123545 head before the review-found transcript-read fix; 8ded06be29's tests fail on it (author: sabotage fails both new tests).
    dict(id="F11-N2-review-fix", expect="refused at GREEN (not_fixed)", base="a7c2df3846f7d6040dd81b7573bd962da546222e",
         head="ac0b07597d767ce8aa3390b60fde1020e3274e72", merge=False, tests_from="8ded06be29cff20f284a474f6e304bda38b84940",
         inject=["tests/tui_gateway/test_submit_row_session_target.py"],
         files=["tests/tui_gateway/test_submit_row_session_target.py"], markers=["AssertionError"], adjacent=[],
         ownership=("unknown", None, []), refs=["rework:review-fix 8ded06be29", "NousResearch/hermes-agent#123545"]),
    # Known-bad: fork #111 head, NEEDS-REWORK (its hunks target code the 6716b72ef2 refactor removed).
    dict(id="F11-N3-fork111-conflict", expect="refused at materialization (BLOCKED, conflicting)", base=MAIN,
         head="df1b7e4ed77d4a519544f5b29b52858b2382e530", merge=True,
         files=["tests/hermes_cli/test_profile_rename_checkpoints.py"], markers=["does not descend from"], adjacent=[],
         ownership=("unknown", None, []), refs=["kvnloo/hermes-agent#111"]),
    # E30-lite positive: a merged upstream fix that adds tests, with author-recorded sabotage.
    dict(id="E30-P1-8ded06be29", expect="4 columns PASS (ownership not applicable -> PARTIAL)", base="ac0b07597d767ce8aa3390b60fde1020e3274e72",
         head="8ded06be29cff20f284a474f6e304bda38b84940", merge=False,
         files=["tests/tui_gateway/test_submit_row_session_target.py"], markers=["AssertionError"],
         adjacent=["tests/tui_gateway/test_submit_row_session_target.py"], ownership=("unknown", None, []), refs=["NousResearch/hermes-agent#123545"]),
    # E30-lite negative: 79dbb1450e (#124792), reverted by 6ca1924763 for shadowing PATH entries; its own tests pin the new behaviour.
    dict(id="E30-N1-79dbb1450e", expect="should be refused; a red/green gate is predicted to miss it (false credit)", base="652fb2eb57de84ea8648bce88b40fce07cad33d6",
         head="79dbb1450ec404a2240529f5554526da4cfec498", merge=False,
         files=["tests/tools/test_mcp_tool_issue_948.py"], markers=["AssertionError"],
         adjacent=["tests/tools/test_mcp_tool_issue_948.py", "tests/tools/test_mcp_bridge_single_failure.py"],
         ownership=("unknown", None, []), refs=["NousResearch/hermes-agent#124792", "revert 6ca1924763"]),
]

for s in SPECS:
    lines = [f'xf_spec = 1\nid = "{s["id"]}"\nrev = 1\nkind = "redgreen"\n{COMMON}origin_refs = {toml_list(s["refs"])}',
             f'expected = {json.dumps(s["expect"])}',
             f'[base]\nrepo = "NousResearch/hermes-agent"\npin = "{s["base"]}"',
             f'[head]\ncommit = "{s["head"]}"\nmerge_onto_base = {"true" if s["merge"] else "false"}']
    if s.get("tests_from") or s.get("inject"):
        lines.append("[inject]" + (f'\ntests_from = "{s["tests_from"]}"' if s.get("tests_from") else "")
                     + (f'\nfiles = {toml_list(s["inject"])}' if s.get("inject") else ""))
    lines.append(f'[probe]\nkind = "pytest"\nfiles = {toml_list(s["files"])}\nreps = 3\njobs = 2\ntimeout_s = 900')
    lines.append(f'[oracle]\nred_markers = {toml_list(s["markers"])}\nsabotage = "per_hunk"\nadjacent = {toml_list(s["adjacent"])}')
    v, at, q = s["ownership"]
    lines.append(f'[ownership]\nverdict = "{v}"' + (f'\nsearched_at = "{at}"' if at else "") + f'\nqueries = {toml_list(q)}')
    lines.append('[outputs]\nnot_tested = ["full test suite", "real provider responses", "kernel network namespace (in-process guard only)"]')
    path = HERE / f'{s["id"]}.toml'
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    wo = {"id": f'xf-{s["id"]}', "kind": "work_order", "project": "hermes-agent", "from": "factory-replay-gate staging builder",
          "to": ["factory"], "status": "claimed", "civ": {"city_id": "oss:hermes-agent"}, "dedupe_key": "frontier:factory-replay-gate",
          "spec": path.name, "spec_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "queue_rank": None,
          "staging": "factory-replay-gate"}
    (HERE / f'{s["id"]}.wo.json').write_text(json.dumps(wo, indent=1) + "\n", encoding="utf-8")
    print(s["id"], wo["spec_sha256"][:12])
