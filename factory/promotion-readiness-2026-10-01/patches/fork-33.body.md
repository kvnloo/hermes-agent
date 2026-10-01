## What does this PR do?

The bundled `security-guidance` plugin scans `write_file` / `patch` / `skill_manage` writes for known-dangerous patterns. It appends a warning in warn mode, and refuses the write under `SECURITY_GUIDANCE_BLOCK=1`. For `skill_manage` it reads `file_path` / `file_content` / `new_string` from the top level of the call args.

`skill_manage` advertises one call shape (`SKILL_MANAGE_SCHEMA`, `"required": ["operations"]`): an `operations[]` array where each op carries its own `file_path` / `file_content` / `new_string`. The flat top-level fields are only accepted for old transcripts and staged-write replay. `skill_manage()` routes to `_skill_manage_batch` and ignores them whenever `operations` is present. So every schema-shaped `skill_manage` write reached the plugin's hooks with nothing to scan. Warn mode added no warning, and block mode let through a skill write that the equivalent `write_file`/`patch` call would refuse.

This PR changes `_scan_args` for `skill_manage`. When the args carry an `operations` list, each op is scanned with the same `(file_path, file_content/new_string)` spec, against the op's own `file_path`, so per-rule path filters such as the `.py` gate still apply. Otherwise (no `operations`, or a non-list value) the existing top-level scan runs; that code path is unchanged.

Known limitation: block mode runs in the agent loop on the raw model args, before `coerce_tool_args`. A JSON-encoded-string `operations` is still not scanned there (nor a bare op object, or a list of JSON-string ops), although dispatch later coerces it into a valid op list and the write goes through. Warn mode sees the coerced args and is covered.

Scope note: the set of scanned keys is unchanged. `content` (create / full SKILL.md rewrite) was not scanned in the flat shape before and is not scanned per-op now. Whether SKILL.md bodies should be scanned is a separate false-positive policy question.

## Related Issue

No upstream issue. Searched open/closed PRs and issues for security-guidance + `skill_manage`/`operations`. Open security-guidance PRs (#126746 V4A patch paths, #116113 bounded windows, #124576 JS filters, #64235 block-by-default, #33186 severity tiers) don't touch the `skill_manage` `operations[]` shape. #126746 and #116113 edit the same `_scan_args` lines; expect a small rebase whichever lands second.

The bug was first flagged by the Detail automated scanner on my fork. This is a narrower rebuild of that fix on current main (per-op `content` scanning left out, see Scope note).

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `plugins/security-guidance/__init__.py`: `_scan_args` iterates `operations[]` for `skill_manage` (each op scanned like the flat shape against its own `file_path`). Otherwise it falls back to the top-level args.
- `tests/plugins/test_security_guidance_plugin.py`: two behaviour tests, using the same benign marker strings as the existing `write_file` / `patch` tests (`pickle.loads(b)`, `eval(user_input)`):
  - warn mode: an `operations[]` `write_file` op to `scripts/load.py` containing `pickle.loads` gets the `pickle_deserialization` warning;
  - block mode: an `operations[]` `patch` op on `scripts/run.py` whose `new_string` contains `eval(` is refused with `eval_injection`.

## How to Test

1. `scripts/run_tests.sh tests/plugins/test_security_guidance_plugin.py -q`
2. On `main` without the fix, both new tests fail. The hooks return `None` (`assert isinstance(None, str)` / `assert isinstance(None, dict)`): 19 passed, 2 failed.
3. With the fix: 21 passed. Adjacent: `tests/plugins/test_security_guidance_plugin.py tests/plugins/test_transform_tool_result_hook.py tests/tools/test_skill_manager_tool.py` give 97 passed.

Not tested: hooks were called directly. No run through the agent-loop dispatch (`agent/tool_executor` -> `model_tools.handle_function_call`). The legacy flat `skill_manage` shape has no test on main or here; its fallback is unchanged code.

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

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
