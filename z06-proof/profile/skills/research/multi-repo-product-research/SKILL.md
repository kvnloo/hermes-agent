---
name: multi-repo-product-research
description: "Use when planning a product or market across user repos."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [research, brainstorming, github, market, go-to-market, data-strategy]
    related_skills: [third-party-stack-research, github, agent-reach]
---

# Multi-repo product research

## When to Use

For requests like "we're combining repos A, B, C — orient us", "what data should we collect for X", "which cities/customers should we target". Locate repos, read locked decisions, ground claims live.

## Procedure

1. **Locate every named repo before orienting.** The user expects their GitHub to be checked, not to be asked for links.
   - `gh repo list kvnloo --limit 2000 --json name,description,isFork,isPrivate,updatedAt,primaryLanguage,url > $TMPDIR/repos.json`, then filter in Python with a regex over name+description (include domain synonyms: e.g. smart city -> city|urban|traffic|twin|transit). Write to a file; piped output of 1000+ repos gets truncated.
   - Matching repos are often FORKS. Resolve the real owner: `gh repo view kvnloo/<r> --json parent`. Collaborators' accounts hold the canonical repos.
   - Read each found repo's README for cross-links: one repo's README often names the sibling repo and its owner (that is how a "missing" repo is found).
   - Also check `gh api user/orgs`. `gh search repos <name>` hits are mostly strangers' repos — say so, never present them as the user's.
   - If a repo truly is not found, report what was searched and ask where it lives (other account, local, unbuilt).
2. **Read the project's anchor/decision files before advising**: `.claude/ANCHOR.md`, `docs/adr/`, `lessons.md`, `CLAUDE.md`/`AGENTS.md`, ROADMAP, via `gh api repos/<o>/<r>/contents/<path> --jq .content | base64 -d`. They carry locked scope, accuracy bars, and measured constraints.
3. **Check the new ask against locked decisions.** If the new direction contradicts a LOCKED scope or a measured result, lead with that conflict and who must sign off, then answer conditionally. Do not silently replan over a locked constraint.
4. **Ground market/landscape claims with live search** (batch 5-10 `web_search` in one execute_code call, then `web_extract` the 2-3 decisive pages). Agency programs, vendor deployments and pilots change monthly; never rank targets from memory.
5. **Separate what software alone can deliver from what needs hardware, partners or data agreements.** Split ambiguous metric names (e.g. "occupancy") explicitly.
6. **Rank with stated criteria.** Criteria line first, then the ranked list with one evidence-backed reason each, then an explicit deprioritize list (incumbent deployed, pilot in progress). Mark items you did not verify.
7. **End with one concrete next unit of work** that fits the repo's own iteration rules (smallest measurable step).

## Adapting a demo across existing products

1. **Inspect the primary demo before proposing features.** Follow `public-video-reference-audit` for the complete interaction sequence and audio, then identify the input gesture, playback/navigation controls, spatial/temporal grounding, context handoff and returned result. A search-model summary or a few screenshots cannot establish the interaction. If the user challenges whether you watched it, answer plainly and finish the media inspection before returning to ideation.
2. **Recover prior intent, then inspect the owning implementations.** Use `unified-memory-operations` for cross-harness retrieval and original-message attribution. Locate the actual candidate worktrees before concluding that an old root checkout lacks the feature. Read the relevant contract/type and its consumer, not only reports or skills; source presence does not establish deployment.
3. **Build a small reuse map before ranking ideas.** For each proposal identify the existing mechanism, the missing integration and the reusable contract. Prefer connecting feedback capture, semantic targeting, candidate review and verification over creating another recorder, dashboard, scheduler or memory store. Share contracts across native/web/3D adapters rather than forcing one overlay onto every product.
4. **Preserve the demo's interaction thesis before adding infrastructure.** Distinguish directing desired changes from reporting defects. Do not turn a fluid talk/point/manipulate workflow into a generic diagnostics, feedback-packet or regression-system proposal. Describe what the person can do without leaving the artifact, then identify the smallest missing integration. Evaluate capture → intended session/agent → change → in-context evidence → accept/undo, including delivery failure and draft/call continuity; keep that proposed loop distinct from what the demo actually proves. Rank by reduced human effort and continuity of use, not merely faster agent execution. Keep developer iteration benefits distinct from ordinary end-user benefits.
5. **Respect evidence resolution.** Low-FPS screenshots and DOM replay cannot establish exact animation timing; propose explicit time-anchored media capture for motion defects. Semantic targets must carry artifact/build identity and expose ambiguous mappings. A recorded journey provides steps, not the expected outcome: require an explicit acceptance condition before turning it into a regression.
6. **Return a few ranked opportunities and one measurable first slice.** Mark proposals separately from existing source and verified runtime behavior. Name the baseline to measure before claiming speedups. Save detailed provenance privately and keep the initial recommendation focused; do not implement, deploy or launch workers for an ideation request alone.

## Reuse inventory + issue dependency graph across repos

For "what have we already built elsewhere that fits product X" plus "graph our issues, their upstream venues and blockers, and give a work order".

1. **Inventory from source, not titles.** Find local checkouts by remote (`git -C <dir> remote get-url origin` over the product/oss roots and `~/.hermes/profiles/*/plugins`). Local `origin/main` is often months stale: list refs by `git for-each-ref --sort=-committerdate` and read the newest integration branch with `git show <ref>:<path>` / `git ls-tree -r --name-only <ref>`. Never fetch or edit in a read-only audit. Per-repo `verify-*/features/*.md` skill docs give a cheap feature + coverage summary; cite them as CLAIMED coverage.
2. **Check uncommitted worktrees.** `git worktree list`, then `git --no-optional-locks status --porcelain` in each candidate. Built-but-uncommitted features have a branch tip equal to some other branch, so a diffstat of zero means look at status, not "nothing built". Flag uncommitted work as at risk.
3. **Check the target product's main for the mechanism before calling it a gap** (`git grep -l -i <term> origin/main -- apps packages`). Several "new" ideas turn out to exist upstream already (notifications, preview annotation, needs-you lanes). In that case reuse = argue in a venue, not port.
4. **Find upstream venues** by regex over a cached discussions index sorted by upvotes. Print the top 5 per topic only; the full index is huge.
5. **Inventory row shape:** idea | product | path/branch/issue | status (shipped/built/designed) | target surface | venue | reuse cost (S/M/L) | evidence + VERIFIED/CLAIMED. End with "take, smallest first" and an explicit "don't port" list. The owner prefers reusing specs/contracts over porting engines.
6. **Graph: parse refs in code, then add judged edges in a separate JSON** (`{from,to,type,reason,evidence}`) so the graph regenerates. Recipe and classification rules are in `references/issue-graph-extraction.md`.
7. **Work order = toposort** over open `blocks` + `fixed_by` edges only (closed items impose no constraint). Report the levels as a table, then list the unordered items by the owner's priority list.

## Output style

- CLI plain text: no markdown headers/bold/fences; numbered sections and indentation only.
- Initial orientation answers stay short; say plainly when the repos have not been read yet.
- Cite repo paths and source facts inline (agency, date, figure).

## Pitfalls

- When the user corrects the repo list mid-request, answer only for the corrected list; do not blend the old name back in.
- Do not stop at the user's own account: the canonical repo may belong to a collaborator, with the user's copy a fork.
- Advice that ignores a repo's measured constraint (e.g. pixels-per-vehicle) will be wrong for the segment; put the repo's measured numbers next to the plan they affect.

## References

- `references/issue-graph-extraction.md` — ref parsing, windowed edge classification, umbrella demotion, edge direction, toposort for issue dependency graphs.
- `references/traffic-cv-hot-lanes.md` — freeway/HOT-lane data needs, sources, incumbents, ranking criteria for the traffic-vision / DemandIQ work.
