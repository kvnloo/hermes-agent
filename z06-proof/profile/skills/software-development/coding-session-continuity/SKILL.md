---
name: coding-session-continuity
description: Use when recovering and resuming prior coding sessions.
version: 1.3.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [session-recovery, coding-agents, git, provenance, continuity, harness-attribution]
    related_skills: [hermes-agent, codebase-inspection, repository-architecture-audits, test-driven-development]
---

# Coding Session Continuity

## Trigger

Use this skill when the user remembers prior work but cannot find its conversation, suspects it started from another directory, asks which agent/harness performed it, wants the status of recent or “running” sessions, expects those sessions on a Kanban board, wants to resume interrupted coding work without losing decisions and state, says prior context lives in **zerOS / sibling products / SQLite branch inventories** rather than only chat history, or asks how to **import memories** from Claude/Codex/OpenClaw or from past Hermes coding sessions (see `references/hermes-memory-import-vs-sessions.md`).

## Core rule

Recover provenance from primary artifacts, not code style or model-name folklore. Treat these as separate identities:

- **Harness/source:** Hermes CLI, Codex TUI, Claude Code, Grok CLI, IDE extension, etc.
- **Model/provider:** the model and billing/routing backend used by that harness.
- **Repository authorship:** commit author/co-author trailers, including imported donor history.
- **Working directory:** where the session started, which may differ from repositories it inspected.

For example, a Hermes session routed through an `openai-codex` provider is not automatically a Codex CLI session; reading `CLAUDE.md` is not Claude Code execution; and imported Grok/Claude commit trailers do not identify the harness that performed a later extraction.

## Recovery workflow

### 1. Freeze the present state

Before interpreting history, record the live repository root, branch, worktrees, status, recent commits, and relevant untracked files. Do not clean, checkout, stash, or overwrite anything. An interrupted session's most valuable continuation point may exist only in dirty files.

When the user explicitly prefers the **main checkout** (e.g. “main is dirty — clean/commit and work there; another worktree will merge-conflict”), treat that as an active constraint for the recovery:

1. freeze and classify dirty paths (intended vs unrelated);
2. validate and commit the intended slice on main;
3. resume edits on that same main worktree;
4. do not create a parallel implementation worktree for the same effort unless the user reverses the preference.

Never interpret “clean” as `git clean`/reset of untracked user work.

### 2. Search conversation history with high-signal anchors

Start with the platform's supported session-history interface. Search in this order:

0. **This chat first when the user attached a still and said recover:** on-screen chrome, the user quote under the image, `parent_session_id`, and live `/tmp` or experiment dirs. Empty FTS on other profiles does not mean no session — the interrupted overlay work may already be in this Telegram thread.
1. exact absolute repository path or distinctive path segment;
2. recent commit SHA/subject;
3. unique implementation symbol, file, or test name;
4. distinctive user phrase or task title;
5. broad harness/model names only after narrowing the candidate session.

Use discovery results to obtain an exact session ID, then read/scroll that session. Broad searches for “Claude”, “Grok”, or “Codex” are attribution noise until tied to the same session lineage and working directory.

#### Compaction-safe evidence capture

A successful command or search whose detailed output was truncated, compacted, or replaced by a placeholder is not evidence for the missing details. Rerun it with a narrower query before making claims.

- Preserve exact session IDs, message IDs, commit anchors, paths, and timestamps so a compacted investigation can resume deterministically.
- Prefer exact-session windows around meaningful writes/commits over repeating a broad transcript dump.
- Reduce direct-store fallbacks to safe metadata and short chronology rows; do not flood context with raw messages or unrelated tool output.
- If a checkpoint says a command succeeded but omits its branch, worktree, or lineage output, treat those facts as unresolved until re-read.

#### Session, worker, and Kanban status

When the user asks about “sessions running” or wants a board view, reconcile conversation records, live turn execution, delegated/background workers, repository artifacts, and durable Kanban cards as separate layers. A resumable session row—especially one with `ended_at` unset—is not proof of active execution. Confirm the final transaction, child/background state, and current artifacts before choosing status language.

Query the native board independently. If sessions were never Kanban tasks, report the actual board first and label any session-derived lanes **reconstructed**; never create or complete cards just to make the two views agree. See `references/session-kanban-status-reconciliation.md` for the compaction-safe tail fallback, status vocabulary, and presentation recipe.

#### Global and cross-repository chronology

When the user asks what happened “globally,” “last,” or “across all repos,” recover two answers separately: the **literal newest log entry** and the **newest substantive human-directed development task**. They are often different.

1. Inventory each available conversation/event store and record its newest timestamp before trusting it. A product-owned “global ledger” may be less fresh than the harness-native session database.
2. Start with the supported session-history interface. If its recent browse is shallow or broad FTS is polluted, use a read-only metadata fallback to enumerate session ID, activity timestamps, working directory/repository root, parent session, first user prompt, and message/tool counts.
3. Classify automated evaluations, benchmark trials, cron/watchdog runs, and delegated children. Collapse child sessions into their root task rather than reporting each child as independent work.
4. Do not sort only by session `ended_at`: a CLI shutdown may finalize many old sessions at the same time. Prefer actual message/tool timestamps, then `started_at`, and inspect the candidate ending transaction.
5. Read or scroll the exact root session around its last write, test, failure, or interruption. Extract the stopping point from real tool evidence, not from a generated title or broad search snippet.
6. Reconcile current Git state, but attribute files to the recovered session only when logged writes, commits, or patches prove ownership. Existing dirty files may predate the session.
7. Report source coverage and freshness explicitly. If the cross-harness ledger is stale or another harness store was not inspected, say so rather than claiming complete global coverage.

For a metadata-first SQLite recipe, classification heuristics, and a concise continuation-report format, see `references/global-cross-repo-recovery.md`.

#### Channel-aware meaning of “last session”

When the user says only “recover last session,” or sends a still and says recover then hand off to omp, do not force a clarification if the stores can answer both plausible meanings. Recover and label separately:

1. the **literal latest substantive human session across all connected surfaces**; and
2. the **latest interrupted session on the current conversation surface**.

These may differ—for example, a newer Desktop task can coexist with an older interrupted Telegram request. Use message/tool activity timestamps and the ending transaction, not generated titles or session end markers. Choose the literal cross-surface result as the primary continuation, mention the same-surface result when different, and do not resume either merely because it is newest.

After identifying the session, inspect any durable continuation task immediately. A session-recovery intake or stale worker may auto-dispatch while recovery is in progress. Distinguish live execution from retry churn by reading task events, runs, worker logs, PID/heartbeat state, and artifacts. If repeated attempts fail before any tool call or artifact, preserve the task as the durable tombstone, stop unchanged retries through the board’s normal failure/block mechanism, record the exact route failure, and require a proven execution envelope before resumption. Do not represent a spawned PID or `running` row as progress.

See `references/channel-aware-last-session-recovery.md` for a compact decision and evidence recipe.

### 3. Reconstruct the session tree

Collect the root session plus delegated/child sessions. For each, establish:

- source/harness;
- model and provider separately;
- starting working directory and repository root;
- parent/root session relationship;
- tool calls that actually wrote files, ran agents, committed, or verified work;
- start/end reason, especially interruption or signal termination.

Do not classify an agent invocation from prose mentions. Require an actual tool/terminal invocation, child-session source, or direct harness log.

### 4. Correlate external harness logs when attribution matters

If the user explicitly asks which harness was used, inspect each plausible harness's direct session metadata for the exact working directory and time window. Prefer metadata/first-record scans over reading every transcript. Avoid printing credentials, environment dumps, or unrelated prompts.

Absence of a repo-local `CLAUDE.md`, JSONL file, or harness name is weak evidence. Direct session metadata is strong evidence. A harness launched from a parent directory and later `cd`'d remains possible unless command logs rule it out, so state confidence precisely.

### 5. Correlate Git and recovery lineage

Use commit timestamps, subjects, reflogs, worktrees, extraction manifests, and dirty-file paths to connect transcript actions to the repository. Distinguish:

- commits created by the recovered session;
- older history imported or filtered from donor repositories;
- sibling repositories merely audited as dependencies/donors;
- current uncommitted files written after the last commit.

### 6. Recover product prior art outside the current repo

When the user says prior context lives in **zerOS**, a sibling product tree, SQLite branch inventories, or “all the branches,” search those product-control-plane artifacts **before** inventing architecture. Conversation FTS alone often misses multi-harness product work.

1. Inventory product roots under `/workspace/zer0/products/` (and `/home/kvn/workspace/zer0/products/` when distinct) — especially `zerOS/`, `pm/`, and feature-named worktrees.
2. Read branch/worktree inventories first (JSON/SQLite/STATUS), then open only the matching worktrees/docs. Do not walk every dirty lane.
3. Separate **authoritative stores** (`.zeros/` YAML/tasks, SQLite ledgers, product briefs) from **projections** (Cursor canvases, VitePress Master Canvas, dashboard HTML). Canvas-alone is never SoT in zerOS doctrine.
4. For Hermes Desktop features that continue zer0 PM/canvas work, map prior art into Hermes seams (plugin SDK, `projects.db`, kanban boards) rather than transplanting a whole tldraw product by default.
5. Include prior-art paths, branch names, and doctrine constraints in the continuation brief.

See `references/zeros-product-prior-art-recovery.md` for the inventory map and Hermes Spatial ↔ Kanban complementarity sketch.

### 6b. Multi-repo host+package products when FTS returns nothing

Products like **4dps/7dps** (thin package) + **portfolio host** + **Halo/COD donor harnesses** often have **empty `session_search`** for “photosphere / preview grid / living 4D” even when large dirty trees and shot packs exist.

Treat disk + git as primary archaeology:

1. Package: branches, worktrees (often none), `git status` / `diff --stat`, untracked `docs/land-wave*.json` / WAVE package notes.
2. Host repo (may be portfolio `dev`, not the package remote): dirty capture tools + `shots/preview`, `shots/*photosphere*`, `shots/7dps/<stamp>/`.
3. Manifests and measure docs (`WAVE-*-MEASURE.md`, `h6_steam_ok`, dual MAD) over chat titles.
4. Donor reports (`halo/reports/photosphere.md`, COD `shots/7dps-engine`).
5. Split every claim into **origin commit / dirty WIP / donor-only**.
6. When rebuilding completion law, write a feature matrix (WANT/DONE/WIP/GAP/DONOR) into product `prompt.md` from this inventory — do not rely on session narrative alone.

Gauntlet recipe: skill `gauntlet-quality-agent-builds` → `references/host-package-preview-pack-gauntlets.md`.

### 7. Build a continuation brief

Pull these facts into the current conversation:

- original goal and product constraints;
- key architecture/workflow decisions;
- completed commits and verified gates;
- files written after the last commit;
- exact last successful action and interruption point;
- active/pending task list;
- known blockers and assumptions;
- authoritative session link or log path;
- product prior-art paths and branch inventory anchors when the work predates this repo/session.

Clearly label confirmed, inferred, and unknown claims.

### 8. Reconcile before resuming

Conversation history describes what happened then; the working tree is authoritative now. Re-read every relevant current file and rerun status/tests before editing. Do not replay stale patches blindly.

When inheriting uncommitted production code that predates the current session, preserve it as user work. Add characterization tests for existing behavior, then use genuine RED→GREEN cycles for missing behavior and bugs. Never delete inherited work merely to manufacture a clean TDD origin.

When dirty shared `main` forces an isolated branch, describe it as a **temporary integration lane**, not a separate product. Record the canonical target branch, why isolation was required, what commits belong to the lane, and the review/HITL gate for eventual integration. This prevents a safety mechanism from silently becoming product fragmentation.

### 8b. Resume bounded work directly without disturbing another harness

Do not turn an unavailable auxiliary coding harness into a user decision when Hermes can complete the bounded task with its own file, shell, test, and browser tools.

1. Inspect live user-owned harness and application processes only far enough to identify collision risk; do not focus, resume, kill, or enqueue into them.
2. Isolate the new work in a separate repository or non-overlapping worktree and record the source assets read from the active project.
3. Use Hermes directly for bounded packaging, static-site work, adapters, manifests, and verification. Reserve delegation for work whose depth, concurrency, or specialist requirements materially benefit from another worker.
4. Run the real artifact and visual gates before delivery. Missing OpenCode, Claude Code, or Codex authentication is not a blocker when the direct Hermes path is sufficient.
5. Report both the new revision and evidence that the user-owned session/process was left untouched.

Ask the user to choose a coding lane only when the available lanes produce materially different scope, authority, cost, or collision risk—not merely because a preferred helper is unavailable.

### 9. Add work to an existing user-owned Codex session without taking it over

When the user explicitly asks to append a task to an already-open Codex/ChatGPT Desktop session, delegate into that exact thread rather than starting a replacement agent:

1. Observe live process/window metadata without focusing, moving, or capturing unrelated user content.
2. Identify candidate session UUIDs from Codex's session index and rollout metadata. Match on working directory, recent user prompts, and activity time; do not choose from recency alone because approval/review child sessions can be newer than the real root. Read the candidate rollout's `session_meta` and follow `parent_thread_id` until the root is reached; never target a sub-agent as though it were the user-owned conversation.
3. Use the native queue interface against the confirmed **root** thread:
   ```bash
   # Write the full addendum to a file first — inline quotes break in zsh/pty wrappers.
   codex queue --thread <exact-root-session-uuid-or-name> --message "$(< /path/to/addendum.md)"
   ```
   Queue into an existing writer rather than interactive `codex resume`. Resume competes for the transcript lease. Resuming an unloaded multi-agent v2 **sub-agent** fails (“cannot resume … through its parent”); walk `parent_thread_id` and queue/resume the parent. Resume of a root that already has an active writer also fails — queue instead.
4. Put workspace, constraints, definition of done, evidence requirements, Git ownership, and merge policy in the queued addendum. If the task depends on local images or artifacts, include their exact absolute paths and explicitly tell the worker to load/inspect them before implementation; do not assume transport-layer attachment support.
5. Treat the returned queue/message ID as proof of enqueue only. **Queue is wait-your-turn, not Steer.** The Desktop Steer button interrupts the current turn and injects immediately; `codex queue` does not. There is no `codex steer` CLI — do not click Steer in the Codex GUI (focus-safe; that window is user-owned). Unread items remain rows in Codex `queue_*.sqlite` (`queued_items`) until consumed; ping the user when those IDs disappear, not when enqueue succeeds.
6. Preserve user ownership: do not kill, resume interactively, change model/sandbox, or reclaim the session unless the user explicitly asks. Pokémon/Blender Astra work stays on Kevin’s already-open Codex asset thread; CoS coordinates and queues, it does not spawn a competing sculpt session.

## Verification checklist

- [ ] Exact root session and child lineage identified.
- [ ] Harness, model/provider, working directory, and Git authorship reported separately.
- [ ] At least two independent anchors correlate the transcript with the repository (for example, commit + written file).
- [ ] Imported/donor history is not misattributed to the active session.
- [ ] For global chronology, literal newest activity is distinguished from newest substantive human-directed work.
- [ ] For an unqualified “last session,” literal cross-surface and current-surface interrupted sessions are reported separately when they differ.
- [ ] Any durable continuation task was checked for real tool/artifact progress versus auto-dispatch retry churn.
- [ ] Every conversation/event store used has an explicit freshness check; chronology does not rely blindly on bulk `ended_at` values.
- [ ] Current dirty state is reconciled with the transcript's last writes, and only proven writes/commits are attributed to the session.
- [ ] The continuation brief names the exact stopping point and next executable task.
- [ ] Any “running” claim is backed by live turn/worker evidence, not merely a resumable session row or null `ended_at`.
- [ ] The actual Kanban board is reported separately from any reconstructed session-status view.
- [ ] Baseline tests/status are rerun before new edits.
- [ ] No secrets or unrelated transcript content are exposed.

## Pitfalls

- **Searching only by folder name:** generated titles may be generic and the session may mention several repositories. Use commit subjects and symbols too.
- **Treating search snippets as the whole log:** exact-session reads may summarize large histories; scroll around meaningful message IDs and inspect the ending transaction.
- **Trusting a “global” ledger without checking freshness:** mirrors and product-owned ledgers can stop ingesting while harness-native history continues.
- **Sorting only by session end time:** one CLI shutdown can finalize many unrelated sessions together. Rank by actual message/tool activity.
- **Assuming “last” means current channel:** a newer Desktop/CLI session may exist while Telegram contains the latest interrupted request. Recover both meanings and label them instead of silently choosing one.
- **Calling auto-dispatch progress:** repeated spawned runs that fail before tool calls or artifacts are retry churn, not continuation. Inspect runs/logs and stop unchanged retries through durable board state.
- **Calling a resumable session active:** null `ended_at`, recent timestamps, or an open conversation do not prove a turn or worker is executing. Check live agent/background state and the final transaction.
- **Treating recent sessions as Kanban cards:** query the board database independently and label any session-derived board as reconstructed.
- **Calling the latest automated record the latest work:** report literal automation separately from the latest substantive root task.
- **Inferring harness from code style or commit trailers:** imported history and co-author metadata routinely mislead.
- **Conflating provider with harness:** report both fields explicitly.
- **Assuming inspected sibling equals starting directory:** require session `cwd`/repo-root metadata.
- **Attributing every dirty file to the recovered session:** prove ownership through logged patches, writes, commits, hashes, or timestamps.
- **Resuming from transcript alone:** files may have changed after interruption; reconcile live state.
- **Dumping raw logs:** extract a concise continuation brief and redact credentials rather than flooding context.
- **Searching only Hermes FTS for product design:** zerOS/PM work often lives in branch inventories, `.zeros/` tasks, and product briefs on disk.
- **Empty FTS on other profiles after a screenshot:** the still + “recover the session” often points at *this* Telegram thread (and its `parent_session_id`), plus `/tmp` artifacts matching the HUD. Search those before declaring no session.
- **Empty FTS ⇒ no multi-host pack history:** 4dps-class work lives in package+host dirty trees, `shots/**`, and land/measure JSON; inventory those before “no sessions found.”
- **Treating canvas/dashboard projections as SoT:** dual-ledgers against durable stores; keep layout as projection over docs/tasks.
- **Taking over user-launched Codex:** if the user started Codex outside CoS, inspect the Codex session store (`history.jsonl`, `sessions/`) and live PIDs, report lanes, and do not kill, reclaim, or continue those processes unless they say to take over.
- **Inlining a long queue prompt:** shell quoting/pty wrappers drop or split the message. File + `$(< file)` is the reliable enqueue path.
- **Calling enqueue “read”:** a queue UUID means the item is waiting. Confirm consumption via `queued_items` disappearing or the rollout gaining the user message.

## References

- `references/pmfe-harness-correlation.md` — Hermes/Codex sibling-repo case with imported Grok/Claude history and an interrupted uncommitted UI slice.
- `references/global-cross-repo-recovery.md` — metadata-first SQLite chronology across harness stores.
- `references/channel-aware-last-session-recovery.md` — unqualified “last session” resolution across surfaces plus retry-churn evidence rules.
- `references/session-kanban-status-reconciliation.md` — session vs live worker vs Kanban board status vocabulary.
- `references/zeros-product-prior-art-recovery.md` — zerOS/PM branch inventories, SQLite maps, canvas prior art, and Hermes Spatial complementarity.
- `references/hermes-memory-import-vs-sessions.md` — official `import-agent` / `claw migrate` / session export vs MEMORY.md; no bulk session→memory miner; external providers.
