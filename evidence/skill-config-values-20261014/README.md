# Skill-config value rendering: independent evidence

Scope: NousResearch/hermes-agent PR 138412 / issue 138411. Reporter and production-fix author: rodricksz4h5. No production changes or upstream publication by this review.

## Verdict: CLEAN for the scoped rendering invariant
The scoped rendering invariant is supported on source head `a4c4b902dbe4074a138a4ecf158c2830cb510ee9` against exact base `0e427d788d253630d38a3a51cd76849e73cd6925`. Independent critical review passed, including a fresh canonical replay of all 30 contract cases. This is not merge approval or a full-suite claim.

- Independent contract: 30 distinct cases; exact base **14 passed / 16 failed**, head **30 passed / 0 failed**.
- Identical adjacent suite on both revisions: **62 passed** (skill commands 26, skill utils 19, cron skill injection 17).
- Author's own two regression cases: **2 passed on head**, not counted as independent cases.
- Final combined head run: 94 passed; base run omits the author's new file and reports 76 passed / 16 failed.
- Repeated head runs are stability/replay evidence, not additional unique coverage.

## What was exercised
Both actual production renderers are imported without stubs or source extraction: skill invocation goes through `build_skill_invocation_message` into `_inject_skill_config`, and settings through `_show_skill_settings` with real discovery/resolution. Every case writes a temporary skill and config. No LLM, live account or deployment is involved.

Fourteen resolved-value cases per renderer cover configured False, 0 and 0.0; missing, empty string, null config and null default; True, positive number and string zero; empty list and mapping; and False/0 defaults. Two more cases alternate first/second/first named profile scopes using the real context override. The process HOME, HERMES_HOME and Path.home are temporary. No production home/profile is read or mutated.

Missing/empty policy is resolver-sensitive: configured None and blank strings fall back to the declaration default. Without a default they resolve to an empty string. The declaration parser drops an explicit null default, so that case also resolves to an empty string. These end-to-end cases therefore verify empty-value rendering but do not exercise a resolved None reaching the renderer. False/0 defaults remain explicit values. Empty containers and 0.0 also become visible under the authored condition; these are characterized semantics beyond the two headline examples.

## Independent requirement evidence
The committed user guide at `website/docs/user-guide/features/skills.md` (Skill Config Settings, lines 317-333) promises that stored skill settings are shown by config show and their resolved values injected when skills load. `website/docs/developer-guide/creating-skills.md` (Config Settings, lines 186-224) describes non-secret preferences and resolution. This supports faithfully rendering configured False/0 independently of the proposed test. The source issue explicitly says its example is synthetic, not a live deployment incident. Do not claim observed deployment harm or repeat its reversed dry-run fallback example as measured impact.

## Runtime and source qualification
Python 3.14.7+20260901 and uv 0.12.3 pinned PM executables were reused through package-directory symlinks without intentional package/install mutations, with task-local runtime facts/cache/manager/test environment. Both PM builds used the supported `pm.build_env --offline` path. The fresh test environment's editable install points only to this checkout. All installed distributions match exact committed lock versions after PEP 503 normalization. Real imports were verified to resolve inside the tested checkout. Manifest hashes are in provenance.json and match both revisions. Own task disk usage after runs was about 799 MiB, below the 1 GiB budget; shared executable storage was not copied. This reuse was not filesystem-enforced read-only.

All runs used `scripts/run_tests.sh`, one worker, `--file-retries 0`, UTC and the canonical clean environment. The byte-identical independent overlay SHA256 was `594090f41602a0033e4b66d7cefc7139081395e71fb82ef291f34481a2e44e02` on both revisions. Source was switched only when no tests were running, and the editable root remained the same. The checkout was restored to exact head for final verification.

## Reproduce
Use a disposable checkout at either exact source revision and a PM-built Python matching its lock. Copy the adjacent `test_skill_config_value_rendering_contract.py` to `tests/agent/` in that checkout. Set HOME to a disposable directory and HERMES_PYTHON to that checkout's fresh test interpreter, then run:

```
scripts/run_tests.sh tests/agent/test_skill_config_value_rendering_contract.py tests/agent/test_skill_utils.py tests/agent/test_skill_commands.py tests/cron/test_cron_prompt_injection_skill.py --file-retries 0 -j 1 -q --tb=short
```

Head-only author checks add `tests/agent/test_skill_config_falsy_values.py`. The base does not contain that file. Do not substitute bare pytest or reuse an editable installation bound to another checkout.

## Limits and initial setup correction
The first evidence-harness collection attempted the uninstalled legacy `yaml` package, so zero tests ran. The harness was corrected to the repository's real `hermes_yaml` wrapper before either counted base/head comparison. That initial error is preserved separately and is not a candidate failure or pass. An initial provenance lookup hit checkout egg metadata without direct_url.json; qualification subsequently read the fresh environment's installed dist-info and verified its binding directly.

Focused Ruff check and diff-whitespace check passed. No full suite, aggregate scripts/check, live deployment, UI process, other OS, full CLI show_config, or i18n IPC was exercised. CI and current review status are separate from local evidence. No main/default update, force push, upstream action, production repair, or credentials were used.

## Source freshness and external gates
At 2026-10-14 14:32 UTC, source PR 138412 remained open at the exact tested head/base, with no submitted reviews or inline review comments. GitHub reported mergeable=true but mergeable_state=blocked. No check-runs were returned. CI, Docker and Nix workflow runs were completed/action_required, so no successful CI run is asserted. CI example: https://github.com/NousResearch/hermes-agent/actions/runs/38575678265 . Local scoped evidence does not clear those gates or transfer implementation ownership.
