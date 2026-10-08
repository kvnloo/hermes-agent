# Pinned Git data for the OpenUI/Luau preview

Opt-in host-data slice stacked on Hermes #457 (`1fb36535a2f703ec5675e2477ce6ad299088a170`).
It replaces the synthetic **input fixture**, not the OpenUI parser, view, lifecycle
or renderer. Nothing is automatically loaded by Hermes or sent to a model.

## Run

Requires Node 22.16+ and Git 2.47+ on a user-selected, locally available repository.
No installation, npm dependency, network request, checkout or model call is needed.
Use an explicit ancestor base and head; they are resolved once to full commit IDs:

```sh
node ui-tsp/experiments/openui-repository/cli.mjs \
  /path/to/repository BASE_COMMIT HEAD /tmp/hermes-openui-metrics
```

The command prints one absolute `repository.json` path. A private sibling
`provenance.json` records commit IDs, collector-source and document hashes, limits,
counts, exclusions and metric semantics. Repeated runs create separate private
output directories rather than replacing another run's files. Keep outputs outside
watched plugin/experiment sources; the CLI reuses #457's existing output guard.

Feed that **document path** to the unchanged preview CLI:

```sh
node ui-tsp/experiments/openui-preview/cli.mjs prepare \
  ui-tsp/experiments/openui-generation/fixtures/explorer.openui \
  /path/printed/by/collector/repository.json local-dogfood:branch-a \
  /tmp/hermes-openui-bundles
```

Preparation still needs #456's isolated locked OpenUI installation with telemetry
and install scripts disabled. Keep the provenance alongside the prepared artifact
for inspection. Use #457's existing explicit-open/capture/inspection instructions;
this collector does not install/open Tern or authorize publication.

## Exactly what the numbers mean

- `code`: committed regular **UTF-8 text lines**, including comments and blanks;
  LF separators plus a nonempty unterminated final line. Not syntax-aware SLOC.
- `churn`: number of **non-merge commits touching each current included path** in
  `base..head`, across reachable branches. Not added/deleted lines or net diff.
  A change followed by a revert counts twice. Merge-only conflict resolutions are
  excluded, and rename history is deliberately not followed.
- `files`: only included text files at head, not all repository files. Deleted or
  old renamed paths do not inflate current-view aggregates.

The title names the metric policy, shortened revision range and omitted count;
the sidecar retains full IDs and semantics. Binary/NUL or invalid-UTF-8 blobs,
symlinks, gitlinks, >1 MiB blobs and labels incompatible with the native document
contract are excluded with reason counts. No omitted content is called zero data.
Directories are exact sums over included descendants. Tracked vendor/generated
text is included; this is not a source-language classifier or secret scanner.
File/directory labels can themselves contain private information: keep output local
and review it before any later sharing. No file contents, remotes, author identities
or absolute repository root are emitted.

## Reuse and bounds

Git owns traversal, object access and history: one `ls-tree -r -l -z --full-tree`,
one `cat-file --batch` for **unique** eligible blobs, and one NUL-delimited raw
`log` query. Eight Git invocations for a nonempty snapshot, independent of file
count. IDs derive from paths, not rank/order; directory aggregates are computed
once. The existing preview normalizer validates the final document. No per-file
subprocess, filesystem crawl, persistent index, daemon or replacement Git parser.
Only Git's documented machine-output framing is decoded.

The collector ignores ambient `GIT_*` repository overrides, disables replacement
objects, optional locks, external diffs/textconv, global/system configuration and
lazy fetch; transport protocols are denied in the child. It trusts the explicitly
selected local Git installation/repository, not arbitrary host extensions.
Dirty/staged/untracked working-tree data is never read into the snapshot.

Hard ceilings: 50k tracked entries, 1 MiB per included blob, 128 MiB unique blob
bytes, 32 MiB raw history and a 60-second total subprocess deadline. Test/host
limits may lower these, never raise them. Shallow/missing history, non-ancestor
ranges, cancelled/failed commands, oversized outputs or invalid final documents
fail without returning a partial snapshot. Large files have explicit exclusion
counts; other resource overruns abort rather than truncating history silently.

## Verification

```sh
node --test ui-tsp/experiments/openui-repository/test/collect.test.mjs
```

Tests create real temporary Git repositories and exercise committed-vs-working-tree
isolation, UTF-8/binary/symlink handling, range semantics, duplicate-object batching,
stable identity, exclusions, cancellation, limits, ref movement, output permissions,
and the existing generation-binding/preview-bundle contract. No Git semantics mock
is used; the process-count wrapper delegates every call to real Git.

CI also runs the unchanged real OpenUI integration and preview suites and pipes a
new synthetic Git repository through the collector into the actual prepare CLI.
Host collection timings are **not Tern input-to-paint measurements**. Live Tern
loading, pixels, interactions, focus and publication remain #457's pending gates.

## Provenance

Credit Kevin Rajan (@kvnloo) for the native artifact/reuse/isolation direction;
Git contributors for repository/object/history plumbing; Thesys/OpenUI contributors
for generation; Brit for the explainer direction; bmdavis419 and T3 contributors
for preview → verify → publish; and Can Bölük / Stencil Labs, OMP/Tern and Hermes
contributors for the native contracts. Reuses #456/#457's unchanged host validation;
no OpenDesign, TanStack, Jev or new rendering code.

Git contracts: https://git-scm.com/docs/git-ls-tree,
https://git-scm.com/docs/git-cat-file, https://git-scm.com/docs/git-log.
This is an isolated downstream experiment; no upstream endorsement is implied.
