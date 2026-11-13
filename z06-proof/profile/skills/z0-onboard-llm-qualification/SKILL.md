---
name: z0-onboard-llm-qualification
description: Use when qualifying z0 onboarding code, docs or LLM changes.
---

# z0 onboarding qualification

## Read-only review procedure

1. Read the requested base-to-head diff and related issue, then trace each documentation claim to its parser, planner, executor, verifier or rollback implementation. Do not run onboarding to validate prose; use existing disposable fixtures or in-memory probes instead.
2. Exercise refusal plus off-path failure together through both `report.render()` and `cli.receipt_summary()`. Assert the required stop/continue instruction and the absence of its opposite — adding a correct note does not remove contradictory older guidance. Test output consumers, not just the new helper.
3. Distinguish whole-plan refusal, component refusal, failure and unavailable checks when checking exit semantics. Confirm `verify` re-executes runnable check steps without claiming it rebuilds artifacts, installs dependencies or makes unavailable tiers runnable.
4. Compare golden plans recursively as parsed JSON, allowing only intended ask fields, registry digests and consequent plan hashes. Count every changed fixture; textual inspection alone can miss unrelated structural drift.
5. Inspect check scripts before running them under a read-only constraint. For docs consistency, use the pure functions in `z0.generate` to compare returned strings with committed outputs; `scripts/docs-check` invokes a generator that writes files. Set `PYTHONDONTWRITEBYTECODE=1` for Python review probes.
6. Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=lib python3 -m unittest discover -s tests/onboard -t . -q`, then targeted renderer/consent/golden tests and the safe registry/leak/diff checks. Report passed, failed and skipped counts separately. Establish base behavior before calling a failure pre-existing; unchanged affected files are evidence of scope, not a base execution.
7. Return severity, file:line, evidence and suggested fix for each finding, followed by command results and a one-line verdict. Label claims about another repository's scripts or settings unverified unless that exact source was inspected.

## LLM and runtime qualification

- Read docs/onboarding/DESIGN.md sections 3, 7, 10 and 11 plus the existing kernel before editing. Keep provider classification separate from plan authority; reuse kernel provider/consent verdicts.
- Run `python3 -m unittest tests.onboard.test_llm` and serial `python3 -m unittest discover -s tests -t .`, then `./scripts/public-leak-check`, `./scripts/registry-check` and `git diff --check`. Inspect skipped tests rather than calling skipped proofs executed.
- Test providers with fakes, not real quota-consuming inference. CLI `--help` can validate isolation options without sending a prompt. Keep credentials out of test output.
- Scrub string leaves before JSON serialization; escaping quotes, backslashes or Unicode can otherwise hide registered secrets and identities from literal matching. Test the emitted prompt after parsing its JSON payload.
- For detected Ollama, query `/api/ps` for loaded models, not `/api/tags` for installed models. Selecting a cold installed model can start an unrequested workload. Prove both empty-loaded and already-loaded cases with fake HTTP responses.
- Replay must return unchanged answer records with zero provider discovery/sends and the same plan hash. Freshness re-plans reuse verified records or fall back when evidence changes; never widen grants.
- When adding structured question kinds, update every transport's enforced JSON schema, not only prompt/parser/verifier code. Exercise a fake HTTP transport to inspect the submitted schema; a fake resolver alone can conceal a production schema mismatch.
- Keep contributor tie-break reasons bound to the selected card (tier/difficulty) and profile/task skill or interest intersections. Pass providers a deep copy so an in-process seam cannot mutate verifier facts. Preserve deterministic user-facing cards and record only verified closed answers or fixed failure codes.
- Qualify contributor CLI output against `suggestion.schema.json` for none/local/auto and run the acceptance selector `-k first_task_pick`; tests with unrelated names will not certify E2.
- After an authorized push, compare `git rev-parse HEAD` with `git ls-remote --heads origin <branch>` before reporting delivery. Do not create PRs when the task forbids them.

## Guided UX and deferred consent

- Restrict guided C1 grants by both bundle and step id at PLAN and APPLY; granting one step must not authorize a sibling in the same bundle.
- Treat deferred bundle acceptance as a bounded delta: compare the recorded and fresh typed steps, retain completed outcomes, exclude new/C0/C2/unselected steps and unrelated checks, and probe prior artifacts before allowing dependent effects. Preserve the original journal so one rollback includes accepted deltas.
- Keep `init --dry-run` profile-only and read-only when routing real init installs to onboarding; preserve doctor inventory behaviour and never use its legacy zero exit code as acceptance evidence.
- Validate LaunchAgent XML with plistlib and exercise the fcntl lock wrapper with a real disposable child. Distinguish rendered previews from installed or healthy services; test auto, non-macOS, no-TTY and declined paths for zero preview writes.
- Check the live base for component actions/resolver modules before claiming full-stack onboarding. A green source-publication gate does not prove missing adapters or a clean-machine runtime installation.
