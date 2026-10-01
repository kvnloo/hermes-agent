## What does this PR do?

The `/subscription` Remote Spending step-up (the "Allow Remote Spending" action) shows the wrong message when the gateway is unreachable.

`requestRemoteSpending` in `ui-tui/src/app/slash/commands/subscription.ts` relied on a `.catch()` to show `slashCmd.subscription.billingUnreachable` ("Could not reach the billing service — check your connection, then retry."). But `ctx.gateway.rpc` (`ui-tui/src/app/useMainApp.ts`) never rejects. It catches every failed request (dropped socket, gateway restart, dead child, "gateway not connected", the request timeout, 120 s by default) and resolves `null`. It also resolves `null` for a malformed response. `GatewayRpc` is typed `Promise<null | T>`. The `.then()` therefore ran with `r === null` and returned `{ granted: false, message: undefined }`. `stepUpDenialResult` has no case for that, so the user saw the default admin-approval copy ("Remote Spending was not allowed — someone with billing permissions (owner, admin, or finance admin) must approve it…") when a retry would have worked.

`requestRemoteSpending` now maps a `null` response to the retry message inside `.then()` and drops the `.catch()`, which could not run. Typed denials (`session_revoked` / `remote_spending_revoked` / `rate_limited`) and the granted path are unchanged.

A step-up whose browser approval outlives the RPC timeout also resolves `null` and now gets the retry message. Retry is correct there too, because the grant persists gateway-side (see the comment on `requestRemoteSpending` in `topup.ts`).

Sibling: `topup.ts` has its own `requestRemoteSpending` with the same unreachable `.catch(() => false)`. There, `null` and a reject both map to `false` (documented as "not yet granted"), so the dead catch changes nothing. A dropped gateway during `/topup` still ends in the billing overlay's admin-approval line, though. Giving it a distinct message needs a reason in the `Promise<boolean>` contract of `BillingOverlayCtx.requestRemoteSpending`, so it is left for a follow-up to keep this diff small.

## Related Issue

No upstream issue or PR found. Searched PRs and issues for `requestRemoteSpending`, `billingUnreachable`, "step-up billing service" and "Remote Spending transport".

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `ui-tui/src/app/slash/commands/subscription.ts`: `requestRemoteSpending` maps `null` to `{ granted: false, message: t('slashCmd.subscription.billingUnreachable') }` and keeps the typed-denial mapping for non-null responses. The dead `.catch()` is removed.
- `ui-tui/src/__tests__/subscriptionCommand.test.ts`: two tests that drive the real overlay ctx built by `/subscription`. (1) `billing.step_up` → `null` gives the retry message. (2) A typed `rate_limited` denial is still carried through. This one passes on `main` too; it guards the rewritten non-null branch.

## How to Test

1. `cd ui-tui && npx vitest run src/__tests__/subscriptionCommand.test.ts`
2. On unpatched `main` with only the new tests, the null test fails: `expected { error: undefined, granted: false, message: undefined } to deeply equal { granted: false, message: 'Could not reach the billing service — check your connection, then retry.' }` (1 failed, 4 passed).
3. With the patch, 5/5 pass. With only the null branch's message replaced by `undefined`, the test fails again.
4. Adjacent: `subscriptionCommand.test.ts`, `subscriptionOverlay.test.tsx`, `billingStepUp.test.tsx` and `topupCommand.test.ts` give 53 passed. `npm run typecheck`, `eslint` and `prettier --check` are clean.

Not tested: the live flow against an authenticated Nous account with a real gateway drop or a real RPC timeout.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: TUI-only change. I ran the targeted vitest files listed above.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
