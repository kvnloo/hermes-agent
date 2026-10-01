#!/usr/bin/env python3
"""Build the r4 arms for staging/compaction-hook-salvage (factory-only, stdlib).

usage: chs_build_arms_r4.py <worktree> <staging_commit> <foldin_commit>

r4 (round-2 fix): the carrier hand-port passes task_id into _run_summary_phase, so the start-side
pre_context_compression payload is #53806's (task_id included); foldin-ref removes that plumbing with the hook.

Every mutated arm is the fold-in commit (carrier hand-port + fold-in, on the staging commit) with ONE
textual mutation applied, committed and pinned at refs/xf/arms/compaction-hook-salvage/<arm>-r4.
Competitor arms re-apply their r1 diff (old staging commit b3b8d73999 -> arm) onto the new staging
commit with `git apply -3`. Prints arm=commit lines for chs_ab_runner.py --arms.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REF = "refs/xf/arms/compaction-hook-salvage/"
CC = "agent/conversation_compression.py"
PL = "hermes_cli/plugins.py"
PD = "hermes_cli/plugins_dispatch.py"
HK = "hermes_cli/hooks.py"
DOC = "website/docs/user-guide/features/hooks.md"

OBSERVER_CALL = '''    with _swallow('on_compression_complete plugin hook failed', exc_info=True):
        from hermes_cli.lifecycle import has_hook, invoke_hook
        if has_hook("on_compression_complete"):
            invoke_hook(
                "on_compression_complete", session_id=new_session_id, old_session_id=old_session_id,
                in_place=new_session_id == old_session_id, tokens_before=tokens_before, tokens_after=tokens_after,
                platform=getattr(agent, "platform", None) or "cli",
            )
'''
VALID_HOOKS_ENTRY = '''    # on_compression_complete: once per local compaction, AFTER the compacted transcript is durable
    # (agent/conversation_compression.py; a manual /compress waits for its host's commit). Never for
    # an attempt that did not commit, nor for native/Codex server-side compaction. Kwargs: session_id
    # (current), old_session_id (same id when in_place), in_place, tokens_before (caller estimate or
    # None), tokens_after (rough estimate), platform. Observer; returns ignored; fail-open.
    "on_compression_complete",
'''
START_HOOK = '''        # Notify generic plugins before compression discards/summarizes older turns.
        # Observer-only: return values are ignored. Plugins can persist task-state,
        # handoff breadcrumbs, or external-memory snapshots without mutating the
        # live conversation or breaking prompt caching.
        try:
            from hermes_cli.plugins import invoke_hook as _invoke_hook
            _invoke_hook(
                "pre_context_compression",
                session_id=agent.session_id or "",
                task_id=task_id,
                conversation_history=list(messages),
                approx_tokens=approx_tokens,
                focus_topic=focus_topic,
                force=force,
                model=getattr(agent, "model", ""),
                platform=getattr(agent, "platform", None) or "cli",
                conversation_id=getattr(agent, "_gateway_session_key", None),
            )
        except Exception as _plugin_err:
            logger.debug("plugin pre_context_compression failed: %s", _plugin_err)
'''
START_HOOK_VALID = '''    # Fired immediately before context compression drops/summarizes older
    # turns. Observer-only: return values are ignored. Plugins can persist
    # task-state or handoff breadcrumbs without mutating the live message list.
    "pre_context_compression",
'''
CARRIER_POST_COMMIT = '''
        # Notify generic plugins of the same compaction boundary.  A plugin can use
        # this to mark a task-state record replayable for the next turn/session, and
        # then return that state through the existing pre_llm_call context-injection
        # contract. Return values are ignored here to keep compression cache-safe.
        try:
            from hermes_cli.plugins import invoke_hook as _invoke_hook
            _invoke_hook(
                "on_session_start",
                session_id=agent.session_id or "",
                boundary_reason="compression",
                old_session_id=_boundary_parent,
                platform=getattr(agent, "platform", None) or "cli",
                model=getattr(agent, "model", ""),
                context_length=getattr(agent.context_compressor, "context_length", None),
                conversation_id=getattr(agent, "_gateway_session_key", None),
            )
        except Exception as _plugin_err:
            logger.debug("plugin on_session_start (compression): %s", _plugin_err)
'''
NOTIFY_CALL = '''        notify(
            agent, new_session_id=agent.session_id or "", old_session_id=_boundary_parent,
            tokens_before=tokens_before, tokens_after=_compressed_est,
        )
'''
PREFIRE = '''        new_system_prompt = _rebuild_system_prompt_at_boundary(agent, system_message)
        # NEGATIVE CONTROL: the observer fires BEFORE the durable commit.
        with _swallow('on_compression_complete plugin hook failed', exc_info=True):
            from hermes_cli.lifecycle import has_hook, invoke_hook
            if has_hook("on_compression_complete"):
                invoke_hook(
                    "on_compression_complete", session_id=agent.session_id or "", old_session_id=agent.session_id or "",
                    in_place=in_place, tokens_before=approx_tokens,
                    tokens_after=estimate_request_tokens_rough(compressed, system_prompt=new_system_prompt or ""),
                    platform=getattr(agent, "platform", None) or "cli",
                )
        commit = _commit_compaction(
'''


def _sub(path, old, new, count=1):
    def apply(text):
        assert text.count(old) == count, f"{path}: anchor found {text.count(old)}x, expected {count}"
        return text.replace(old, new)
    return (path, apply)


MUTATIONS = {
    # Negative controls
    "neg-prefire": [
        _sub(CC, OBSERVER_CALL, ""),
        _sub(CC, "        new_system_prompt = _rebuild_system_prompt_at_boundary(agent, system_message)\n"
                 "        commit = _commit_compaction(\n", PREFIRE),
    ],
    "neg-nodefer": [
        _sub(CC, '''        notify = (
            _queue_context_engine_compression_notification
            if defer_context_engine_notification
            else _notify_context_engine_compression_complete
        )
''', "        notify = _notify_context_engine_compression_complete  # NEGATIVE CONTROL: deferral bypassed\n"),
    ],
    # Per-hunk sabotage of the fold-in
    "sab-h1-observer-call": [_sub(CC, OBSERVER_CALL, "")],
    "sab-h2-queue-payload": [_sub(
        CC, "            agent, new_session_id=new_session_id, old_session_id=old_session_id, **payload\n",
        "            agent, new_session_id=new_session_id, old_session_id=old_session_id\n")],
    "sab-h3-tokens-before": [_sub(CC, "            tokens_before=approx_tokens,\n", "")],
    "sab-h4-tokens-after": [_sub(CC, "tokens_before=tokens_before, tokens_after=_compressed_est,",
                                 "tokens_before=tokens_before, tokens_after=None,")],
    "sab-h5-valid-hooks": [_sub(PL, VALID_HOOKS_ENTRY, "")],
    "sab-h6-keep-carrier-post-commit": [_sub(CC, NOTIFY_CALL, NOTIFY_CALL + CARRIER_POST_COMMIT)],
    "sab-h7-payload-and-docs": [
        _sub(HK, '''    "on_compression_complete": {
        "session_id": "test-session-2", "old_session_id": "test-session", "in_place": False,
        "tokens_before": 120000, "tokens_after": 30000, "platform": "cli",
    },
''', ""),
        (DOC, lambda t: "".join(l for l in t.splitlines(True) if not l.startswith("| `on_compression_complete` |"))),
    ],
    # Variants
    "foldin-bounded": [_sub(PD, '''"pre_verify", "on_session_start", "on_session_end",
}''', '''"pre_verify", "on_session_start", "on_session_end",
    "on_compression_complete",
}''')],
    "foldin-ref": [_sub(CC, START_HOOK, ""), _sub(PL, START_HOOK_VALID, ""),
                   _sub(CC, "    attempt: _Attempt, task_id: str,\n) -> _SummaryPhase:", "    attempt: _Attempt,\n) -> _SummaryPhase:"),
                   _sub(CC, "system_message=system_message, attempt=attempt,\n        task_id=task_id,\n    )",
                        "system_message=system_message, attempt=attempt,\n    )")],
}

COMPETITORS = {  # r1 arm commit -> applied onto the new staging commit
    "c93391-code": "c93391-code",
    "c118847-handport": "c118847-handport",
    "c125881-merge": "c125881-merge",
}
OLD_STAGING = "b3b8d73999ec0a629f5bcddb995c2a9761c21afc"


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
        sha = commit(wt, f"arm {arm}-r4 (factory-only mutation of c53806-foldin-r4)")
        git(wt, "update-ref", REF + arm + "-r4", sha)
        out[arm] = sha
    for arm, old in COMPETITORS.items():
        git(wt, "checkout", "-q", "--detach", staging)
        diff = git(wt, "diff", "--binary", OLD_STAGING, REF + old) + "\n"
        p = subprocess.run(["git", "apply", "-3", "--index"], cwd=wt, input=diff, capture_output=True, text=True)
        if p.returncode != 0:
            print(f"# {arm}: apply -3 failed: {p.stderr.strip()[:400]}", file=sys.stderr)
            git(wt, "reset", "-q", "--hard")
            continue
        sha = commit(wt, f"arm {arm}-r4 (r1 arm diff re-applied onto the r4 staging commit)")
        git(wt, "update-ref", REF + arm + "-r4", sha)
        out[arm] = sha
    for arm, sha in out.items():
        print(f"{arm}={sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
