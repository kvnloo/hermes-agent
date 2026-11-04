# OpenUI intent board (`ephemeral-intent/v1`)

A second reviewed native view on the same bounded pipeline as the repository explorer
(`OPENUI-V2.md`). It brings the ephemeral-ui intent kit (Ripple declared intent, AODL contract,
work and proof, z0intelligence decisions, value, context and health) into Tern natively.

## Contract

- **Catalog:** `openui-generation/src/intent.mjs`. Root `IntentBoard(snapshotId, sections)` with
  1–8 distinct sections: `DeclaredIntent()`, `ContractGates()`, `WorkSlices()`, `ProofReceipts()`,
  `DecisionMix(by: "execution" | "providers" | "status")`, `TokenValue()`, `ContextFlow()`,
  `RuntimeHealth()`. The shared definition lives in ephemeral-ui
  (`integration/openui/ephemeral-intent.v1.json`); the pinned copy in `fixtures/` is checked
  signature-for-signature by `test/intent.test.mjs`.
- **The model selects; the host owns data.** Sections take no data props. The only argument is
  the decision dimension enum. Values come from the host document built by ephemeral-ui
  `tools/openui-intent-doc.mjs` from its sanitized snapshot, validated field by field in
  `openui-preview/src/intent-document.mjs` (64 KiB, 12-item lists, enums, no control
  characters) and again in Luau.
- **Read-only.** No section approves, executes or publishes. `ApproveContract`-style components
  fail as unknown; approval stays with the host's AODL path.
- Same gates as the repository view: static subset, real `@openuidev/lang-core@0.3.1` parse with
  no recovery, reachable statements, bundle identity over selection + document + renderer +
  bridge hashes. `createGenerationAdapter({ library: 'intent' })` selects the catalog.

## Use

```sh
# host document (ephemeral-ui checkout)
node tools/openui-intent-doc.mjs > intent-board.json
# compile a model's program and write a bundle (snapshot key "z0")
OPENUI_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 \
  node ui-tsp/experiments/openui-preview/cli.mjs prepare-intent program.openui intent-board.json SESSION:BRANCH OUT/ --json
tern open --tab OUT/<id>.hvisual.json   # plugin hermes-openui routes it to the native block
```

## Observed (2026-11-03, groot)

| Gate | Result |
|---|---|
| Generation tests (real parser) | 89 passed (68 existing + 21 intent) |
| Preview contracts | 101 passed (85 existing + 16 intent); integration 2; collector 14 |
| Lua 5.4 + stub Tern | 12 existing + 13 intent checks; not live Luau evidence |
| Real model turn | Groq `openai/gpt-oss-120b`, one shot from the adapter prompt, produced `IntentBoard("z0", [ContractGates(), ProofReceipts(), DecisionMix("providers")])`; compiled by the real CLI |
| Ordinary Tern window | Private daemon (`TERN_CONFIG_DIR`/`TERN_DAEMON_SOCKET`), plugin linked there only, bot display. 8-section, 3-section and the model's board rendered natively; ↑/↓ and click move section focus; `tern capture --surfaces` text contains every host value |

Not yet verified: the `/visual` discovery path invoking `prepare-intent` from a live Hermes turn
(it was run by hand), remote/Windows, human pixel review, and the Hermes desktop/T3 renderers of
the same catalog.
