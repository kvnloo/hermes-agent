# Prepared OpenUI previews in the current frontend

This slice connects the existing generation/preview experiment to Kevin's
`preview/tern-frontend` at `ba430cf6cb567122134a6daa61a227a9c33e36c7`.
It does not replace the frontend or add a testing/control harness.

## Isolation

`base/tern-openui-frontend-20261008` is a **new integration carrier** combining
that exact preview with the unchanged #456/#457/#461 source trees and their
existing workflows. Their original commits remain parents. The user's preview,
base branch, and existing feature branches are not rewritten or advanced.
The #460 collector stays separate; its output format is already compatible.

`exp/tern-openui-frontend` adds the frontend command and sheet on this carrier.
The feature commit is independently cherry-pickable onto a frontend that has the
same prerequisite experiments. The carrier is not an instruction to merge old
PRs into main or to replace the active testing branch.

## Use

Run the normal source-checkout frontend launcher; it already provides
`HERMES_PYTHON_SRC_ROOT`. No additional environment flag or package is required.
In the active frontend, `/visual` shows the exact session/branch scope and usage.
Prepare an existing complete OpenUI program and approved repository document
with that scope, using the existing `openui-preview/cli.mjs prepare` command.
No new model call or repository scan is necessary to re-prepare saved inputs.

Then run `/visual /absolute/path/to/<id>.hvisual.json`. The sheet reuses the
existing strict bundle validator, actual source fingerprints and scope check.
It displays only selected host-computed KPIs, initial mode, identity, and a
native file link. The separately enabled `hermes-openui` file route can open
that file in the existing Luau block; without the plugin, the normal file
viewer/menu is the fallback. The command never installs or enables a plugin.

The link opens the current file again. It is **not** an atomic same-revision
handoff, screenshot receipt, inspection approval or publication action. All
candidate views are labeled unverified. Automatic generation, publication into
the transcript and rich inline treemap mounting remain separate work.

## Ownership and performance

The existing App overlay stack and instance-owned callbacks handle focus and
Close. A late read cannot reopen a dismissed/replaced sheet or cover an approval
that arrived later. Session/branch mismatches hide already loaded data and links;
observed mismatches stay expired even if the user returns. No new session,
gateway, approval, prompt-submit, composer or capture owner is introduced.

This is a read-only preview entry point, not an authorization boundary. It does
not attest an unobserved ABA history or the contents of a later file open.
Escape aborts the owned read. Replaced, bounded reads may finish, but their
results are discarded. Regular-file and byte limits cover the actual read,
including a file growing after stat; UTF-8 decoding is strict.

Metrics are projected once after validation. `node()` only builds a small tree;
it does not scan the repository, hash source, parse OpenUI, make network calls,
start a browser, poll, or invoke a model. Files counts descendants of the
repository root; an empty root has zero files. Text lines/file touches preserve
#460's definitions rather than relabeling them SLOC or net changed lines.

## Verification

New tests live in the existing frontend Vitest suite: bounded local-file reads,
summary projection, overlay replacement/cancellation/session/approval ownership,
and integration with the real #456/#457 validator and source fingerprints.
The existing read-only preview workflow also runs the focused frontend checks
against the real `@stencil-hq/tern` SDK; its existing contract job is unchanged.
The frontend package has no committed lock in this baseline, so that job uses
the existing exact package versions but does not claim transitive lockfile
reproducibility. Installation scripts and telemetry are disabled.

Local checks use Node 22 and a **synthetic JSX representation**, not the Tern SDK
or a live window; do not count them as Luau/pixel/input-to-paint evidence. The
real SDK tests run in CI. Kevin's local rendering tests proceed independently.

## Credit

Credit Kevin Rajan for local testing, the advancing frontend, shared composer
submission and instance-owned overlay fixes; Can Bölük / Stencil Labs and
OMP/Tern contributors for native views and file routes; Thesys/OpenUI for the
generation core; Brit for the explainer direction; bmdavis419/T3 Code for the
preview/verify/publish reference; and Hermes contributors for session authority.
Existing experiment licenses and attribution are unchanged.
