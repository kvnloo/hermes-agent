# Reproduce owner-safe evidence: hermes-136343

Verdict: PASS for bounded evidence only. Head: `a6841a848c50ec79801f860b5d595104cb7a8a3e`.

Use an existing owner checkout at that exact head. Set OWNER_CHECKOUT to its absolute path and PACKET to this evidence directory's absolute path. Only hermes_cli/tree_fingerprint.py is imported; no full application is started. No production code is bundled. Verify its SHA256 against CRITIC.md. Alternatively, put that exact owner module beside these test scripts; no third-party dependencies are needed.

```sh
cd "$PACKET"
PYTHONPATH="$OWNER_CHECKOUT/hermes_cli" python3 -B -m unittest -v test_walk_error
PYTHONPATH="$OWNER_CHECKOUT/hermes_cli" python3 -B run_handler_control.py
```

Expected results: 2 pass / 2 fail (exit 1); then 4 pass (exit 0) for the runtime counterfactual.

Read CRITIC.md for the contract, attribution, and test limitations. OWNER_HANDOFF.md describes the proposed owner handoff, not an external message already sent.

The original test scripts are unchanged. The included log files are sanitized copies: absolute local paths in traceback frames were shortened to filenames; result lines and assertions are unchanged. No private operational metadata is included.

These checks establish the cited current-head behavior. They do not establish baseline newness or a whole-application gate. Coordinating review refreshed both remote heads and owners after the rate-limit window and reported them unchanged before packaging; the independent critic itself made no remote freshness request. Refresh again before any later publication.
