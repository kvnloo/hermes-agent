## What does this PR do?

The bundled `security-guidance` plugin scans `write_file` / `patch` / `skill_manage` writes for known-dangerous patterns. It appends a warning in warn mode, and refuses the write under `SECURITY_GUIDANCE_BLOCK=1`. For `skill_manage` it reads `file_path` / `file_content` / `new_string` from the top level of the call args.

`skill_manage` advertises one call shape (`SKILL_MANAGE_SCHEMA`, `"required": ["operations"]`): an `operations[]` array where each op carries its own `file_path` / `file_content` / `new_string`. The flat top-level fields are only accepted for old transcripts and staged-write replay. `skill_manage()` routes to `_skill_manage_batch` and ignores them whenever `operations` is present. So every schema-shaped `skill_manage` write reached the plugin's hooks with nothing to scan. Warn mode added no warning, and block mode let through a skill write that the equivalent `write_file`/`patch` call would refuse.

This PR changes `_scan_args` for `skill_manage`. When the args carry an `operations` list, each op is scanned with the same `(file_path, file_content/new_string)` spec, against the op's own `file_path`, so per-rule path filters such as the `.py` gate still apply. Without `operations`, the existing top-level scan runs unchanged.

Block mode needs one more step. In the agent loop, `pre_tool_call` gets the raw model args (`agent/tool_executor._parse_tool_arguments` → `_pre_tool_block`). `coerce_tool_args` runs later, in `model_tools.handle_function_call`. It repairs three `operations` shapes into a valid op list: a JSON-encoded string, a bare op object, and a list of JSON-string ops. Each of them then passes `_validate_batch_ops` and the write goes ahead. Before coercion, the hook would find nothing to scan in any of them. `_scan_args` now normalises these shapes the same way first: it `json.loads` a string `operations` and string ops, and wraps a bare op object in a list. Warn mode (`transform_tool_result`) already gets the coerced args, and the normalisation is a no-op there.

Scope note: the set of scanned keys is unchanged. `content` (create / full SKILL.md rewrite) was not scanned in the flat shape before and is not scanned per-op now. Whether SKILL.md bodies should be scanned is a separate false-positive policy question.

## Related Issue

No upstream issue. Searched open/closed PRs and issues for security-guidance + `skill_manage`/`operations`, and for `pre_tool_call` + argument coercion. Open security-guidance PRs (#126746 V4A patch paths, #116113 bounded windows, #124576 JS filters, #64235 block-by-default, #33186 severity tiers) don't touch the `skill_manage` `operations[]` shape. #126746 and #116113 edit the same `_scan_args` lines; expect a small rebase whichever lands second.

The bug was first flagged by the Detail automated scanner on my fork. This is a narrower rebuild of that fix on current main (per-op `content` scanning left out, see Scope note), and the commit credits detail-app[bot] as co-author.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

One commit on `main` @ `330d9d6df9` (branch `ready/fork-33-security-guidance-skill-ops-v2`), +54/−2:

- `plugins/security-guidance/__init__.py`: `_scan_args` iterates `operations[]` for `skill_manage`, scanning each op like the flat shape against its own `file_path`. Before that, a small `_json_or_raw` helper normalises the raw shapes that dispatch would coerce (JSON-string list, bare op object, JSON-string ops). If no op list comes out of that, it falls back to the top-level args.
- `tests/plugins/test_security_guidance_plugin.py`: two behaviour tests. They use the same benign marker strings as the existing `write_file` / `patch` tests (`pickle.loads(b)`, `eval(user_input)`):
  - warn mode: an `operations[]` `write_file` op to `scripts/load.py` containing `pickle.loads` gets the `pickle_deserialization` warning;
  - block mode, parametrized over the native list and the three raw shapes (`list`, `json_string`, `bare_op`, `json_string_ops`): a `patch` op on `scripts/run.py` whose `new_string` contains `eval(` is refused with `eval_injection`.

## How to Test

1. `scripts/run_tests.sh tests/plugins/test_security_guidance_plugin.py -q`
2. On `main` without the fix, all 5 new test cases fail because the hooks return `None` (`assert isinstance(result, str)` / `assert isinstance(out, dict)`): 19 passed, 5 failed.
3. With the fix: 24 passed. Each normalisation step is needed: drop the bare-op wrap, the string-`operations` decode or the string-op decode, and the `bare_op`, `json_string` or `json_string_ops` case fails, respectively.
4. Adjacent: `tests/plugins/test_security_guidance_plugin.py tests/plugins/test_transform_tool_result_hook.py tests/tools/test_skill_manager_tool.py` → 100 passed. `ruff check` is clean on both touched files.

I also checked by hand, outside the test suite, that the real `coerce_tool_args("skill_manage", ...)` turns each of the three raw shapes into `[op]` and that the result passes `_validate_batch_ops`. A JSON string holding a single object is not coerced into a valid list (dispatch rejects it), and `_scan_args` doesn't treat it as one either.

Not tested: the tests call the hooks directly. They don't go through the full agent-loop dispatch (`agent/tool_executor` -> `model_tools.handle_function_call`). The legacy flat `skill_manage` shape has no test on main or here. Its fallback path is unchanged.

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
