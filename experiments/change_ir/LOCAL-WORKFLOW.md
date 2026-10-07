# Local Change IR workflow

Implementation slice of [#455](https://github.com/kvnloo/hermes-agent/issues/455).
Python 3.11+ and Git are sufficient for the CLI. No runtime dependency is added.

This is a human-assisted workflow: an operator curates operations, supplies an
evidence-backed semantic review and selects a patch. The CLI binds those inputs
to a Git commit, preserves receipts and applies the selected patch in a separate
worktree. It does not extract semantics from arbitrary prose or generate code.

## Import and refresh

Start with a curated fixture using the existing schema (`105624.json`, `31157.json`
or `78207.json`). Keep its stable Change ID, original authors, source references,
invariants, independent operations and historical baseline. Exported issue/PR
discussions, docs and test files can be attached as sources. Their bytes are hashed;
their text is never executed. Keep those original files available at their paths.

```sh
python experiments/change_ir/change-ir.py ingest experiments/change_ir/fixtures/105624.json \
  --source /path/to/pr-export.json --out /path/to/packet.json
python experiments/change_ir/change-ir.py refresh /path/to/packet.json \
  --repo /path/to/clean-target --out /path/to/refresh-001.json
```

The target must be a clean Git root. Scanned anchors must be tracked files inside
it. Empty probes are `unknown`; unreadable files fail collection. A textual match
never upgrades an operation to `already_on_main` or `still_needed`.

Without a review, every operation is `unknown`. To record a semantic review,
copy `target_sha` and `packet_sha256` from the CLI results into a separate JSON file:

```json
{
  "target_sha": "<full target commit>",
  "packet_sha256": "<canonical packet digest>",
  "reviewer": "<reviewer identity>",
  "operations": [{
    "id": "OP-observe-sibling-addressed-user",
    "states": ["still_needed"],
    "reason": "<finding based on the pinned source and behavior>",
    "evidence": ["<commit:path or review URL>"],
    "allowed_paths": [
      "gateway/config_loader.py",
      "plugins/platforms/telegram/adapter.py",
      "tests/gateway/test_telegram_group_gating.py"
    ]
  }]
}
```

Allowed states: `still_needed`, `already_on_main`, `invalidated`,
`needs_decision`, `unknown`, with `moved` as an additional location qualifier.
Unreviewed operations stay `unknown`. Reviews for a different commit or packet
are rejected. Evidence references and reviewer identities are operator assertions,
not authenticated signatures or automatically verified semantic proofs.

```sh
python experiments/change_ir/change-ir.py refresh /path/to/packet.json \
  --repo /path/to/clean-target --review /path/to/review.json \
  --relations experiments/change_ir/relations.json --out /path/to/refresh-002.json
python experiments/change_ir/change-ir.py render /path/to/refresh-002.json \
  --out /path/to/review.md
```

Every output file is created exclusively and never overwritten. The original
fixture and earlier receipts remain unchanged when the target advances. These
are local append-only conventions; hashes do not prevent deliberate file edits.
Explicit `maintainer_decisions` may be supplied in the review as objects containing
`state`, `by` and `source`. Technical classifications never infer such decisions.

## Compare concurrent work

```sh
python experiments/change_ir/change-ir.py compare \
  experiments/change_ir/fixtures/root-ownership-catalog.json \
  --out /path/to/collisions.json
```

The catalog translates historical Run 004 evidence into explicit contracts:
problem family, lifecycle boundary, outcome, policy and invariants. Comparison
uses those fields, not PR numbers or keyword overlap. Equal contracts produce
`same_operation`; differing policies at the same boundary produce
`overlapping_policy`. Explicit complementary boundaries produce `complements`;
other boundaries in the same family stay `related_distinct_boundary`.
Different outcomes/invariants at the same boundary and policy stay `unknown`.

Original authors and evidence accompany each relation. Contract accuracy still
requires review. The supplied catalog is historical, not a current re-review of
the six PRs. Existing `supersedes` and other provenance edges can be carried in
`relations.json`; comparison does not invent them or choose which PR should merge.

## Materialize and verify a selected operation

```sh
python experiments/change_ir/change-ir.py materialize /path/to/refresh-002.json \
  --operation OP-observe-sibling-addressed-user --patch /path/to/selected.diff \
  --worktree /path/to/new-worktree --branch local/change-ir-review \
  --selected-by '<operator and local selection context>' --out /path/to/materialized.json
python experiments/change_ir/change-ir.py verify /path/to/materialized.json \
  --out /path/to/verified.json --timeout 300 -- \
  /bin/bash scripts/run_tests.sh tests/gateway/test_telegram_group_gating.py -q
```

Only a reviewed `still_needed` operation is eligible. The source checkout must
still match its review. Text patches are limited to exact reviewed filenames;
renames, copies, symlinks, submodules and binary patches are rejected. The new
worktree and branch are preserved for inspection, including on a later failure.
Choose another output name for each new attempt.

Verification runs only the explicitly supplied argv, never a command read from
discussion text or a fixture. It records stdout, stderr, exit status, timeout and
whether tracked changes and non-ignored untracked bytes stayed identical. Hermes
home/runtime directories are temporary and provider credentials are not inherited.
This is process-environment isolation, not an OS sandbox for untrusted commands.
Use reviewed commands and the repository's existing test environment.

A passed receipt means that command exited successfully on unchanged inputs.
Ignored files, external dependencies and services are outside that fingerprint.
Select tests that cover the chosen operation's contract; passing a narrow slice
does not establish every invariant of a larger packet. No receipt authorizes
promotion. The CLI does not merge, publish, close PRs, prioritize work, run as a
service, or modify a production gateway.

## Runnable check

```sh
scripts/run_tests.sh tests/experiments/test_change_ir.py -q
```

The two integration tests exercise real Git worktrees, unknown-versus-reviewed
states, stale-review rejection, immutable output history, source and patch path
boundaries, timeout/failure/input-mutation receipts, provenance and collision
contracts (including an unseen Change ID and a conflicting invariant).
