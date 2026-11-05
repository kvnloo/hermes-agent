# intake_ledger_match

This private intake plugin observes `pre_llm_call` and always returns `None`. It never adds context, invokes a provider, changes model settings, or waits for ledger I/O on the LLM path.

A context-bound daemon thread matches each owner message using word TF-IDF and 4096-dimensional signed character-trigram hash embeddings. These are local orthographic embeddings, not neural semantic embeddings. The matcher reads only row `id`, `ask`, and `check`. It uses a confidence threshold of 0.30 and a best-versus-second margin of 0.025. Explicit row IDs and repository paths get stronger matches. A low-confidence message becomes a new `I<nnn>` row. The new ask is a shortened extract with request boilerplate removed.

`register(ctx)` binds the profile home and reads optional settings through the existing plugin API:

```yaml
plugins:
  enabled:
    - intake_ledger_match
  entries:
    intake_ledger_match:
      settings:
        ledger_path: /path/to/ayo-ledger.json
        owner_id: '1083429746'
```

The default ledger is Kevin's existing intent-analyzer `ayo-ledger.json`. CLI, TUI, and ACP are local owner surfaces. Remote platforms must supply the configured owner sender ID. Explicit assistant/tool roles and subagents are ignored. Today's Hermes payload supplies `turn_id`, not native message ID. Supplied `source_msg_id` or `message_id` takes precedence and is preserved. A missing identity fails open and logs an error rather than inventing an ID.

## File writes

All cooperating writers must acquire `<ledger>.lock` with `flock(LOCK_EX)`. The plugin reads the ledger only after acquiring that stable sidecar. It deduplicates message IDs, allocates new IDs, and preserves unrelated row fields inside the same transaction. It fsyncs a same-directory temporary file, replaces the ledger atomically, and fsyncs the directory. The existing ledger file must exist and pass schema checks. Invalid input is not replaced. The worker abandons a lock attempt after five seconds.

The plugin also checks for changes by non-locking writers before replacement. This detects many conflicts but cannot make non-cooperating writers safe. Existing `render_ledger.py` does not honor this lock. That separate writer needs the same lock protocol before concurrent updates have a complete guarantee.

## Logs and lifecycle

The plugin writes JSON lines to the bound profile's `logs/ledger-match.log`. Events include `loaded`, `pre_llm_call`, `ledger_updated`, and `error`. The logs include message IDs and error classes, not message bodies. A logging error never stops the LLM call. `on_session_end` and unload drain workers for at most six seconds. Forced process termination can lose in-flight work. This is an observer, not a durable queue.

## Verification

Tests are also installed at `intake/plugins/test_intake_ledger_match.py`, beside the existing intake plugin tests. In the source checkout, use the canonical runner through fleet-build:

```bash
HERMES_PYTHON=$(command -v python3) scripts/run_tests.sh -j 1 tests/plugins/test_intake_ledger_match.py
python3 scripts/replay_intake_ledger_match.py replay-labels.json replay-ledger.json --out replay-result.json
python3 scripts/replay_intake_ledger_match.py replay-labels.json replay-ledger.json --sequential --out replay-sequential.json
```

The operation folder contains frozen labels, source line numbers, both replay attempts, installation hashes, and exact fleet commands. The labels were not changed after scoring. The matcher was tuned on this coverage set, so its score is not a held-out estimate.

The offline smoke uses a host stand-in and must not be represented as a live Hermes turn. No gateway restart or public action is part of installation.
