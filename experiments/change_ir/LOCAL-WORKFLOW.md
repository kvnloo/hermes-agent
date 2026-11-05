# Change IR workflow

Implementation of the v0 workflow in [#455](https://github.com/kvnloo/hermes-agent/issues/455).
The [optional skill](../../optional-skills/software-development/change-ir/SKILL.md)
is the complete operating procedure. Its self-contained Python/Git helper lives
at `optional-skills/software-development/change-ir/scripts/change-ir.py`.
No new model service, runtime dependency, daemon or production gateway change.

## Agent and helper responsibilities

The active agent reads actual discussions, code, tests and repository policy,
extracts independently aging operations, compares behavioral contracts, records
uncertainty and reconstructs selected work against the pinned target. The helper
collects sources with IDs/digests, binds reviews to those sources, preserves each
run receipt, isolates patches and enforces the reviewed verification contracts.
Agent reasoning is reviewable evidence, not a proof of semantic equivalence.

## Commands

Set `CLI` to the skill's `scripts/change-ir.py` in your installed skill directory.
Keep receipts outside the target and materialization worktrees. Every output
filename must be new. Follow the skill's packet/review schemas.

```sh
python "$CLI" collect --repository OWNER/REPO --issue NUMBER --out sources.json
python "$CLI" collect --repository OWNER/REPO --query 'is:pr topic' --out candidates.json
python "$CLI" inspect --repo /clean/target --path AGENTS.md --span code.py:1:100 --out code.json
python "$CLI" ingest intent.json --source sources.json --source code.json --out packet.json
python "$CLI" refresh packet.json --repo /clean/target --review review.json \
  --evidence sources.json --evidence code.json --relations relations.json --out refresh.json
python "$CLI" compare catalog.json --out collisions.json
python "$CLI" render refresh.json --collisions collisions.json --out review.md
python "$CLI" materialize refresh.json --operation OP-selected --patch selected.diff \
  --worktree /new/worktree --branch local/change-ir-review --selected-by 'operator context' --out realization.json
python "$CLI" verify realization.json --contract behavior-test --out verified.json -- \
  bash scripts/run_tests.sh tests/path/test_behavior.py -q
python "$CLI" prepare-pr realization.json --verification verified.json --out pr.md
```

The verification argv must exactly match the approved contract. Repeat
`--verification` for multiple contracts. Use the existing test environment, and
read the complete test logs. Publish only within the user's authorization.
GitHub remains the review surface; no command merges, closes PRs or grants priority.

## Boundaries and migration

Unreviewed operations remain `unknown`, even if every anchor matches. A reviewed
`still_needed` operation requires collected code evidence, a minimal plan, exact
allowed filenames and executable verification contracts. `already_on_main`
also requires code evidence. Every target change requires fresh inspection and
review; historical baselines remain intact.

Run 006 receipts remain historical. They lack collected evidence/contracts, so
refresh them using this workflow before a new materialization. The earlier script
and test paths moved into the optional skill and `tests/skills/`; historical run
commands describe the versions they executed and are not rewritten.

Search includes at most 100 candidates and declares incomplete coverage. Code
excerpts and history limits are explicit. Hashes detect accidental changes but do
not authenticate authors or semantic judgments. Fingerprints omit ignored files
and external dependencies. Verification uses a temporary Hermes home/runtime and
an isolated environment, not an OS sandbox for untrusted commands.

The supplied collision catalog is the source-reviewed historical Run 004 corpus.
Its comparisons do not infer current acceptance, supersession or merge priority.
Same operations flag coordination; different boundaries stay distinct. Explicit
supersession edges require source evidence and retain human credit.

## Runnable checks

```sh
scripts/run_tests.sh tests/skills/test_change_ir_skill.py -q
scripts/run_tests.sh tests/skills/test_authoring_standards.py -k change-ir -q
```

Integration checks exercise real Git worktrees, source collection, evidence
integrity, independent states, historical immutability, collision contracts,
patch boundaries and verification/preparation failures. Run 007 records the live
PR-to-current-main exercise and the thirteen v0 acceptance criteria.
