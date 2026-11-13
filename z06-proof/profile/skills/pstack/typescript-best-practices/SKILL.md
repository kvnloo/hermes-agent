---
name: typescript-best-practices
description: TypeScript best practices. Use when reading or editing any .ts or .tsx file.
paths: ["**/*.ts", "**/*.tsx"]
disable-model-invocation: true
---

# TypeScript best practices

Apply the **type-system-discipline** principle skill first.

| Rule | Summary |
|------|---------|
| Discriminated unions | Model variants with a `kind` literal discriminant so impossible states can't be represented. No optional-field bags. |
| Branded types | Brand primitives with `& { readonly __brand: "X" }` so they can't be mixed up. Validate once at the boundary. A brand comes from a verifying type guard (`input is AgentId`), never from `as`. |
| Constructive modeling | Build the shape so the illegal value can't be constructed. `[T, ...T[]]` for non-empty, `[T, T][]` for even length, `start` plus `duration` for a range. Not a runtime guard, not a wish for refinement types. |
| Simplest total type | Keep `T[]` while every operation on it stays total. Strengthen to `NonEmpty<T>` only where the loose type forces `!`, a cast, or a "should never happen" throw. |
| `unknown` over `any` | External data is `unknown`. |
| Schemas before guards | Before hand-writing a property-by-property type guard, use the repository's runtime schema library and infer the type from the schema, such as `z.infer`. |
| No `as` casts | Every `as` is a runtime crash waiting. Cast only after validation. |
| Narrowing hierarchy | Discriminant switch > `in` operator > `typeof`/`instanceof` > user-defined type guard > `as`. |
| Type guards | Must verify the claim. A lying guard is worse than `as` because the bug hides behind a name that says it's safe. Name them `isX` or `hasX`. |
| Exhaustiveness | Inline `const _exhaustive: never = x;` in default arms so the compiler errors when a new variant is added. |
| `satisfies` over `as` | Validates the value without widening literal types. |
| Boundary validation | Parse where data crosses in, into a named domain type. `Record<string, unknown>` (however spelled) stops at that parse. Trust types inside. See the **boundary-discipline** principle skill. |
| Schema-derived types | Reach for `Pick`/`Omit`/`Parameters`/`ReturnType`/`Awaited`/`typeof` before declaring a new interface. |
| Object args | Pass objects, not positional, so argument order is self-documenting. Skip on hot paths (per-frame render, tokenizers, parsers). |
| Real tests | Don't mock what you can run. Prefer the framework's real test primitives with leak/disposable checks, and verify UI in a running build. Mock only what you can't run locally. |
| Structured telemetry | Prefer structured logger diagnostics with enough context to debug from an id. No `console.log` in shipped code. |

## Provider identity and asynchronous UI assets

When changing provider marks or other metadata-driven assets:
1. Trace identity and asset metadata from configuration/catalog through the selected option to the rendered component before editing. Treat transport/driver identity separately from agent identity; never identify an agent from its model or user-editable label.
2. Inspect the consuming layout before changing an icon or badge's footprint. A child that grows inside a fixed-width slot can overlap adjacent controls even when its own layout is correct.
3. Keep source selection and image-load state independently testable. Scope completion/error events to the current source so a previous image cannot reveal or suppress the replacement.
4. In ownership-limited shared work, identify required caller changes before implementing the component API. Return exact integration seams and distinguish implemented component behavior from an integrated, verified feature.

For the detailed identity/asset checklist, see `references/provider-identity-assets.md`.

## Cross-client telemetry presentation

When bringing an existing telemetry UI to another client:
1. Trace the working client's selector and normalized telemetry contract before designing the new display. If the derivation is client-local, extract it into the existing shared runtime and keep the original client on that same implementation; do not copy a second formula that can drift.
2. Separate current occupancy from cumulative processing, billing totals, and account limits. Treat absent or nonpositive capacity as unavailable, not zero utilization; never fill the gap with guessed model capacities.
3. Scope subscriptions and retained UI state to environment, thread, provider context, and model selection. Reset an open details surface when its owner changes, while deriving its contents from live telemetry so an already-open surface cannot retain a previous report.
4. Resolve report freshness before applying source precedence. A completed compaction may supersede an earlier turn report; an enclosing record's update timestamp is not proof that its usage measurement is newer. If telemetry lacks enough identity or capacity information, expose the uncertainty instead of carrying stale values forward.
5. Test known usage, absent telemetry, missing and zero capacity, zero occupancy, over-capacity usage, source switching, and compaction. Preserve the measured token count even when a visual progress indicator clamps to its drawable range. Keep static-test results distinct from native interaction acceptance, and report any unexecuted checks explicitly.

Examples: `references/patterns.md`.
