# Combined memory substrate — downstream study

Base: `e82bf01eec9bb58848209b07f0bc7d8895a39f9b` (fresh upstream/main fetch).
Inputs:
- c0wb0yp0tat0, restore #141876 `af16e3ab16eed2492552c325ad1777533a8b7004` (via readfix).
- jfugalde, hardened read `f90969aef6a62ae475370fe43cc9a0c6d11d3122`.
- Finn763, chain docs #116673 `ffc651bd11982eb5b4e1412f1b4b4c34d91cd42d`.
- Safe failure echoes: #654 `75c8a38c0c5a417166fd6cd22fdcf08d02595d5a`,
  `studies/rfc-143379/runs-20261026/receipts/blocked-echo-v3/candidate.patch`.
- Immutable runner/probes: #659 `5184f7a19bbd6df8b50be32bb1cd501f163c19b9`.

## Composition decisions

Keep main's newer lock permissions, drift snapshot/delete guards, remove-only batch exemption,
retry cap, approval routing, and `07af2357ec` live-entry overflow contract.
The historical chain patch conflicted in batch-growth and drift handling: retain main's
implementations with a None-limit guard. The hardened read replaces chain's unlocked,
cache-mutating read, not main's newer write implementation. It holds the target lock,
sanitizes anchors and docs, and calculates usage from local parsed entries.
Chain writes preflight the reference, then revalidate with the anchor lock held through
commit (anchor before doc lock); an interleaved unlink therefore refuses the write.
Anchor reads hold the anchor lock while collecting doc stats under each doc lock.
Advisory locks do not fence external writers that ignore them.

Read schema is top-level action=read; writes remain operations[]. Doc names are passed
through the real inline agent executor as well as the registry. No combinators added.
The readfix no-echo policy is intentionally not ported: sanitized live echoes keep main's
contract. Its read behavior tests are ported separately; unchanged #654 blocked-echo
probes are also included. Prompt schema snapshots are serialized from the literal schema;
the real renderer is checked remotely.

## Evidence boundaries

Avrea receipts will be linked on the downstream draft PR for the exact pushed SHA.
No author-selected 297-case manifest exists: **NOT_CERTIFIED** for that acceptance bar.
The 4096-byte response probe is advisory: uncapped docs remain uncapped, no silent truncation.
No 300+ cycle real-model/compressor run, private field logs, upstream posting, or deployment.
Successful removal/replacement audit payloads and approval records still retain raw entry
text as on main; this study does not claim blanket poisoning-path or consent closure.
