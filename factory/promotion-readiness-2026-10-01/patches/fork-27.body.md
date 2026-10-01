## What does this PR do?

`subscription_manage_url()` (`agent/subscription_view.py`) builds the `/manage-subscription` deep link the CLI opens from `/subscription`. Its docstring says the output is `{portal_origin}/manage-subscription?org_id=<id>[&plan=<tier_id>]` and that it mirrors the TUI's `buildManageUrl`. In practice it started the outbound query from the server `portalUrl`'s own query and only popped `org_id`/`plan`. Any other param on `portalUrl` (`topup=open`, `utm_*`, `ref`, …) was carried onto the manage page.

The TUI (`ui-tui/src/app/slash/commands/subscription.ts::buildManageUrl`) and desktop (`apps/desktop/src/app/settings/billing/use-billing-state.ts::buildManageSubscriptionUrl`) builders both keep only `new URL(portal_url).origin`, so the same subscription state gave the CLI a different URL from the other two surfaces.

This PR builds the query from the contract-owned keys only (`org_id`, then `plan`). The http(s)/netloc guards are unchanged. `_absolutize_portal_url` is untouched, so callers that use `portalUrl` directly keep its query.

Reviewer note: this reverses part of #68689. Its commit message says `subscription_manage_url` "now preserves unrelated portal query params (parse_qsl, popping only the contract-owned org_id/plan) and restricts to http/https schemes, matching the desktop URL builder". The desktop `buildManageSubscriptionUrl` used `new URL(portalUrl).origin` at that commit and still does, so the CLI and desktop have emitted different query strings since then. The test that pinned the passthrough (`test_manage_url_preserves_unrelated_query_params`) was later removed in the suite-wide test prune (6b81590c55). If carrying portal query params onto the manage page is intended, the TUI and desktop builders are the ones to change instead, and this PR can be closed.

Impact is latent: it only shows up when `GET /api/billing/subscription` returns a query-bearing `portalUrl`. Query-bearing portal URLs do exist on the billing side: the server sends a relative `portalUrl` such as `/billing?topup=open` on billing error payloads, and `build_billing_state` falls back to `{portal}/billing?topup=open`. Neither of these reaches `subscription_manage_url` today, because the subscription fallback is the bare portal base.

## Related Issue

No upstream issue. Searched open/closed PRs and issues for `subscription_manage_url`, `manage-subscription`, and portal query terms. The only relevant result is #68689, which introduced the behaviour.

The issue was first flagged by an automated Detail (detail.dev) scan on my fork. This is a trimmed version of that fix (kvnloo/hermes-agent#27).

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `agent/subscription_view.py`: `subscription_manage_url` no longer seeds params from `parts.query`. It emits only `org_id`/`plan` (org_id first). Dropped the now-unused `parse_qsl` import.
- `tests/agent/test_subscription_view.py`: one behaviour-contract test, `test_manage_url_drops_portal_query_params`. A `portalUrl` carrying `topup=open&utm_source=email&org_id=stale` yields exactly `…/manage-subscription?org_id=org_1&plan=plus`.

## How to Test

1. `scripts/run_tests.sh tests/agent/test_subscription_view.py -q`
2. On `main` without the fix, `test_manage_url_drops_portal_query_params` fails (1 failed, 14 passed). Expected `https://portal.example/manage-subscription?org_id=org_1&plan=plus`, got `https://portal.example/manage-subscription?topup=open&utm_source=email&org_id=org_1&plan=plus`.
3. With the fix: 15 passed. Adjacent: `tests/agent/test_subscription_view.py tests/hermes_cli/test_subscription_cli.py tests/hermes_cli/test_billing_portal_url.py tests/agent/test_billing_view.py` give 46 passed.
4. Not tested: the live portal. I have not confirmed whether `GET /api/billing/subscription` ever returns a query-bearing `portalUrl`. The TUI and desktop builders are unchanged and their tests were not run. The full `tests/` suite was not run, only the four files above.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted files above were run, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A. The existing docstring already describes the corrected shape.
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
