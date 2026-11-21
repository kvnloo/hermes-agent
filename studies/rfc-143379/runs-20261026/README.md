# RFC #143379 runs, 2026-10-26 (downstream only)

This directory holds exact-SHA executions that answer the collaborator's request in
[RFC #143379 comment 6409420509](https://github.com/NousResearch/hermes-agent/issues/143379#issuecomment-6409420509).
The request is to run #654's exact-head falsifiers against the fixed substrate with the sanitized `read()`.

No upstream writes were made. All runs used synthetic data, an isolated scratch `HERMES_HOME` and
disposable detached worktrees. Model-provider credentials were unset. No live profile or service was touched.

## Environment

- Host: a Linux x86_64 lab host (20 cores, kernel 7.2), executed on 2026-10-26 between 06:52Z and 07:40Z.
- Each checkout's canonical `scripts/run_tests.sh` built its own pinned test env: Python 3.14 via `uv`, per-file subprocess isolation, `TZ=UTC`, `PYTHONHASHSEED=0`.
- git 2.56.0.
- Probe sources: #654's unchanged `checkout/test_real_checkout.py`, run through #659's `run_fixed_substrate.py` (#659 head `a18fe04e480e9c924f16cb6dfbce8a0c4bcc910b`; the probe sha256 is in each `receipt.json`).

## Pinned SHAs

| Label | Commit | Owner |
| --- | --- | --- |
| upstream main at run time | `0107da5d2a362b1b0b29aff8ada3fd2d4437f88e` | upstream |
| #141876 read restore | `af16e3ab16eed2492552c325ad1777533a8b7004` | c0wb0yp0tat0 |
| hardened read (`jfugalde/hermes-agent` `fix/read-restore-combined`) | `f90969aef6a62ae475370fe43cc9a0c6d11d3122` | jfugalde (restore by c0wb0yp0tat0, rebased on main `2647748a8b`) |
| #116673 chain docs, latest | `ffc651bd11982eb5b4e1412f1b4b4c34d91cd42d` | Finn763 |

The collaborator's "round-two combined substrate" has **no published commit SHA**. So it was **not** tested.
`f90969aef6` is the closest published stand-in for the "readfix's sanitized `read()`" part. The collaborator's
gist says the readfix cherry-pick is content-identical to it on the five hardening files.

## R1: unchanged #654 probes via the #659 runner (`scripts/run_matrix.sh`)

The battery uses every `tests/tools/test_memory*.py` file at each SHA. The author's exact 297-case list
is still not published, so the runner correctly reports `claimed_297_battery_green=false` and `NOT_CERTIFIED`.

| Probe | af16e3ab16 (#141876) | f90969aef6 (hardened read) | ffc651bd11 (#116673) |
| --- | --- | --- | --- |
| read dispatch contract | PASS | PASS | PASS |
| read concurrency snapshot | **RED** (read overwrote newer in-memory entries) | **PASS** | **RED** (same) |
| external edit visible, frozen prompt unchanged (x2) | PASS | PASS | PASS |
| UTF-8 BOM (x2) | PASS | PASS | PASS |
| corrupt UTF-8 fails closed, disk untouched (x2) | PASS | PASS | PASS |
| chain-doc orphan readable / not writable | skip (no chain docs) | skip | PASS |
| chain-doc reference race | skip | skip | **RED** (write committed after reference removed) |
| 4 KiB doc response (exploratory only) | skip | skip | RED (131,186 bytes) |
| `tests/tools/test_memory*.py` | 149/149 | 165/165 | 170/170 |

Receipts: `receipts/fixed-substrate/<sha>/receipt.json` and the per-probe JUnit XML.

Findings:

1. The hardened read turns the #141876 concurrency RED into GREEN without regressing the dispatch contract or the neighbouring memory tests. That is bars 1 and 2 of the collaborator's request, for the read half only.
2. The two chain-doc REDs belong to #116673 and cannot change until #116673 is re-cut on top of the hardened read. No published commit does that yet.
3. Correction to fork comment 6406901256: the BOM and corrupt-UTF-8 REDs reported there do **not** reproduce with the corrected fixture from `4fc368badc`. The earlier fixture wrote the literal characters `\xef\xbb\xbf` / `\xff`, not the bytes. On real bytes, all three heads pass. Treat the earlier RED as a fixture artifact, not a Hermes defect.

## R2: composition with current main (`scripts/mergetree.sh`, `git merge-tree --write-tree`)

| Pair | Result |
| --- | --- |
| #141876 x #116673 | conflict: `tools/memory_tool.py`, `tools/memory_tool_store.py` (reproduces jfugalde) |
| hardened read x #116673 | conflict: same two files + both prompt-surface fixtures |
| main `0107da5d2a` x #141876 | conflict: `tools/memory_tool.py` |
| main `0107da5d2a` x hardened read | conflict: both memory files + both prompt-surface fixtures |
| main `0107da5d2a` x #116673 | conflict: `tools/memory_tool_store.py` |

Main moved after `2647748a8b`. Teknium landed six memory-tool commits on 2026-10-24/25:
`38968d7552`, `faef4e0ab8`, `07af2357ec`, `ff706b7787`, `b044f7cf28` and `26e8e3f4d5` (#144240).
So **none** of the candidates (restore, hardened read, chain docs) currently applies to main. A rebase is required before any landing order is real.

## R3: blocked-entry echo probe (`probes/test_blocked_echo_probe.py`, `scripts/run_probe2.sh`)

The probe asks: can a memory entry that the load-time scan replaced with `[BLOCKED: …]` in the prompt
still reach the model verbatim through a write-failure response? It also pins main's new contract
`07af2357ec`: "a one-item add over budget returns the live entries again" (Teknium).

| Test | main 0107da5d2a | #141876 | hardened read f90969aef6 | #116673 | **candidate** (main + `probes/make_candidate.py`) |
| --- | --- | --- | --- | --- | --- |
| poison is blocked in snapshot (precondition) | PASS | PASS | PASS | PASS | PASS |
| over-budget add does not echo blocked text | **RED** (`current_entries`) | PASS | PASS | **RED** | PASS |
| no-match hint does not echo blocked text | **RED** (`closest_entries`) | **RED** | PASS | **RED** | PASS |
| ambiguous-match list (batch path) | PASS | PASS | PASS | PASS | PASS |
| main contract: one-item overflow returns live entries | PASS | **RED** | **RED** | PASS | PASS |
| v3: legacy single-op `patch` no-match | **RED** (`closest_entries`, `current_entries`) | not run | **RED** (`closest_entries`) | not run | PASS |
| v3: legacy single-op `remove` ambiguous | **RED** (`matches`) | not run | **RED** (`matches`) | not run | PASS |

Probe versions: v2 (rows 1-5) sha256 `5e6f41ae…`, receipts in `receipts/blocked-echo/`.
v3 (all rows; the committed file) sha256 `af535107…`, receipts in `receipts/blocked-echo-v3/`, run on main, f90969aef6 and the candidate only.
The two v3 rows test predictions from the ChatGPT source review `RFC143379-READFIX-REVIEW-01` (fork comment 6410184456). That review called these two paths OPEN on f90969aef6, and execution confirms both.

Memory-path suite (`tests/tools/test_memory*.py` + `tests/agent/test_*memory*.py`, 30 files):
main 354/354, candidate 354/354.

Findings:

1. xngg1021's and jfugalde's leak claims are **confirmed by execution on current upstream main**. They are not only a property of the restore PR. A poisoned entry is withheld from the system prompt, but it comes back verbatim in `current_entries` (over-budget add) and in `closest_entries` (no-match), both of which go to the model.
2. The hardened read closes the batch-path leaks, but **not** the legacy single-op `patch` no-match or ambiguous `matches` paths. It also closes the over-budget leak by dropping `current_entries` entirely. That **contradicts main's newer maintainer contract** `07af2357ec`, which deliberately restored the echo for one-item adds. The same conflict appears as the merge conflicts in R2.
3. The two properties are compatible. A ~40-line study candidate (`receipts/blocked-echo/candidate.patch`) runs the echoed lists through the same strict threat scan. It keeps the maintainer contract (clean entries unchanged), closes all four measured leak vectors and keeps all 354 memory-path tests green. This is a downstream existence proof, not a proposed upstream patch. The removal path for a blocked entry (model versus human) is still the open design question jfugalde raised.
4. Through the advertised `operations[]` path, the batch walker formats its own ambiguity message, so that row passes everywhere. The raw `matches` list is reachable through the legacy single-op path (v3 row).
5. Not covered here: successful-mutation echoes (`removed_entry`, `replaced_entry`, and similar) and the already-`[BLOCKED:`-prefixed passthrough. The source review flagged both. They are design questions (audit versus model-facing payload), not probed.

## Not run

- The collaborator's round-two combined substrate: no published SHA.
- The author's exact 297-case battery: no manifest.
- The 300+ cycle real-compressor / real-model gate.
- Field logs: these remain private by agreement.
- Full Hermes suite on any candidate in this directory.
- Any composition rebased onto current main.

## Reproduce

```bash
export LAB=$PWD/lab   # scratch dir
git clone --filter=blob:none https://github.com/kvnloo/hermes-agent.git $LAB/repo
git -C $LAB/repo fetch https://github.com/NousResearch/hermes-agent.git \
  pull/141876/head:pr141876 pull/116673/head:pr116673 main:upstream-main
git -C $LAB/repo fetch https://github.com/jfugalde/hermes-agent.git fix/read-restore-combined:jf-readfix
git -C $LAB/repo worktree add --detach $LAB/wt-study a18fe04e480e9c924f16cb6dfbce8a0c4bcc910b
mkdir -p $LAB/probes && cp studies/rfc-143379/runs-20261026/probes/* $LAB/probes/
bash studies/rfc-143379/runs-20261026/scripts/run_matrix.sh    # R1
bash studies/rfc-143379/runs-20261026/scripts/mergetree.sh $LAB/repo   # R2
bash studies/rfc-143379/runs-20261026/scripts/run_probe2.sh    # R3
```

Upstream main is a moving target. R2 and R3 pin `0107da5d2a`, so check it out explicitly if main has moved.
