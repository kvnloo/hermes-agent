# Independent filesystem-error regression evidence for Hermes #136343

Owner: yoyodine-industries. Original content-fingerprint design and fix belong to that contributor. This review tests the documented fail-open invariant; it proposes no competing implementation.

- PR: https://github.com/NousResearch/hermes-agent/pull/136343
- Exact head: a6841a848c50ec79801f860b5d595104cb7a8a3e
- Base reported by fresh PR metadata: 27ca2a21f3bcab231f9723c0e15dddb3495d902e
- Exact module: hermes_cli/tree_fingerprint.py
- Git blob SHA1 independently matched: f6fe11685adb52a1a8b30b1eb82de9276d1ab91b
- No full checkout, production edit, upstream post, or downstream publication.

## Reproduction

Run from the directory containing the unchanged owner module and test:

    python3 -B -m unittest test_walk_error -v

Executed: 4 tests, 2 PASS / 2 assertion FAIL, exit 1. Both controls pass: unchanged tree is clean; genuine content edit is detected. Both failure cases use real temporary source files and real os.walk, injecting PermissionError at exactly one os.scandir subtree boundary. The resulting partial fingerprint is non-None, and comparing it with the healthy boot fingerprint reports skew despite unchanged source bytes.

Mechanism: _source_files calls os.walk without onerror. Python's walker suppresses scandir errors by default, so _stat_signature_root's OSError handler never sees this error. The partial listing is hashed and memoized as valid content.

    python3 -B run_handler_control.py

Counterfactual control executed: 4 PASS, exit 0. It supplies a propagating onerror callback to the real walker; unchanged owner source remains on disk. This isolates the proposed cause but is not a production fix or owner PR GREEN.

## Limitations and next action

This is exact-module execution with filesystem fault injection, not live permission manipulation, installed gateway dispatch, or the full repository gate. The accepted same-size/same-mtime memo limitation is unrelated and not challenged. GitHub secondary rate limiting began after the source and owner checks; latest-head/ownership refresh remains required before handoff or publication. Independent critic: PASS for the bounded exact-module finding; see CRITIC.md.

Ask the original owner to cover failed enumeration, including nested subtrees, with a real walker error-path test and preserve the fail-open contract. Do not mark the whole PR rejected based on unrelated accepted memo tradeoffs.
