# RFC #143379 offline receipt consumer

Downstream-only **reader**, not a replacement runner, patch or benchmark. This
consumes the original rfc143379.shared-falsifiers.v1 receipt from
[Draft #659](https://github.com/kvnloo/hermes-agent/pull/659), plus its
actual JUnit reports and the unchanged #654 probe and consent fixture.
No Hermes imports, network, user profile, credentials or models are used.

## Evidence boundary

**VALID_RECEIPT** validates identity and completeness of the supplied files
against independent pins; it **does not** mean CERTIFIED_COMBINED, current-head
status, a real model/compressor run, or authentic author approval.
**VALID_SYNTHETIC** is only for deliberately fabricated positive fixtures.
All inconsistent inputs return **NOT_CERTIFIED**, a reason code and exit 1.

The consumer requires: the published combined **40-hex source SHA** matching
the #659 candidate SHA and externally pinned source SHA; the #659 runner,
original probe, scenarios and path-list manifest digests matching their actual
file bytes; and a separately author-curated **exact 297-testcase identity
manifest**. The runner's suite manifest is a list of test *paths*, not proof of
the author's 297 exact testcase identities. Passing counts without identities,
a neighboring-only/subset-only memory battery or runner self-tests cannot pass.

All four required #659 selectors, one advisory selector and every declared
memory path must have the exact requested/observed JUnit classname::name sets.
The consumer checks reports, logs, unique IDs, suite/row counters, path and
selector metadata, zero required failures/errors/skips and successful exit
codes. The 4 KiB advisory is integrity-checked but is **not** an acceptance rule.
A JUnit older than its own log by over 60 seconds fails STALE_REPORT; missing
reports, failed process exits, forged green flags, malformed XML and mismatched
counters also fail. Timestamp checks are replay warnings, not cryptographic
authenticity. #659's fresh output-directory rule and trusted custody are still
essential. Do not overwrite old run evidence or relabel historical SHA results
as current combined execution.

The rule is frozen as rfc143379-author-297-zero-gaps-v1. Any replacement,
including epsilon=2pp, returns RULE_CHANGE_NOT_AUTHORIZED even if a caller
provides purported approval. Authority metadata is mandatory for the existing
rule (issuer, HTTPS decision_url, declared_at, scope), but the offline parser
**cannot authenticate the author**. Verify approval and the 297 names externally.

## Supplementary case-manifest shape

This is **additional input**, not a replacement for #659 receipt.json. The
following illustrative JSON uses placeholders: it is not executable evidence
or an author-approved manifest. Every path must occur in the supplied #659
suite-path manifest; memory testcase IDs across all paths must total exactly
297, with no duplicates.

```json
{
  "schema": "rfc143379.receipt-contract.v1",
  "evidence_kind": "real_combined",
  "candidate_label": "combined_substrate",
  "source_sha": "<published exact 40-hex SHA>",
  "combined_sha": "<same published combined source SHA>",
  "runner_sha256": "<64-hex #659 runner file digest>",
  "suite_manifest_sha256": "<64-hex runner suite-path list digest>",
  "probe_sha256": "<64-hex unmodified #654 test_real_checkout.py digest>",
  "scenarios_sha256": "<64-hex original consent_scenarios.json digest>",
  "required_cases": {
    "read_dispatch": ["tests.tools.test_rfc_homework::test_read_dispatch_contract"],
    "read_concurrency": ["tests.tools.test_rfc_homework::test_read_concurrency_snapshot"],
    "chain_reference_race": ["tests.tools.test_rfc_homework::test_chain_doc_reference_race"],
    "encoding_freshness": ["<all JUnit IDs matching the exact selector>"]
  },
  "advisory_cases": ["<the exact advisory classname::name>"],
  "memory_cases": {
    "tests/tools/test_memory_tool.py": ["<all author-selected testcase IDs at this path>"]
  },
  "acceptance": {
    "rule_id": "rfc143379-author-297-zero-gaps-v1",
    "authority": {
      "issuer": "<owner of acceptance decision>",
      "decision_url": "https://github.com/NousResearch/hermes-agent/issues/143379",
      "declared_at": "<UTC date>",
      "scope": "Author-selected 297-case battery, unchanged no-skip rule"
    }
  }
}
```

In a synthetic test fixture, use evidence_kind=synthetic and
candidate_label=synthetic_fixture, with a clearly synthetic authority marker.
The example above cannot be used as real admission without the actually
author-provided testcase names and published exact source.

## Commands

Consume an **already executed** #659 output (requires a separate trusted
checkout of #659's runner, not a copy invented on this study branch):

```bash
python3 studies/rfc-143379/receipt_contract/validate.py \
  --receipt /immutable/run/receipt.json \
  --runner /checkout-draft-659/studies/rfc-143379/checkout/run_fixed_substrate.py \
  --suite-manifest /author/297-suite-paths.txt \
  --case-manifest /author/exact-case-identities.json \
  --probe studies/rfc-143379/checkout/test_real_checkout.py \
  --scenarios studies/rfc-143379/checkout/consent_scenarios.json \
  --expected-source-sha <published-40hex-combined-source> \
  --expected-runner-sha256 <independently-pinned-64hex-hash>
```

The author-defined 297-testcase list and the round-two combined substrate
were **not supplied** in the previous October 26 report. Their availability
must be checked afresh. No accepted combined execution is implied by this code.

Run **synthetic** offline regressions from the repository root:

```bash
python3 -m unittest discover -s studies/rfc-143379/receipt_contract -p 'test_*.py' -v
```

The tests construct 297 named **synthetic** JUnit cases plus synthetic probe
reports and fake source/runner bytes in a disposable temporary directory.
They cover one valid synthetic receipt, no 297 manifest, wrong source and
runner hashes, duplicate identities, skipped required cases, forged counters,
stale green XML, missing combined SHA and changed acceptance rules.
These are neither RFC model runs nor real #654 falsifier executions.

## Source attribution

Original RFC and read restore: c0wb0yp0tat0
([#143379](https://github.com/NousResearch/hermes-agent/issues/143379),
[#141876](https://github.com/NousResearch/hermes-agent/pull/141876)).
Chain-doc proposal: Finn763
([#116673](https://github.com/NousResearch/hermes-agent/pull/116673)).
Readfix review: jfugalde (see [#654](https://github.com/kvnloo/hermes-agent/pull/654)).
Receipt format and runner hardening: original [#659](https://github.com/kvnloo/hermes-agent/pull/659)
contributors. The earlier BOM and bad-UTF8 RED was a fixture artifact and was
retracted; this directory does not reopen it.
