## What does this PR do?

`memory-providers.md` says Hindsight's local embedded mode installs `hindsight-all` on first use through Hermes' lazy-install path. That stopped being true when #128442 moved the catalog pin to vectorize-io/hindsight eb021da3: the plugin no longer calls `tools.lazy_deps` (a stub on main that raises) or depends on `hindsight-all`. At that SHA, `pyproject.toml` declares `hindsight-client>=0.10.1,<1` and `hindsight-embed>=0.10.1,<1`, `embedded.py:_check_local_runtime()` imports only those two, and the server runs as a separate process that `hindsight-embed` starts from an installed `hindsight-api` binary or else via `uvx hindsight-api`, which downloads the server on its first start (`setup.py`). The zh-Hans page still described the bundled-era wizard (`hindsight-all`, auto-upgrading `hindsight-client >= 0.4.22`) and now matches the English page. Docs only.

The open pin bump #129093 (v1.2.1, d56c4ac) declares the same dependencies and starts the server the same way, so this text holds after it lands.

Sources at eb021da3 (`hindsight-integrations/hermes`):

- `pyproject.toml`: `dependencies` lists only those two packages.
- `embedded.py`: the `_check_local_runtime()` docstring says the server runs as a separate process that `hindsight_embed` starts "from an installed `hindsight-api` binary, else a `uvx hindsight-api` fallback"; the comment on `_DAEMON_START_TIMEOUT = 900` says the first start on a machine with no `hindsight-api` binary downloads the server through uvx.
- `setup.py:105`: the setup wizard prints "The Hindsight server runs as a separate process; first use downloads it if needed."

## Related Issue

No issue tracks this. Replaces #127354 (closed), which edited the same sentence to call embedded mode unsupported under PM; #128442 removed the catalog `known_issues` entry that wording relied on.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/user-guide/features/memory-providers.md`: replace the `hindsight-all` lazy-install sentence with the pinned plugin's dependencies (`hindsight-client`, `hindsight-embed`) and how the server starts (an installed `hindsight-api` binary, else `uvx hindsight-api`, which downloads it on first start).
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/features/memory-providers.md`: add `hermes plugins install hindsight` to the 依赖 row and the install block, and replace the bundled-era wizard paragraph with a translation of the English paragraph.

## How to Test

1. On `main`, read `plugin-catalog/hindsight.yaml` (pin `eb021da3b2501911e4b57c82b3de1123572a200e`, set by #128442) and `tools/lazy_deps.py` (`install_specs` raises `ImportError`). The old sentence names an install path the pinned plugin no longer uses.
2. Read the plugin at the pinned SHA eb021da3 (`hindsight-integrations/hermes`): `pyproject.toml` dependencies, `embedded.py` `_check_local_runtime()` and `_DAEMON_START_TIMEOUT`, `setup.py` `_check_mode_dependencies()`. Not tested: actually starting local embedded mode.
3. Python steps of `docs-site-checks.yml`: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` (clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run: `npm run lint:diagrams`, `npm run build:fast`. The changed lines contain no `{}` or raw tags outside code spans.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` — not run; docs-only change, no Python touched
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS) — docs scripts only (see How to Test)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A
