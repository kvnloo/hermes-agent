# Owner disposition and held-key follow-up — 2026-10-05

This is an additive dated note. Historical commit objects, qualification results and published packet files remain unchanged. The two Hermes handoffs below are source comparisons, not new deliveries or owner-runtime approvals.

## FTS: use the existing #133400 owner carrier

**liuhao1024**'s saved open draft [#133400](https://github.com/NousResearch/hermes-agent/pull/133400), head `b6d3e92f4c491c54028ea931ec00e6e584488e8d` (PR created/updated at 16:36:27 UTC), overlaps our published `2b6d7a3` on **herbic07**'s #133375 exception-class report. Both roll back after a per-index DatabaseError without counting that index as rebuilt. Our patch retains WARNING text; the owner keeps the OperationalError arm and adds a DatabaseError arm with ERROR-level repair guidance. DatabaseError is the superclass of OperationalError, not its sibling.

Favor the owner's carrier; retain our branch as historical corroboration, not a competing promotion or another unique fix. Our real temporary-DB rollback/ordinary-row invariants may be useful, but the exact WARNING assertion would fail against the owner's chosen diagnostic. Owner source includes multi-index coverage, which was not rerun here; our two passes and 11 checks belong only to our exact commit. Stronger repair wording does not establish structural corruption for every DatabaseError. Any adoption requires agreement on that diagnostic contract and exact-head qualification.

## Telegram: use #133401 for the broader selection review

The same owner's saved open [#133401](https://github.com/NousResearch/hermes-agent/pull/133401), head `48141a06e1ed5162eec35e286d9dd860ab66da81` (PR created/updated at 16:37:39 UTC), overlaps our `f3a87ae` at the missing-message diagnostic. It also changes selection to `_effective_update_message(update)` and logs update_id. Our partial diagnostic keeps `update.message` and logs only a constant. These are not equivalent independent fixes or a tested composition.

Favor owner review for selection behavior, preserving **wordpressnewbie**'s report credit and visibility of earlier selection owners #88903/#51747. The owner's synthetic effective-message test and reported results do not independently reproduce real PTB decoding or the reported DM-topic sequence. Our inert-self test cannot transfer unchanged because the owner invokes an adapter method before the guard and changes the expected log. Our classifier extraction was checker remediation, not something to port automatically. No owner-runtime, incident-resolution or merge-readiness approval is made.

## CUA: original-owner held-key handler follow-up

Published [289a65f](https://github.com/kvnloo/cua/commit/289a65f653f1fb42eee8e0ce822979a19baed1b6) preserves **pingu52**'s [#4537 head](https://github.com/trycua/cua/commit/b334ef24dd57441c586822687f89953adc0c1676) as its direct parent and credits the same author's #4536 companion contract. It adds only SandboxComputerHandler.key_down/key_up: list press order, reverse release order, and unchanged scalar/name forwarding. No new normalization, failure cleanup or protocol policy is introduced.

The real handler consumer uses an inert recording keyboard. Untouched owner fails on missing key_down; the final same consumer passes. Scoped Ruff, formatting and diff checks pass. This proves handler forwarding only, not generic model reachability, real keyboard input, VM/native-driver behavior or current-main readiness. Existing keypress, runtime-checkable protocol and other handlers remain unchanged.

Normal owner agent/core package initializers run in a fresh Python 3.12.14 environment with exactly 63 reviewed distributions. No package-module replacement or custom source-loader shortcut is used. Telemetry is disabled before import; process-local network denial applies before imports; the non-autouse mock_litellm fixture is not selected. Standard compiled dependency imports are disclosed: this is not native-library-free execution or an OS network-sandbox proof. No live client, model, service, VM or actual key action occurred.

At **17:08 UTC**, independent API and credential-free Git verification matched exact SHA, tree and sole original-owner parent. Both changed remote blobs match the reviewed commit. Exact-head inventory: **zero check runs, statuses and workflow runs — CI_NOT_RUN**. This is one owner-branch follow-up delivery; publication does not broaden its handler-only qualification.

Local evidence: owner-overlap-133400/handoff-review.md and 133401-independent-handoff.md; cua-held-keys-owner/README.md, independent-review.md and remote-verification.json. No tests or network queries were repeated to prepare this note. No upstream communication, PR state change or competing promotion is authorized by it.
