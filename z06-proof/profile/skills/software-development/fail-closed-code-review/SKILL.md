---
name: fail-closed-code-review
description: "Use when issuing immutable, machine-readable code verdicts."
version: 1.2.0
metadata:
  hermes:
    tags: [code-review, fail-closed, immutable, verification, json]
    related_skills: [requesting-code-review, github-code-review]
---

# Fail-Closed Immutable Code Review

Use this skill when the user wants a final review rather than implementation,
especially when files must not be modified or the verdict must be machine-readable.
The deliverable is a verdict grounded in the final observed worktree, not a patch.

## Invariants

- **Read-only means read-only.** Do not stage, format, auto-fix, generate fixtures
  inside the repository, or run commands whose normal behavior rewrites files.
- **Review the whole current change.** Include staged, unstaged, and untracked
  files; ordinary `git diff` does not include untracked files.
- **Fail closed.** A security concern, reproducible logic defect, incomplete
  scope, unparseable required output, or stale verification evidence blocks a pass.
- **Honor the requested envelope exactly.** If the user requests JSON only,
  return one valid JSON value with no markdown fence or prose around it.
- **Green tests are evidence, not proof.** Audit lifecycle transitions, ownership,
  stale async completion, and untested state combinations independently.

## Workflow

### 1. Read governing instructions

Load repository and nearest scoped instruction files before evaluating the diff.
Load the applicable review skill, but do not follow auto-fix or commit steps when
the user requested an immutable review.

### 2. Establish scope

Capture:

```bash
git status --short
git diff --stat
git diff --check
git ls-files --others --exclude-standard
```

Read tracked diffs by file and read every untracked source/test file directly.
For large diffs, split review by file rather than truncating the combined patch.

#### Live PR scope when head and base diverged

For a hosted PR, bind the provider-reported head SHA, base SHA, state, and file list,
then verify the remote PR head independently. Do not assume `git diff base..head`
is the PR patch: when the feature branch started from an older base, that range can
include unrelated commits that landed on current base after the merge-base. Review
the provider file set and `git diff $(git merge-base base head)..head`; reconcile
both views before accepting scope. Re-freeze the live head after review and again
after any repair push.

When other agents may still be writing, also record a hash manifest for every
changed and untracked file. `git status` and `git diff --stat` can remain
identical while an untracked file is rewritten, so they are not a sufficient
snapshot identity.

Honor data-boundary constraints during discovery. If the caller excludes
private data, keep searches rooted at the exact repository and do not broaden
them into `$HOME`, session stores, sibling products, or unrelated workspaces.
Use narrowly targeted local documentation rather than searching user history.

### 3. Trace behavior, not just changed lines

Read enough surrounding production code to reconstruct:

- state ownership and valid transitions;
- async operations and their cancellation tokens;
- resource acquisition/release paths;
- stale callbacks and identity guards;
- error, mute/disable, unmount, retry, and re-entry paths;
- the real caller contract for callbacks and pending data.

Check whether a flag is being used as evidence for a stronger fact than it
actually proves. For example, "awaiting a response" does not necessarily prove
that generation is still busy, playback exists, or a response will ever arrive.

#### Filtered contributors, freshness, and presentation state

When a derived value filters, deduplicates, clamps, or rejects source rows, every
stronger claim about that value—freshness, provenance, sample count, trust, or
status—must be computed from the exact rows that actually contributed. A recent
invalid/NaN/out-of-range row must not refresh an old valid baseline merely because
it has a newer timestamp. Audit duplicate precedence before and after filtering.

Then reconcile the full presentation contract: domain status, helper predicates
such as `usable`, eligibility, returned payload/comparison, and uncertainty labels
must agree. Do not present mature-but-stale data as young/provisional data, and do
not emit a comparison when the domain state says it is unusable. Test the exact
fresh/stale boundary, one step beyond it, no-contributor history, recent rejected
rows, duplicate rows, and calendar transitions. See
`references/filtered-derived-state-and-pr-scope.md`.

For path, mount, credential, authorization, or capability guards, trace every
consumer of the derived value—not only the guarded helper. Inventory receipts,
markers, logs, cleanup, finalizers, child-process environment, and retry paths.
A wrapper can validate a path once, then later recreate or mutate an unsafe
location through a stale cached value even when the core operation revalidates.
Model the transition `valid → unavailable/changed → every subsequent writer`,
and run a temporary-directory reproduction when safe. See
`references/stale-derived-authority.md`.

### 4. Verify with non-mutating checks

Run the narrow behavior tests first, then relevant typecheck, lint, formatting
check, and `git diff --check`. Use check-only formatter modes. Report exactly
which suites and counts passed; do not imply that a requested file ran if the test
runner silently ignored a nonexistent path.

For security and integrity claims, add a minimal adversarial reproduction when it
can run entirely in a temporary directory: exercise symlink inputs, mutable
commitments, tampered manifests, caller-controlled partition keys, or stale
identity tokens directly. Disable bytecode/cache generation and verify the
repository hash manifest is unchanged afterward. A concrete exploit trace is
stronger than a speculative finding and often exposes gaps that happy-path tests
cannot see. See `references/adversarial-security-probes.md`.

### 5. Reconcile tests with the state machine

For every lifecycle fix, enumerate cross-products that tests often miss:

- operation phase × mute/disable/end/unmount;
- before acquisition × during acquisition × after acquisition;
- busy × not busy;
- pending response present × absent;
- active callback × retained stale callback;
- old cancellation token × replacement token.

A test covering the intended happy transition does not cover adjacent stale-state
transitions. Prefer a concrete transition trace over speculative wording.

### 6. Freeze the final snapshot

The worktree may change while review commands run. Immediately before verdict:

```bash
git status --short
git diff HEAD --stat
git diff HEAD --check
git ls-files --others --exclude-standard

# Bash: hash every changed or untracked path, including files ordinary diffs omit.
while IFS= read -r -d '' file; do
  if [[ -e "$file" || -L "$file" ]]; then
    printf '%s  %s\n' "$(git hash-object -- "$file")" "$file"
  else
    printf 'DELETED  %s\n' "$file"
  fi
done < <(
  git diff HEAD --name-only -z
  git ls-files --others --exclude-standard -z
)
```

Compare the path-to-object-id map, not only status/stat output. If any tracked or
untracked file hash changed, re-read that file and rerun impacted checks; earlier
green output is stale evidence for modified code. If the scope is actively
converging, repeat until one complete review/verification pass observes a stable
manifest. Keep the manifest path-qualified: a bare list of object IDs makes it
hard to identify which concurrently edited file invalidated the evidence.

### 7. Emit the verdict

Use the caller's schema. A common fail-closed shape is:

```json
{
  "passed": false,
  "security_concerns": [],
  "logic_errors": ["path:line: concrete defect and reachable transition"],
  "suggestions": ["non-blocking improvement"],
  "summary": "one-sentence grounded verdict"
}
```

Keep blocking defects in `logic_errors`, not `suggestions`. Include file/line,
preconditions, transition sequence, and user-visible consequence. Mention passing
checks in the summary without allowing them to override a proven logic defect.

## Pitfalls

- Reviewing only `git diff` and missing untracked implementation files.
- Running an auto-fix skill despite an explicit no-modification constraint.
- Treating a stale boolean as authoritative resource ownership.
- Relying only on an optional caller cancellation signal when the shared hook
  itself can unmount or cancel during asynchronous acquisition.
- Assuming aborting a promise clears every related lifecycle flag.
- Passing because tests are green while an untested state cross-product wedges.
- Returning a markdown code fence when the consumer requested raw JSON.
- Reusing verification output after the worktree changed mid-review.
- Assuming unchanged `git status`/diff stats mean untracked files are unchanged.
- Broadening a repository-only review into user session stores or unrelated
  workspaces after the caller excluded private data.
- Reporting a plausible attack without running a safe temporary-directory probe
  when the defect is cheaply reproducible.
- Auditing only the named core operation while side-channel writers—receipts,
  completion markers, finalizers, logs, or child-process handoffs—reuse stale
  path or authority decisions.

## References

- `references/filtered-derived-state-and-pr-scope.md` — live PR merge-base
  scoping plus temporal/freshness review of filtered derived state.
- `references/voice-resource-ownership.md` — a concrete lifecycle-audit pattern
  for mute/unmute, async cancellation, stale flags, and microphone ownership.
- `references/adversarial-security-probes.md` — temporary-directory
  counterexamples for path/CAS safety, causal dataset leakage, and frozen
  evaluation integrity without modifying the reviewed repository.
- `references/external-agent-bridges.md` — authority, prompt trust, secret
  isolation, cancellation, trace continuity, and truthful outcome checks for
  adapters that call retrieval or learning services around agent execution.
- `references/stale-derived-authority.md` — production-caller audit and safe
  reproduction pattern for guards whose derived paths or permissions outlive
  the condition that made them valid.
