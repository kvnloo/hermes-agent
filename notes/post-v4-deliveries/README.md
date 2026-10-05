# Two additional Hermes delivery records — 2026-10-05

This addendum follows checkpoint `ecb9bcc71023c4dd75605049f2e1100960642297` without rewriting its historical evidence. The mutable ledger now contains **41 Hermes branch records**, alongside 16 OMP and 6 CUA records. These are delivery records, including overlapping owner children and evidence, **not a count of unique fixes**.

## #47198: marker fits within the owner's aggregate cap

Published [1c6d6d1c77b842772151676bc28ddfc5e88c1b9c](https://github.com/kvnloo/hermes-agent/commit/1c6d6d1c77b842772151676bc28ddfc5e88c1b9c) preserves **liuhao1024**'s [original owner commit](https://github.com/NousResearch/hermes-agent/commit/a6dc3d021776f9910debda8bcd8190364c4d7c6b) as its direct parent. It addresses [teknium1's marker-cap review](https://github.com/NousResearch/hermes-agent/pull/47198#discussion_r3581086204).

The existing real temporary three-ancestor hint consumer previously returned 16,051 characters against a 16,000-character cap. Its strengthened assertion fails on the owner and passes with the unchanged marker reserved inside the cap: **one negative failure, one final pass**. The owner runner and supported Python 3.12.14 were used; `git diff --check` passed. This owner tree has no `scripts/check`; there is no modern 11-check or full-suite claim.

This is **owner-child qualification only**. Current `824a942e` has different discovery, digest deduplication, directory rebinding, override selection and a 32,000-character per-file truncation contract. The [separate deterministic directory-priority review](https://github.com/NousResearch/hermes-agent/pull/47198#discussion_r3581086201) remains unresolved, including omitted-hint bookkeeping. No ancestor-first, nearest-first or other retention policy was chosen here. The child is not a current-main port or whole-PR approval.

## #98419: literal transcript survives plaintext fallback

Published [e0c7bbc3b6f8e04e099eb7c4496c2c82edf8a638](https://github.com/kvnloo/hermes-agent/commit/e0c7bbc3b6f8e04e099eb7c4496c2c82edf8a638) is a **test-only child** of **Artemonim**'s [owner head](https://github.com/NousResearch/hermes-agent/commit/205553904950dcdadebae52535c7b73ac7ca1eda). [PR #98419](https://github.com/NousResearch/hermes-agent/pull/98419) records liyangbing's request and the author's request for a regression test.

The consumer exercises real transcript formatting, metadata and `TelegramAdapter.send`. An inert bot boundary raises the actual PTB `BadRequest` on HTML submission, then captures plaintext. The test checks exact spoken literal tags, entities, quotes and emoji. Reversing strip/decode order produces **one negative failure**; restored production yields **one final pass and 11 checks**. Production is unchanged. Only the official pinned PTB 22.8 wheel was added to the existing environment; no project dependency files changed.

The 11 checks qualify the test-child delta against its owner. Three relevant runtime paths were source-identical from `715742` to `ac28abc9`, but later `824a942e` changes the Telegram adapter through held-inbound mixin extraction. Neither the source audit nor a clean read-only merge-tree proves a current-main integration. No live Telegram, speech recognition, chunking, authentication, or complete owner-feature qualification is claimed.

## Remote evidence and next choices

Independent API and Git verification pins both published SHA/tree/parent chains in `deliveries.json`. Each recorded hosted snapshot has zero check runs, statuses and workflow runs: **CI_NOT_RUN**, separate from local qualification.

- For #47198, resolve the owner's deterministic retention-priority contract before any current-main integration. Preserve the precise marker correction and original author.
- For #98419, use the owner-child consumer as review evidence. A current integration would first reconcile the later adapter change; do not relabel the historical one-test result as current-main coverage.
- For CUA [#4537](https://github.com/trycua/cua/pull/4537), **pingu52** owns head `b334ef24dd57441c586822687f89953adc0c1676` and explicitly excludes Sandbox forwarding. The owner accepts `keys: list | str`, while Sandbox keyboard methods accept one `key: str`; the translation contract remains undecided. The protocol does not require held-key methods, and absence alone does not establish a full model-action regression. Do not widen the protocol or duplicate the custom-handler work to force a test.
- CUA #4537 also has a dependency gate: the supported Python 3.12 environment lacks a four-root subset of **42 distributions: 41 locked wheels totaling 40,891,024 bytes, plus local `cua-core`**. Four installed-version mismatches would add 342,722 wheel bytes if lock reconciliation is required. A fresh-environment traversal lists 59 wheels totaling 45,945,150 bytes. These are metadata estimates, not verified downloaded or extracted sizes, a validated complete import closure, or an approved install plan. Owner-head dependency equivalence is still being assessed. No installation, handler test, native key action, or implementation occurred. Parent can select an owner-coordinated inert-keyboard forwarding proof only after the contract and exact supported dependency scope are settled.

Nonbundled provenance: `/workspace/receipts/hint-marker-47198/`, `/workspace/receipts/stt98419/`, and `/workspace/receipts/cua-doc-consumer-intake/README.md`. No tests or source intake were repeated to prepare this metadata. Existing published packets remain unchanged.
