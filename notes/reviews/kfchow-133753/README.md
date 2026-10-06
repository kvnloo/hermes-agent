# KFChow router review — Hermes #133753

Original design and implementation: **KFChow / @kfchow-ai**. Review, regression tests and the limited cache repair: **@kvnloo**. This evidence branch is not a competing plugin or a new catalog entry. No Hermes production source was changed.

## Exact sources

- Catalog PR: https://github.com/NousResearch/hermes-agent/pull/133753
- Catalog head: `3dfd9583cb872b52b26a2fa407b403811062a0c9`
- Pinned standalone plugin: `ccc8e7c9a79cfe20210552b1084d277d9f847234`
- Newer plugin head inspected: `508dbbe40ba920233c80a02a514dab98d53ea9f2`; its `__init__.py` has the same Git blob.
- Complete plugin `__init__.py`: blob `f487407e8b32b9d0af594948e49eafd6428c0568`, 17,836 bytes.
- Complete Hermes `agent/turn_api_request.py` at the catalog head: blob `1be4db0a6286c81d9024197964902b99e975b089`, 8,961 bytes.
- Complete Hermes `hermes_cli/middleware.py` at the catalog head: blob `7d5888004ba6e1a27506e5504b16964544f9eee4`, 8,459 bytes.

All three reconstructed source files were byte-verified against their Git blob SHA before execution. Container DNS blocked cloning; the GitHub connector supplied the source. No live model, credentials or paid service was used.

## Findings

### 1. Request-only routing does not retain a turn's chosen model

The plugin rewrites a copy of the first request, then returns `None` for tool-loop follow-ups or a duplicate `turn_id`. Hermes rebuilds the request from the agent's unchanged model. Observed request sequences in the focused host-boundary harness:

| Scenario | First request | Next request |
|---|---|---|
| Downgrade, tool follow-up | target-small:free | source-paid |
| Downgrade, repeated first-attempt callback | target-small:free | source-paid |
| Escalation, tool follow-up | target-premium | source-mid |

Interleaving A first -> B first -> A retry also calls the classifier three times, because `_STATE['last_turn']` is one process-global slot.

The host-boundary harness executes the complete source modules above. Plugin discovery, model-specific transport assembly, unrelated host dependencies and the classifier are test doubles. It is not a complete AIAgent run, end-to-end provider test, or measurement of actual billing.

Request-assembly source: https://github.com/NousResearch/hermes-agent/blob/3dfd9583cb872b52b26a2fa407b403811062a0c9/agent/turn_api_request.py#L93-L190
Model ownership source: https://github.com/NousResearch/hermes-agent/blob/3dfd9583cb872b52b26a2fa407b403811062a0c9/agent/chat_completion_helpers.py#L1470-L1525

### 2. Credit cache is not bound to the identity it probed

Warm a positive probe for synthetic account A, then change/remove `NOUS_API_KEY` or change `NOUS_BASE_URL`. The original module returns the cached `True` before inspecting the new identity. The inverse case reuses account A's negative verdict for a healthy B.

`credit-cache-identity.patch` fixes ONLY this local cache defect. It keys the single bounded cache entry by a digest of endpoint + credential + probe model and uses monotonic expiry. It retains no plaintext credential in the cache. The patch includes a standalone nine-case regression file.

It does **not** prove that the environment probe represents the credential actually selected by Hermes, that a two-token probe admits a full prompt's cost, or that the premium target has sufficient quota. It does **not** repair turn routing.

## Tests actually executed

Environment: Linux, Python 3.13.5, pytest 9.0.2; plugin tests are isolated and do not install Hermes (whose declared runtime is Python 3.14).

- Twenty-case host-boundary + credit harness, original: **12 passed / 8 failed**.
- Same harness, limited cache repair: **16 passed / 4 failed**. The four remaining failures are the routing sequences above, deliberately not hidden or marked passing.
- Standalone credit regression, original: **5 passed / 4 failed**.
- Standalone credit regression, repair: **9 passed**.
- Applied combined patch to another fresh source copy using `git apply --check` / `git apply`: **9 passed** again.

Standalone cases duplicate the credit cells in the twenty-case harness; do not add them together as unique coverage. The author's reported 64-test suite, live Hermes plugin validation, full Hermes suite and live provider billing were not run here.

## Apply in the standalone plugin checkout

Download the adjacent patch, then from the plugin repository at the pinned revision:

```bash
git apply --check /path/to/credit-cache-identity.patch
git apply /path/to/credit-cache-identity.patch
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_credit_probe_identity.py -q
```

The author must adopt the repair and update the catalog SHA for users to receive it. No adoption is claimed.

## Related routing work — inspected, not fully reviewed here

- #107945 (KoNit-K): per-task model/provider pins resolve before child construction.
- #89936 (teknium1), preserving daveinturkey15-byte's lifecycle plumbing and Sebastian Müller's Prime Agent design credit: per-spawn reasoning effort.

These are useful candidate public integration surfaces for composing a decision with a concrete child route. They are not a substitute for same-session turn routing or a verified merged dependency.
