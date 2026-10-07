# Run 006 — executable local workflow

Date: 2026-10-07. Author: Codex, at the workspace owner's request.
Scope: local implementation slice of [#455](https://github.com/kvnloo/hermes-agent/issues/455).
Usage and limits: [LOCAL-WORKFLOW.md](../LOCAL-WORKFLOW.md).

## Result

The local CLI now executes curated import → evidence collection and explicit review
→ collision comparison → review rendering → scoped worktree materialization →
verification receipts. Historical fixtures and Runs 001–005 were not rewritten.

Semantic classification and contract curation remain review work. The CLI does not
claim to infer meaning or generate a new implementation from arbitrary discussion.
This completes the bounded local workflow, not the entire productization proposal.

## Executed checks

| Check | Observed result |
|---|---|
| Canonical runner, `tests/experiments/test_change_ir.py` | 2 passed, 0 failed |
| Materialized target, `tests/gateway/test_telegram_group_gating.py` | 30 passed, 0 failed |
| `scripts/check --staged --base 27e1eec4` | 11 checks passed; health 0 blocking, 0 advisory |
| Exact materialization bytes versus `f582ac19` | All three source/test files identical |
| Source checkout after materialization | Clean, same pinned HEAD |

The two workflow tests exercise positive and negative paths in real temporary Git
repositories: source digests and attribution, historical fixture preservation,
unknown state despite matching anchors, stale commit/packet review rejection,
no receipt overwrite, tracked-only evidence, path and symlink restrictions,
explicit operation selection, patch scope, successful/failed/timed-out commands,
input mutation detection and collision comparison independent of PR number.

Targeted tests ran through `scripts/run_tests.sh`, with `HERMES_PYTHON` pointing to
an isolated test environment under this clone's `.git/change-ir-test-env/`.
It uses CPython 3.14.8 and the needed direct test dependencies pinned in the
repository. This is a targeted local environment, not a complete CI installation
or a lock-identical reproduction of the remote Linux environment.

The first system-Python attempt stopped on missing `ruamel.yaml`. Reusing an
interpreter stored under the production Hermes home then hit the test suite's
real-home I/O guard; the guard remained intact. A separate environment resolved
both problems. The first Telegram verification recorded 29 passed and one missing
`psutil` import. Installing the repository's pinned `psutil==7.2.2` in that isolated
environment produced the 30-pass receipt without changing the materialized code.
The original failed receipt remains alongside the successful one.

## Real fixture replay through the CLI

- Input: existing `105624.json`, captured PR and issue-comment exports from Run 005.
- Target: `59a3866ea5a07290afd9a1d137d52d679b77f3ab`, in a clean detached worktree.
- Unreviewed receipt: all three operations `unknown`, independent of anchor matches.
- Explicit review: sibling-addressed user observation `still_needed`; final-response
  mirroring `needs_decision` for this local selection; existing bot-sender policy
  `already_on_main`. This is a local review at the pinned target, not an upstream
  acceptance decision or an automatic reclassification of latest main.
- Selected operation: `OP-observe-sibling-addressed-user` only.
- Materialization: the previously verified patch, applied to a new local branch
  `codex/change-ir-sibling-observe-v0`, with exact allowed filenames.
- Verification: canonical Telegram group-gating tests; exit 0; inputs unchanged;
  `promotion_authorized=false`.

| Materialized file | Git blob |
|---|---|
| `gateway/config_loader.py` | `code@f7fcbf76` |
| `plugins/platforms/telegram/adapter.py` | `code@0c24106e` |
| `tests/gateway/test_telegram_group_gating.py` | `code@29780bd2` |

The curated root-ownership catalog returns 15 pairwise relations: one same operation,
two policy overlaps, three complementary pairs and nine distinct boundaries.
In particular, #102199/#102320 collide, #102258 carries a competing repair policy,
#102208 complements preflight work, and #105608/#128970 retain separate boundaries.
These are consequences of the supplied historical contracts, not a new semantic
audit of the six PRs.

## Review-context measurement

Using Python `len(text)` on decoded UTF-8, the rendered review is 4,379 characters
and the local Git patch is 7,509: **11,888 total**, versus Run 005's captured original
67,558 characters (**82.40% fewer characters**). Raw API envelopes and verification
logs are excluded; their originals remain available through receipt source pointers.

This is a third, explicitly different packet format: rendered Markdown plus local
Git diff. Run 005 measured fixture JSON plus the 7,519-character GitHub compare
diff. Do not replace either historical result with this number. The reduction is
scope-limited to one operation and excludes initial curation/reading cost; it is
not a measurement of human time saved or equal-feature implementation efficiency.

## Evidence and attribution

Local receipts are retained under `.git/change-ir-v0/`; test/check stdout under
`.git/change-ir-tests-final.log` and `.git/change-ir-checks-final.log`.
The artifact manifest has SHA-256
`10d5f835e82f97cc0f261762c9e076c2d75c039ef53227c44fd9618e12b9a194`.
The successful Telegram receipt `105624-verified-002.json` has SHA-256
`dfc694754c967560bd09cab498e677cc46f7bb4012efa724c3b8236d9941a529`.
These local artifacts are not included in a Git clone of this branch.

Reviewed implementation identities: `change-ir.py` `code@bf8ee791`,
`refresh_probe.py` `code@e77ebacf`, test file `code@eebde2fc`.

Original Change IR experiment and rematerialization credit remains with @kvnloo;
Telegram proposal/problem credit remains with @majkonautic and @DavidMetcalfe.
The collision catalog retains each historical PR author and source receipt.
This work adds the local execution wrapper, probe boundary corrections and tests.
No upstream message, push, PR, merge, service or production deployment was performed.
