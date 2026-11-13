---
name: skill-library-maintenance
description: "Use when updating vendored skill packs or publishing skills."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [skills, pstack, vendoring, publishing, maintenance]
    related_skills: [hermes-agent-skill-authoring, public-repo-snapshot-publishing]
---

# Skill library maintenance

## When to Use
Use when the owner asks whether pstack (or another vendored skill pack) is being used or kept up to date, asks to "keep our public skills updated", requests a historical usage audit or reviewed public extraction, or when a pack's `SOURCE.txt` pin is older than upstream.

## Standing owner preferences
- **Use pstack while working.** At the start of non-trivial work, load the pstack principle skills that fit with `skill_view` (usually build-the-lever, prove-it-works, sequence-verifiable-units, never-block-on-the-human, guard-the-context-window) and follow them. Following the ideas without loading the skill doesn't count. Say which ones you applied when it matters.
- Keep vendored packs current with upstream, and keep the owner's public skill repos current with the skills learned locally.
- Only touch the active profile's copy. Another profile's copy (for example `profiles/<other>/plugins/pstack`) needs the owner's OK first.

## Update a vendored pack (pstack recipe)
1. Read `<profile>/skills/pstack/SOURCE.txt` for the pinned commit. The upstream clone is `/mnt/zer0models/oss/cursor/plugins`. Run `git fetch -q origin` and `git log --oneline <pin>..origin/HEAD -- pstack` to see what changed.
2. Find the local modifications before overwriting anything. `git archive <pin> pstack | tar -x -C $TMPDIR/old`, then `diff -rq $TMPDIR/old/pstack/skills <installed>`. Ignore `SOURCE.txt`, `LICENSE` and `_agents`. Save each changed file's diff with `diff -u`. Files that exist only locally (for example an added `references/` file) survive on their own.
3. Back up the installed dir with `cp -a`. Then `git archive origin/HEAD pstack` into `$TMPDIR/new`, `rsync -a new/pstack/skills/ <installed>/` (no `--delete`), and `rsync -a new/pstack/agents/ <installed>/_agents/`.
4. Re-apply each saved diff: run `patch --dry-run` first, then for real. If a hunk fails, merge it by hand. Never drop the owner's local change silently.
5. Rewrite `SOURCE.txt` with the new short SHA, its date, the version from `pstack/plugin.json`, and a list of the local additions kept.
6. Verify: every `SKILL.md` `name:` matches its folder, and the patched file still contains the local section. Report new and removed upstream skills (from `comm` of the old and new skill lists).

## Audit and extract personal skills
1. Establish the authorized phase: analysis, extraction, publication and installation are separate gates. An analysis-only audit must not update installed skills, fetch into repositories, change profiles or publish a PR. Keep outputs within the authorized directory; never work around a denied write through the shell.
2. Discover the actual clone from recorded source paths and verify its Git remotes. The known public collections are `kvnloo/kvnloo-skills` and `kvnloo/hermes-jev-skills`, but names alone do not establish the current checkout or layout. Inspect `git worktree list --porcelain`, branch/HEAD, status and remote default branch before choosing a destination. An installer or manifest on an unmerged branch is not shipped infrastructure.
3. For historical value, count actual tool-call evidence across the requested profiles and harnesses, not mtime, current availability or usage metadata. Separate successful loads, failed loads, reference views and incidental source inspection; deduplicate retained transcript copies. Follow [Historical usage and port selection](references/historical-usage-audits.md) for the census and evidence schema.
4. Rank transferable procedures by distinct-session reach, current task fit, safety payoff and modernization cost, not call volume alone. Treat archived skills as possible donors and bundled/upstream skills as reuse candidates. Merge unique laws into maintained class-level skills rather than resurrecting competing broad triggers or copying whole private manuals.
5. Check active thread and capability ownership before modernizing routing, accounting, memory, scheduling or evaluation guidance. Preserve existing authorities; a skill port must not create a competing store or control plane.
6. Review rights and public safety per selected file. A collection's root license or a local `license: MIT` field does not establish rights to third-party prose, scripts, standards, photos or media. Preserve original authors, source commits and notices; unresolved provenance blocks extraction.
7. Extract generic cores with optional harness adapters and a private deployment overlay. Replace hostnames, network identities, private paths and personal examples; remove owner-specific credentials, physical-scene data and implicit spending/overnight authority. Review scripts, references, fixtures, symlinks and media as well as SKILL.md. Zero secret-regex matches is not publication clearance.
8. Keep audit reports, raw session identifiers, local source paths and historical outcome excerpts private. Propose only reviewed generalized skills and synthetic tests for public publication. Don't push public changes unasked; install into live harnesses only under separate approved scope.

## Fix a skill agents keep skipping
Agents pick skills from a ~430-row index whose descriptions are cut to 60 chars (`SKILL_PROMPT_DESC_LIMIT`, agent/skill_utils.py), and generic tools (web_search, web_extract) sit one call closer. Measure misses in state.db first (sessions that hit the trigger but never `skill_view`ed the skill).
1. Front-load the trigger in the description's first ~55 chars ("Use for X/Reddit/YouTube/social URLs and web research."); the rest is invisible in the index.
2. If the trigger is mechanical (URL host, fixed phrase), add a route to the clean profile's `plugins/skill-routes/routes.yaml`. The plugin injects a one-line `<skill-route>` nudge once per session and stays silent after the skill loads. Replay 30 days of user rows through `route()` and read a sample of hits before shipping a pattern: boilerplate in delegated briefs ("research how artists...") false-fires.
3. Never ship a hand-maintained map or catalog of "what works". The owner rejects static docs as guaranteed to go stale. Keep a structured card file as the source: each card has cue, use, not_when, evidence message ids, last seen and hit counts. Regenerate the readable map from it on a guarded user timer (MemAvailable floor plus the shared heavy lock, nice/idle I/O). Then add a freshness pass:
   - Serve only cards with recent owner evidence to routers.
   - Mark cards whose named skills no longer exist as broken.
   - Emit unmatched recent corrections as new-card candidates for the network and hypothesis bots.

   Swap in a new card set only when it beats the current one on a time-split replay of later owner messages. Working instance: `operations/best-way-map-20261105/refresh.sh` and `freshness.py`, run by `best-way-map-refresh.timer`.

## Port approved skills into a public collection
Use once publication is authorized. Recipe with gate commands and test shape: [Public skill port recipe](references/public-skill-port-recipe.md).
1. Keep the destination's existing layout; never add a second installer. Check whether an unmerged installer branch is based on current main (`git merge-base`) and mention it as a follow-up PR only.
2. Branch a fresh worktree from `origin/main` in the authorized location; leave other registered worktrees alone.
3. Rewrite each skill from scratch, never copy-edit the private file: read the source SKILL.md, keep only methods that generalize, and write source references anew instead of copying them (they carry most of the private anecdotes, third-party links and franchise examples). Target well under 150 lines; add one topical reference or template only where depth is needed.
4. Link overlapping pstack/superpowers skills by URL with credit instead of restating them; verify each linked skill name exists in the upstream checkout first.
5. Name a third-party tool only after confirming it is public (`--help`/`--version`, known upstream); otherwise describe it generically. Phrase harness-specific commands as "if your build exposes X, check `--help` first".
6. Run the mechanical gate on added lines of the outgoing diff, plus the repo's tests, then commit one skill per commit and a final tests+README commit. Open a draft PR and link it.
