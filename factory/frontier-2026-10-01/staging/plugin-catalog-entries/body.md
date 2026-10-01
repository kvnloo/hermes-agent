## What does this PR do?

Adds a catalog entry for **paw-pii**, a standalone plugin that finds and redacts personal data on the device before a request reaches the model provider. Detection runs a ProgramAsWeights PII program locally through llama.cpp. The model and the `paw_pii` library come from programasweights/pii. I wrote the Hermes integration and own the plugin repository (kvnloo/pii). The entry pins `<new-sha>`, subdir `integrations/hermes`.

It replaces the closed `plugin_index.json` seed (#102924). That file has since been removed in favour of `plugin-catalog/`.

How it differs from the PII work already here:

- `desensitize` (in the catalog) is aimed at Chinese-language chats. It uses reversible placeholders, hooks, a regex fallback and an optional LLM layer. paw-pii does one-way placeholder redaction with a single local model program. It is wired as `llm_request` and `tool_execution` middleware, and it also adds `detect_pii` and `redact_pii` tools.
- `privacy-gateway` (#129692, open) uses Presidio and an encrypted alias vault. paw-pii uses a compiled local model and needs no vault and no env var.
- #63917 (open) adds regex anonymization to core behind `privacy.*` config. paw-pii stays out of core as a plugin.

#95186 (open) is related but is not a redactor. It would let the host fail closed when a required privacy middleware is unavailable. paw-pii is one plugin that contract would cover, so the two complement each other.

If you'd rather list only one local PII plugin, or want a different key (`paw-pii` is also the programasweights package name), I'm happy to rename it or close this.

## Related Issue

Refs #102922

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [x] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [ ] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `plugin-catalog/paw-pii.yaml`: a new entry pinned to `<new-sha>` in kvnloo/pii, subdir `integrations/hermes`.
  - The capabilities match what `register()` wires at that commit and what the plugin's own `plugin.yaml` declares: tools `detect_pii` and `redact_pii`, and middleware `llm_request` and `tool_execution`.
  - The description discloses what happens on first use. The program downloads from programasweights.com and a base model (`<size measured at first use>`) downloads from Hugging Face. After that, inference is local.
  - The description also states what happens when the model cannot load (`<behaviour at the new pin>`) and that each string is scanned separately, which adds local inference time per turn.

## How to Test

1. `python3 scripts/validate_plugin_catalog.py plugin-catalog/`
2. `hermes plugins validate --install-deps <clone of kvnloo/pii at <new-sha>>/integrations/hermes`
3. `scripts/run_tests.sh tests/hermes_cli/test_plugin_catalog.py tests/scripts/test_validate_plugin_catalog.py tests/website/test_extract_plugins.py`

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate. No other PR adds paw-pii; the closest related privacy PRs are listed above.
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Not the full suite: I ran the catalog, validator and docs-extractor tests, and `<N of M pass>` (log below).
- [ ] I've added tests for my changes (required for bug fixes, strongly encouraged for features). This is a data-only entry. The existing `test_shipped_catalog_entries_are_all_valid_and_pinned` covers it.
- [x] I've tested on my platform: Linux (x86_64)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A. N/A: the plugins page is generated from the entry.
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [ ] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A. The plugin has only been run on Linux. `<platforms line at the new pin>`
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A. N/A: no Hermes tool changes. The plugin's tool schemas live in its own repo.

## Screenshots / Logs

```
$ python3 scripts/validate_plugin_catalog.py plugin-catalog/
<output at <new-sha>>

$ hermes plugins validate --install-deps <clone>/integrations/hermes
<output at <new-sha>>

$ scripts/run_tests.sh tests/hermes_cli/test_plugin_catalog.py tests/scripts/test_validate_plugin_catalog.py tests/website/test_extract_plugins.py
<summary line>
```

AI assistance: Claude Code drafted the catalog entry and this description, and ran the checks listed above.
