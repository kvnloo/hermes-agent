# RFC #143379: shared fixed-substrate falsifier handoff

Downstream-only coordination for [experiment #654](https://github.com/kvnloo/hermes-agent/pull/654), [tracking #653](https://github.com/kvnloo/hermes-agent/issues/653), and [upstream RFC #143379](https://github.com/NousResearch/hermes-agent/issues/143379#issuecomment-6409420509). Preserve authorship: c0wb0yp0tat0 owns #141876 and the proposed fixed substrate; Finn763 owns #116673. This harness tests their code without rewriting either author's upstream PR or posting upstream.

## Goal lock

- Requested target: the contributor's **round-two combined substrate plus the sanitized, stateless read fix**, **not** pristine main or the unfixed historical PR heads.
- Acceptance: run #654's *unchanged* read-dispatch and concurrency probes and the real chain-document probes against one pinned, **published 40-character candidate commit**. Require the read dispatch to remain PASS and the previous concurrency/anchor race failures to turn GREEN. Preserve every failure and skip, including encoding, disk, and orphan-document fixtures.
- The author says the **297-case** memory suite must also stay green. A precise list of the 297 tests is **not included** in #654 or verified here; request the author's exact file selection to avoid passing a different suite and calling it 297.
- The **4,096-byte doc-response size** is an *exploratory policy candidate*, not an agreed upstream API requirement: report its result separately.
- The proposed 300+ cycle real-model/real-compressor gate is an **independent experiment**, not satisfied by a green read test.

## Status 2026-10-26

The original upstream heads are pinned in #654:
- Read restoration #141876: af16e3ab16eed2492552c325ad1777533a8b7004.
- Chain docs #116673 (latest previously verified): ffc651bd11982eb5b4e1412f1b4b4c34d91cd42d.
- Study #654 head at handoff: e20a805fc896fb8616031a29bd6d3c5284dc329b.

**BLOCKED on the actual repaired target SHA, not on test construction.** The upstream comment links two gists, but their full contents could not be fetched from this ChatGPT environment. Neither an exact fixed-substrate commit nor the author's 297-file selection has been independently verified. Do not assume a patch in a gist has landed on any PR branch.

## Runner

From a checkout containing this studies folder and a Hermes checkout that has already fetched the candidate commit:

    python3 studies/rfc-143379/checkout/run_fixed_substrate.py /absolute/path/to/hermes-checkout FIXED_40_HEX_SHA /absolute/output-dir --suite-manifest /absolute/path/to/exact-297-files.txt

The suite file contains one repo-relative test path per line, for example:

    tests/tools/test_memory_tool.py

Without --suite-manifest, the runner executes five neighboring memory files, **but never claims the exact 297-case battery passed**. This is by design. Only an exact candidate SHA is accepted; no branch-tip substitution or automatic network access. The runner makes a disposable git worktree, injects the **unchanged** #654 test module and synthetic consent fixture, runs the canonical scripts/run_tests.sh, stores logs and JUnit XML, and writes receipt.json with test/skip counts, source hashes and observed gate state.

The runner itself passed a **synthetic mock-checkout smoke test** and a syntax check. There is **no real repaired-head execution receipt yet**.

## Parallel agent pickups (independent lanes)

**A — Exact-head execution:** Obtain the collaborator's fixed-substrate Git commit SHA (or a trusted patch plus immutable hash) and their precise 297-test suite manifest, fetch into an isolated clone, run the command above, and report receipt.json and run URL on #654. Never label a missing/timeout/skipped probe PASS; do not modify the unchanged probe to make it green. Evaluate read dispatch, concurrent read/write, anchor-unlink race and Unicode/corrupt-file behavior individually.

**B — 300+ cycles:** Use a real Hermes compressor and model with explicitly fixed baseline, K settings, compression ratios 4x to 8x, real paraphrases and source-attributed probes. Report per-cycle/per-bin exact-recitation and cold-pointer misses **including silent non-invocations**. Do not represent seeded toy 3.65% coverage as model recall. Obtain a fresh runner budget/accounting snapshot before costly cloud dispatch.

**C — Confidential logs:** Keep the collaborator's 2.5-week *raw* logs private; arrange access only through a mutually approved restricted repository or equivalent. First establish collection consent and the privacy boundary. Scan for tokens/secrets, identifiers, personal text and tool arguments; redact before any export. Keep an unmodified private source under owner control, restrict access and retention, and have the owner approve sanitized output. Publish **no raw log text or secrets** to #654, the RFC, build artifacts or model prompts. Provide aggregated compaction counts, provenance-loss metrics and sanitization audit only.

**D — Integration review:** Verify the actual fixed substrate composes with current upstream main and retains the declared strict tool schema. Check the #141876 restoration, Finn763's chain-doc handler, prompt-surface fixtures, background-memory consent and group-chat isolation. Keep author's source changes separate from independent tests; preserve original credit.

## Factory boundaries

Only kvnloo/hermes-agent downstream branches and Draft PRs for implementation; existing #654/#653 for results; queue #447 for one canonical summary. No upstream writes, default-branch merges, reviewer pings, or private-log uploads without explicit approval. No claim that the author's code is fixed until the **exact repaired commit** passes.