## What does this PR do?

`evm_client.py compare` (optional `blockchain/evm` skill, documented as "Shows cheapest/most expensive chain") sorted chains with `x.get("gas_price_gwei") or float("inf")` and read the headlines off the ends of that list. That truthiness test folds two different values into `+inf`:

- **`None`**: `_fetch_chain_stats` swallows an `eth_gasPrice` failure into `gas_price_gwei=None`. The failed chain sorted last and was reported as `most_expensive_gas`, while `errors` stayed `{}`.
- **`0.0`**: an RPC returning `0x0` is the cheapest chain, but it also sorted last and was reported as `most_expensive_gas`.

The sort now uses an explicit `is None` check, so `0.0` stays a real minimum. The headlines come only from chains that reported a price, and both are `null` when none did. Failed chains stay in `comparison` with their null price, and `errors` and `_fetch_chain_stats` are unchanged.

Left unchanged: `_fetch_chain_stats` still maps a response with no `result` to 0.0 gwei (`gas_hex or "0x0"`). `rpc_call` already raises on an RPC `error`, so this only affects malformed responses.

The bug and this fix were first found by the Detail automated bug finder; this PR keeps its fix and trims the tests to two behaviour tests.

## Related Issue

No upstream issue. A search of upstream PRs and issues (`evm_client.py`, `most_expensive_gas`, `cheapest_gas`, `gas_price_gwei`, `evm compare`) found no existing fix. Open #29194 (Injective EVM support) and #18508 (read-only EVM JSON-RPC additions) also modify `evm_client.py`, but not `cmd_compare`. Both also add `tests/skills/test_evm_skill.py`, so whichever of these PRs lands later will need a trivial rebase of that new file.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `optional-skills/blockchain/evm/scripts/evm_client.py` (`cmd_compare`): sort key maps only `None` (not `0.0`) to `+inf`: `float("inf") if x.get("gas_price_gwei") is None else x["gas_price_gwei"]`. `cheapest_gas` and `most_expensive_gas` now come from the priced subset.
- `tests/skills/test_evm_skill.py` (new, 2 invariant tests, stdlib + pytest + `unittest.mock`, no network, per `skills/AGENTS.md`). One test checks that a chain whose gas fetch failed is never a headline and stays visible with `null` gas. The other checks that a `0x0` chain is `cheapest_gas`, not `most_expensive_gas`.

## How to Test

1. `scripts/run_tests.sh tests/skills/test_evm_skill.py -q`
   - On `main` (f8489405600c), both tests fail for the stated reasons: `assert 'ethereum' == 'bsc'`, because the failed-fetch chain is named most expensive, and `assert 'bsc' == 'ethereum'`, because the zero-gas chain is not cheapest.
   - With this change, 2 passed.
2. Negative controls:
   - Restoring the truthiness sort key makes only the zero-gas test fail.
   - Taking the headlines from the unfiltered list makes only the failed-fetch test fail.

   So each test pins one half of the fix.
3. Adjacent: `tests/skills/test_optional_skill_scripts.py`, `test_optional_skill_self_paths.py` and `test_authoring_standards.py` pass with the change (1479 passed across those three files plus the new `test_evm_skill.py`). `ruff check`, `check-windows-footguns.py` and `git diff --check` are clean.

Not tested: a live run against public RPCs. The all-chains-failed case (both headlines `null`) follows from the `if priced else None` branch but is not pinned by a test.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass: only the targeted files listed above were run
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), via `scripts/run_tests.sh`

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A (N/A: the change restores the documented "cheapest/most expensive chain" behaviour)
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

N/A
