# Hermes × z0int × RLM × SoL-Pi lab v0

Tracking: #318, #322, #323. Evaluation owner: kvnloo/z0evals#69.

This directory is an experiment join layer, not a new product protocol.

Rules:

1. Existing component receipts stay canonical; the experiment receipt stores pointers plus matched measurements/outcome.
2. `verified_success: null` stays unknown. Execution completion never upgrades it.
3. H0/Z/R/S single-factor cells run before pair/full-stack cells.
4. Shadow components cannot change execution.
5. Exact revisions and frozen fixture ids are mandatory for publishable cells.
6. Private raw transcripts/screens/audio stay local; export sanitized receipts and evidence identities only.

Arms: `H0 Z R S ZR ZS RS ZRS`.

The first implementation task is a validator + failure-injection fixture set for `experiment.schema.json`.
