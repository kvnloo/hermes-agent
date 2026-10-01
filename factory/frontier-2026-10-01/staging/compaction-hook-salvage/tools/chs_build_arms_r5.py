#!/usr/bin/env python3
"""Build the r5 arms for staging/compaction-hook-salvage (factory-only, stdlib).

usage: chs_build_arms_r5.py <worktree> <staging_commit> <foldin_commit>

r5 (round-3 fix): the fold-in moves both dispatches into a sibling (agent/conversation_compression_observer.py),
routes #53806's start-side call through hermes_cli.lifecycle, delivers on_compression_complete only after the
attempt's commit fence and lease are released (the #118120 hazard; same delivery point as #127058), and bounds it
under plugins.hook_callback_timeout.

Every mutated arm is the fold-in commit with ONE textual mutation (pinned at
refs/xf/arms/compaction-hook-salvage/<arm>-r5). Carrier arms re-apply their r4 patch (a diff against the r4
staging commit) onto the r5 staging commit with `git apply -3`; r4-offer is the round-2 combined diff
(patches/arm-c53806-foldin.patch) re-applied the same way, as the real-world in-fence control. foldin-x127058
merges NousResearch/hermes-agent#127058's head into the fold-in and resolves the single conflict by keeping both
post-fence deliveries. Prints arm=commit lines for chs_ab_runner_r5.py --arms.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
REF = "refs/xf/arms/compaction-hook-salvage/"
CC = "agent/conversation_compression.py"
OB = "agent/conversation_compression_observer.py"
PL = "hermes_cli/plugins.py"
PD = "hermes_cli/plugins_dispatch.py"
HK = "hermes_cli/hooks.py"
DOC = "website/docs/user-guide/features/hooks.md"

STAGE = '''        from agent.conversation_compression_observer import stage_compression_complete

        _compression_complete = stage_compression_complete(
            agent, commit, deferred=defer_context_engine_notification, tokens_before=approx_tokens,
            tokens_after=_compressed_est,
        )
'''
FINALLY = '''            if _compression_complete is not None:
                _compression_complete()
'''
START_CALL = '''        from agent.conversation_compression_observer import notify_compression_start

        notify_compression_start(
            agent, messages, task_id=task_id, approx_tokens=approx_tokens, focus_topic=focus_topic, force=force,
        )
'''
START_FN_HEAD = "def notify_compression_start("
START_VALID = '''    # Fired immediately before context compression drops/summarizes older
    # turns. Observer-only: return values are ignored. Plugins can persist
    # task-state or handoff breadcrumbs without mutating the live message list.
    "pre_context_compression",
'''
VALID_ENTRY_TAIL = '''    # estimate), platform. Observer; returns ignored; fail-open; bounded by hook_callback_timeout.
    "on_compression_complete",
'''
PREFIRE = '''        new_system_prompt = _rebuild_system_prompt_at_boundary(agent, system_message)
        # NEGATIVE CONTROL: the observer fires BEFORE the durable commit.
        from agent.conversation_compression_observer import _invoke_compression_complete
        _invoke_compression_complete({
            "session_id": agent.session_id or "", "old_session_id": agent.session_id or "", "in_place": in_place,
            "tokens_before": approx_tokens,
            "tokens_after": estimate_request_tokens_rough(compressed, system_prompt=new_system_prompt or ""),
            "platform": getattr(agent, "platform", None) or "cli",
        })
        commit = _commit_compaction(
'''


def _sub(path, old, new, count=1):
    def apply(text):
        assert text.count(old) == count, f"{path}: anchor found {text.count(old)}x, expected {count}"
        return text.replace(old, new)
    return (path, apply)


def _drop_function(path, head):
    """Remove a top-level function (from its ``def`` line to the next top-level ``def``)."""
    def apply(text):
        start = text.index(head)
        nxt = text.index("\ndef ", start + 1)
        return text[:start] + text[nxt + 1:]
    return (path, apply)


MUTATIONS = {
    # Negative controls
    "neg-prefire": [
        _sub(CC, STAGE, ""),
        _sub(CC, "        new_system_prompt = _rebuild_system_prompt_at_boundary(agent, system_message)\n"
                 "        commit = _commit_compaction(\n", PREFIRE),
    ],
    "neg-infence": [_sub(CC, STAGE, STAGE + '''        # NEGATIVE CONTROL: run it here, inside the commit fence and with the lease held.
        if _compression_complete is not None:
            _compression_complete()
            _compression_complete = None
''')],
    "neg-nodefer": [_sub(OB, "    if not deferred:\n        return lambda", "    if True:  # NEGATIVE CONTROL: deferral bypassed\n        return lambda")],
    # Per-hunk sabotage of the fold-in
    "sab-h1-stage-call": [_sub(CC, STAGE, "")],
    "sab-h2-finally-call": [_sub(CC, FINALLY, "")],
    "sab-h3-tokens-before": [_sub(CC, "deferred=defer_context_engine_notification, tokens_before=approx_tokens,",
                                  "deferred=defer_context_engine_notification, tokens_before=None,")],
    "sab-h4-tokens-after": [_sub(CC, "            tokens_after=_compressed_est,\n        )\n",
                                 "            tokens_after=None,\n        )\n")],
    "sab-h5-valid-hooks": [_sub(PL, VALID_ENTRY_TAIL, "")],
    "sab-h6-bounded": [_sub(PD, '''    "on_compression_complete",
}''', "}")],
    "sab-h7-payload-and-docs": [
        _sub(HK, '''    "on_compression_complete": {
        "session_id": "test-session-2", "old_session_id": "test-session", "in_place": False,
        "tokens_before": 120000, "tokens_after": 30000, "platform": "cli",
    },
''', ""),
        (DOC, lambda t: "".join(l for l in t.splitlines(True) if not l.startswith("| `on_compression_complete` |"))),
    ],
    "sab-h8-start-call": [_sub(CC, START_CALL, "")],
    "sab-h9-deferred-chain": [_sub(OB, '''        setattr(agent, _PENDING_CONTEXT_ENGINE_NOTIFICATION, _notify_then_observe)
''', "        pass  # SABOTAGE: deferred call never chained\n")],
    # Variant: the fold-in without #53806's start-side hook and its task_id plumbing
    "foldin-ref": [
        _sub(CC, START_CALL, ""), _sub(PL, START_VALID, ""),
        _sub(CC, "    attempt: _Attempt, task_id: str,\n) -> _SummaryPhase:", "    attempt: _Attempt,\n) -> _SummaryPhase:"),
        _sub(CC, "system_message=system_message, attempt=attempt,\n        task_id=task_id,\n    )",
             "system_message=system_message, attempt=attempt,\n    )"),
        _drop_function(OB, START_FN_HEAD),
    ],
}

R4_PATCHES = {  # r4 arm diffs against the r4 staging commit 111f361fb0, re-applied onto the r5 staging commit
    "c53806-handport": "arm-c53806-handport.patch",
    "c93391-code": "arm-c93391-code.patch",
    "c118847-handport": "arm-c118847-handport.patch",
    "c125881-merge": "arm-c125881-merge.patch",
    "r4-offer": "arm-c53806-foldin.patch",
}
PR127058 = "refs/xf/pr/127058"


def git(wt, *args, check=True, input_text=None):
    p = subprocess.run(["git", *args], cwd=wt, capture_output=True, text=True, input=input_text)
    if check and p.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {p.stdout}{p.stderr}")
    return p.stdout.strip()


def commit(wt, msg, author=("Kevin Rajan", "7121943+kvnloo@users.noreply.github.com")):
    git(wt, "add", "-A")
    git(wt, "-c", f"user.name={author[0]}", "-c", f"user.email={author[1]}", "commit", "-q", "-m", msg)
    return git(wt, "rev-parse", "HEAD")


def main() -> int:
    wt, staging, foldin = sys.argv[1:4]
    wt = Path(wt)
    out = {}
    for arm, muts in MUTATIONS.items():
        git(wt, "checkout", "-q", "--detach", foldin)
        for path, fn in muts:
            f = wt / path
            f.write_text(fn(f.read_text(encoding="utf-8")), encoding="utf-8")
        sha = commit(wt, f"arm {arm}-r5 (factory-only mutation of foldin-r5)")
        git(wt, "update-ref", REF + arm + "-r5", sha)
        out[arm] = sha
    for arm, patch in R4_PATCHES.items():
        git(wt, "checkout", "-q", "--detach", staging)
        diff = (ST / "patches" / patch).read_text(encoding="utf-8")
        p = subprocess.run(["git", "apply", "-3", "--index"], cwd=wt, input=diff, capture_output=True, text=True)
        if p.returncode != 0:
            print(f"# {arm}: apply -3 failed: {p.stderr.strip()[:400]}", file=sys.stderr)
            git(wt, "reset", "-q", "--hard")
            continue
        sha = commit(wt, f"arm {arm}-r5 (r4 arm diff re-applied onto the r5 staging commit)")
        git(wt, "update-ref", REF + arm + "-r5", sha)
        out[arm] = sha
    # foldin-x127058: the fold-in merged with #127058's head; the one conflict keeps both post-fence deliveries.
    git(wt, "checkout", "-q", "--detach", foldin)
    p = subprocess.run(["git", "-c", "user.name=Kevin Rajan", "-c", "user.email=7121943+kvnloo@users.noreply.github.com",
                        "merge", "--no-ff", "--no-commit", PR127058], cwd=wt, capture_output=True, text=True)
    conflicted = git(wt, "diff", "--name-only", "--diff-filter=U", check=False).split()
    f = wt / CC
    text = f.read_text(encoding="utf-8")
    start, mid, end = text.find("<<<<<<< "), text.find("\n=======\n"), text.find("\n>>>>>>> ")
    if conflicted:
        assert conflicted == [CC] and text.count("<<<<<<< ") == 1, conflicted
        ours = text[text.index("\n", start) + 1:text.find("\n||||||| ", start) if "\n||||||| " in text[start:mid] else mid]
        theirs = text[mid + len("\n=======\n"):end]
        resolved = theirs + "\n" + ours + "\n"
        text = text[:start] + resolved + text[text.index("\n", end + 1) + 1:]
        f.write_text(text, encoding="utf-8")
    sha = commit(wt, "arm foldin-x127058-r5 (factory-only: foldin-r5 merged with #127058 head f306319fe7; "
                     f"conflicts resolved by keeping both post-fence deliveries: {conflicted})")
    git(wt, "update-ref", REF + "foldin-x127058-r5", sha)
    out["foldin-x127058"] = sha
    for arm, sha in out.items():
        print(f"{arm}={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
