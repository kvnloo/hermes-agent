---
name: test-driven-development
description: "TDD: enforce RED-GREEN-REFACTOR, tests before code."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [testing, tdd, development, quality, red-green-refactor]
    related_skills: [systematic-debugging, subagent-driven-development]
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask the user first):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

## Red-Green-Refactor Cycle

### RED — Write Failing Test

Write one minimal test showing what should happen.

**Good test:**
```python
def test_retries_failed_operations_3_times():
    attempts = 0
    def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception('fail')
        return 'success'

    result = retry_operation(operation)

    assert result == 'success'
    assert attempts == 3
```
Clear name, tests real behavior, one thing.

**Bad test:**
```python
def test_retry_works():
    mock = MagicMock()
    mock.side_effect = [Exception(), Exception(), 'success']
    result = retry_operation(mock)
    assert result == 'success'  # What about retry count? Timing?
```
Vague name, tests mock not real code.

**Requirements:**
- One behavior per test
- Clear descriptive name ("and" in name? Split it)
- Real code, not mocks (unless truly unavoidable)
- Name describes behavior, not implementation

### Verify RED — Watch It Fail

**MANDATORY. Never skip.**

```bash
# Use terminal tool to run the specific test
pytest tests/test_feature.py::test_specific_behavior -v
```

Confirm:
- Test fails (not errors from typos)
- Failure message is expected
- Fails because the feature is missing

**Test passes immediately?** You're testing existing behavior. Fix the test.

**Test errors?** Fix the error, re-run until it fails correctly.

### GREEN — Minimal Code

Write the simplest code to pass the test. Nothing more.

**Good:**
```python
def add(a, b):
    return a + b  # Nothing extra
```

**Bad:**
```python
def add(a, b):
    result = a + b
    logging.info(f"Adding {a} + {b} = {result}")  # Extra!
    return result
```

Don't add features, refactor other code, or "improve" beyond the test.

**Cheating is OK in GREEN:**
- Hardcode return values
- Copy-paste
- Duplicate code
- Skip edge cases

We'll fix it in REFACTOR.

### Verify GREEN — Watch It Pass

**MANDATORY.**

```bash
# Run the specific test
pytest tests/test_feature.py::test_specific_behavior -v

# Then run the broader regression suite authorized by the task
pytest tests/ -q
```

Confirm:
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)

**Test fails?** Fix the code, not the test.

**Other tests fail?** Fix regressions now.

### REFACTOR — Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers
- Simplify expressions

Keep tests green throughout. Don't add behavior.

**If tests fail during refactor:** Undo immediately. Take smaller steps.

### Repeat

Next failing test for next behavior. One cycle at a time.

## Avoid Horizontal Slices

Do **not** write all tests first and then all implementation. That is horizontal slicing: RED becomes "write a pile of imagined tests" and GREEN becomes "make the pile pass." It produces brittle tests because the tests are designed before the implementation has taught you what behavior and interface actually matter.

Use vertical tracer bullets instead:

```text
WRONG:
  RED:   test1, test2, test3, test4
  GREEN: impl1, impl2, impl3, impl4

RIGHT:
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

A tracer bullet is one end-to-end behavior slice. It proves the path works, teaches you about the interface, and keeps each next test grounded in what you just learned.

## Why Order Matters

**"I'll write tests after to verify it works"**

Tests written after code pass immediately. Passing immediately proves nothing:
- Might test the wrong thing
- Might test implementation, not behavior
- Might miss edge cases you forgot
- You never saw it catch the bug

Test-first forces you to see the test fail, proving it actually tests something.

**"I already manually tested all the edge cases"**

Manual testing is ad-hoc. You think you tested everything but:
- No record of what you tested
- Can't re-run when code changes
- Easy to forget cases under pressure
- "It worked when I tried it" ≠ comprehensive

Automated tests are systematic. They run the same way every time.

**"Deleting X hours of work is wasteful"**

Sunk cost fallacy. The time is already gone. Your choice now:
- Delete and rewrite with TDD (high confidence)
- Keep it and add tests after (low confidence, likely bugs)

The "waste" is keeping code you can't trust.

**"TDD is dogmatic, being pragmatic means adapting"**

TDD IS pragmatic:
- Finds bugs before commit (faster than debugging after)
- Prevents regressions (tests catch breaks immediately)
- Documents behavior (tests show how to use code)
- Enables refactoring (change freely, tests catch breaks)

"Pragmatic" shortcuts = debugging in production = slower.

**"Tests after achieve the same goals — it's spirit not ritual"**

No. Tests-after answer "What does this do?" Tests-first answer "What should this do?"

Tests-after are biased by your implementation. You test what you built, not what's required. Tests-first force edge case discovery before implementing.

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Keep as reference, write tests first" | You'll adapt it. That's testing after. Delete means delete. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "Test hard = design unclear" | Listen to the test. Hard to test = hard to use. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "Manual test faster" | Manual doesn't prove edge cases. You'll re-test every change. |
| "Existing code has no tests" | You're improving it. Add tests for the code you touch. |

## Red Flags — STOP and Start Over

If you catch yourself doing any of these, delete the code and restart with TDD:

- Code before test
- Test after implementation
- Test passes immediately on first run
- Can't explain why test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "Keep as reference" or "adapt existing code"
- "Already spent X hours, deleting is wasteful"
- "TDD is dogmatic, I'm being pragmatic"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write the wished-for API. Write the assertion first. Ask the user. |
| Test too complicated | Design too complicated. Simplify the interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify the design. |

## Hermes Agent Integration

### Running Tests

Use the `terminal` tool to run tests at each step:

```python
# RED — verify failure
terminal("pytest tests/test_feature.py::test_name -v")

# GREEN — verify pass
terminal("pytest tests/test_feature.py::test_name -v")

# Full suite — verify no regressions
terminal("pytest tests/ -q")
```

### With delegate_task

When dispatching subagents for implementation, enforce TDD in the goal:

```python
delegate_task(
    goal="Implement [feature] using strict TDD",
    context="""
    Follow test-driven-development skill:
    1. Write failing test FIRST
    2. Run test to verify it fails
    3. Write minimal code to pass
    4. Run test to verify it passes
    5. Refactor if needed
    6. Commit

    Project test command: pytest tests/ -q
    Project structure: [describe relevant files]
    """,
    toolsets=['terminal', 'file']
)
```

### With systematic-debugging

Bug found? Write failing test reproducing it. Follow TDD cycle. The test proves the fix and prevents regression.

Never fix bugs without a test.

## Async cancellation and cleanup regressions

- Gate asynchronous setup and submission with deferred promises instead of sleeps; abort at the actual boundary so the test deterministically reaches the race.
- Assert both prompt settlement and resource cleanup: a rejected promise alone does not prove socket listeners, polling timers, or accepted remote work were released.
- Test cancellation before setup, during setup, during remote submission, and through the owner's cancel/shutdown methods; an abort listener registered after an await does not replay an earlier abort.
- Keep verification within the assigned scope. When the parent owns union CI or the user authorizes targeted tests only, run the focused regression and its authorized test file rather than broadening to the full suite; report that boundary explicitly.

For the boundary matrix, timer/listener assertions, and safe handling of an in-flight remote POST, use [Async cancellation testing](references/async-cancellation-testing.md).

## Testing Anti-Patterns

- **Testing mock behavior instead of real behavior** — mocks should verify interactions, not replace the system under test
- **Testing implementation details** — test behavior/results, not internal method calls
- **Happy path only** — always test edge cases, errors, and boundaries
- **Brittle tests** — tests should verify behavior, not structure; refactoring shouldn't break them

## Integration Verification Pipeline

Unit tests prove modules in isolation. For systems that boot a server, serve
static artifacts, or depend on browser/runtime state, add a deterministic
integration verification step that a future session or CI can invoke as one
command — not as a manual sequence.

### When to add one

- The system under test boots a server (dev server, static file server, proxy)
  and a browser or HTTP client must reach it to observe the behavior you care
  about.
- Local verification currently requires manual steps: pick a port, start a
  server, wait, run a test script, kill the server. Any one of those steps
  can be forgotten or done wrong on a re-run.

### What it looks like

Build two small scripts and one npm target:

1. **`scripts/static-server.mjs`** (or equivalent) — a self-contained server
   launcher that:
   - Accepts `--port PORT` and `--directory DIR`.
   - When `--port` is omitted, bind the real server to OS port `0` and
     announce its assigned port only after binding. Never probe then release
     a port: another process can acquire it before the real server binds.
   - When an explicit port is occupied, fail nonzero without falling back,
     polling that listener, or killing its owner.
   - Print the bound port to stdout.
   - Exits cleanly on SIGTERM/SIGINT so a wrapper can shut it down.
   - Uses Python's `http.server` (or the project's known-good static server)
   if that is the simplest reliable option for the artifact format — prefer a
   command that is already on the machine over installing a Node package.

2. **`scripts/run-inspection-static.mjs`** (or equivalent) — a wrapper that:
   - Spawn an owned static server on OS port `0` by default; read its actual
     bound port before attempting HTTP readiness.
   - Require a successful HTTP response from that owned instance, not merely
     any listener or any HTTP status. Bound both port-announcement and HTTP
     readiness with one deadline; never start tests after cancellation.
   - Forward explicit `BASE_URL`, browser and artifact-directory overrides
     unchanged. For local-only harnesses, require `BASE_URL` to name the
     owned loopback listener and derive its requested port without attaching
     to an existing server.
   - Spawn the inspection/test script only after readiness succeeds.
   - Propagates the child's exit code.
   - Shuts the server down (SIGTERM, then wait; SIGKILL only as last resort)
     in a `finally`-style cleanup so it runs on success, failure, and signal.

3. **`package.json` script** — one entry, e.g.
   `"test:inspection:static": "node scripts/run-inspection-static.mjs"`,
   that runs the whole pipeline with no manual server step.

### Pitfalls

- **Shell backgrounding works, but can hide failures and orphan children.**
  npm normally executes scripts through a shell, which supports `&`. Avoid
  compound background chains that lose the intended PID, cwd, exit status or
  cleanup trap. A Node.js wrapper with `spawn` makes ownership and cleanup
  explicit. A terminal tool refusing foreground `&` is a tool restriction,
  not an npm limitation.
- **Confusing deterministic execution with a fixed port.** Use OS port `0`
  for the actual bind, then pass the resulting URL to tests. Explicit port
  occupancy must fail rather than hijacking or silently replacing the user's
  endpoint. Test this with a live unrelated fixture and assert it received
  no readiness requests and remains usable.
- **Not waiting for HTTP readiness.** Spawning the server and immediately
  running the test produces intermittent failures. Poll the server's root URL
  (or a known artifact URL) with a short timeout before launching the test.
- **Exiting before children finish.** Send SIGTERM, await child exit/reaping,
  and use bounded SIGKILL fallback. A process group can outlive its leader;
  test a real descendant that delays shutdown after its parent exits. Exercise
  success, nonzero exit, readiness failure, early server death, startup signals,
  active-test signals and TERM-resistant children through executables, not
  source-string assertions. Preserve exact RED/GREEN commands and exits.
- **Test script reads env at module load time.** If the server's port or base
  URL is passed via environment variables and the test script reads them when
  the module loads (top-level `process.env.XXX`), changing the env between test
  cases leaks state. Use a lazy getter (e.g. `getAssetOrigin()` reading
  `process.env.NEXT_PUBLIC_ASSET_ORIGIN` at call time) so each test can
  reconfigure without a module reload.
- **Do not call a failure pre-existing without a baseline run.** Execute the
  same test against an untouched baseline and the candidate with matching
  build settings. Report failures in both without weakening assertions or
  broadening scope. Initialization checks do not prove later interaction or
  detail-loading acceptance criteria.
- **Exercise private ESM CLI runners in isolated child processes without adding shipped test hooks.** Install process-local I/O mocks before dynamically importing the entrypoint, set the child's `process.argv` to trigger its existing main guard, and assert exit status, emitted JSONL, dispatch receipts, and cleanup. Keep the fixture mode only in the test file so imports and prototype mocks cannot leak across test cases.
- For visibility-gated React/Ink clocks, mount the real component and retain real roster subscriptions; fake only the clock timers and Date while leaving the renderer scheduler live. Count invoked timer callbacks and committed renders during hidden time, verify visible text immediately after re-expansion, and mutation-remove the reseed separately from the visibility gate. Wait for cascaded passive-effect cleanup without advancing fake time, so the next interval cannot accidentally satisfy an immediate-refresh assertion.
- When releasing WebGL contexts in React cleanup, test the real StrictMode effect replay as well as mocked player disposal. Reusing the same canvas after `WEBGL_lose_context.loseContext()` leaves the replayed effect on a deliberately lost context; let each effect own a fresh canvas in a React-owned host. Exercise actual `loseContext`/`restoreContext`, assert the same live canvas recovers with non-black pixels, and repeat mount/unmount cycles while checking every retired context is lost. Tag asynchronous initialization by generation so obsolete decodes cannot reject or overwrite a newer restored player.
- Test promise-ordering defects in the immediate consumer continuation.
  Retry inside the original promise's rejection handler or direct await/catch,
  with no sleep; helper assertions can add microtasks that mask stale-job
  races. Gate fetch/decode completion with deferred promises and verify both
  settlement and resource/accounting state.

### Verification checklist for the pipeline itself

Before treating the integration test as done, run the pipeline end-to-end:

- [ ] `node scripts/static-server.mjs --help` exits 0 and prints usage.
- [ ] `node scripts/static-server.mjs --port <free> --directory out` starts,
  prints a port, serves `out/` (HTTP 200 on root and on a known artifact).
- [ ] Killing the server process frees the port (next run can reuse it).
- [ ] `node scripts/run-inspection-static.mjs` starts the server, waits for
  readiness, runs the inspection test, shuts the server down, and exits with
  the inspection test's exit code.
- [ ] `npm run test:inspection:static` is one command that does all of the
  above with no manual step.
- [ ] Running it twice in succession does not fail on port occupancy (the
  first run's server is fully shut down before the second starts, or the
  second auto-selects a different port).

### Relationship to TDD

This pipeline is **not** a substitute for unit tests. Unit tests (`test-paths.mjs`
in the session) cover the resolver logic in isolation; the integration pipeline
covers the booted artifact reaching a browser/runtime and producing the expected
state. Both are part of "the test exists and failed first" — the unit test
proved the code shape, the integration pipeline proved the deployed artifact
behaves.

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without the user's explicit permission.
