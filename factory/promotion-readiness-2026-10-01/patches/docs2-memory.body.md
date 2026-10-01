## What does this PR do?

`memory-providers.md` says Hindsight's local embedded mode installs `hindsight-all` on first use through Hermes' lazy-install path, which honours `security.allow_lazy_installs`. That stopped being true when #128442 moved the catalog pin to vectorize-io/hindsight eb021da3. The plugin at that pin no longer calls `tools.lazy_deps` (on main a stub that raises) and no longer depends on `hindsight-all`. At that SHA:

- `pyproject.toml` declares only `hindsight-client>=0.10.1,<1` and `hindsight-embed>=0.10.1,<1`. Both are installed with the plugin.
- `embedded.py:_check_local_runtime()` imports only those two.
- The server runs as a separate process that `hindsight-embed` starts. It uses an installed `hindsight-api` binary if there is one, and otherwise runs `uvx hindsight-api`, which downloads the server the first time it starts.

The English paragraph now says this: local embedded mode installs nothing into Hermes' environment on first use, its two in-process packages come with the plugin, and the server may be downloaded through uvx on first start. The zh-Hans page still described the bundled-era wizard (`hindsight-all` for local mode, auto-upgrading `hindsight-client >= 0.4.22`). Its install text now matches the English page. Docs only.

The open pin bump #129093 (v1.2.1, d56c4ac) declares the same dependencies and starts the server the same way, so this text still holds after it lands.

Sources at eb021da3:

- `hindsight-integrations/hermes/pyproject.toml`: `dependencies` lists only those two packages. A comment says they are installed into the Hermes venv by `hermes plugins install` / `enable`.
- `hindsight-integrations/hermes/embedded.py`: the `_check_local_runtime()` docstring says the server runs as a separate process that `hindsight_embed` starts "from an installed `hindsight-api` binary, else a `uvx hindsight-api` fallback". The comment on `_DAEMON_START_TIMEOUT = 900` says that the first start on a machine with no `hindsight-api` binary downloads the server through uvx.
- `hindsight-integrations/hermes/setup.py:105`: the setup wizard prints "The Hindsight server runs as a separate process; first use downloads it if needed."
- `hindsight-embed/hindsight_embed/daemon_embed_manager.py` `_find_api_command()`: it uses an installed `hindsight-api` entry point, else falls back to `["uvx", f"hindsight-api@{api_version}"]`.

## Related Issue

No issue tracks this. Replaces #127354 (closed), which edited the same sentence to call embedded mode unsupported under PM. That wording relied on the catalog `known_issues` entry that #128442 removed.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/user-guide/features/memory-providers.md`: replace the `hindsight-all` lazy-install sentence. The new text says that local embedded mode installs nothing into Hermes' environment on first use, that its in-process packages (`hindsight-client`, `hindsight-embed`) are the plugin's declared dependencies and are installed with the plugin, and that `hindsight-embed` starts the server from an installed `hindsight-api` binary or otherwise through `uvx hindsight-api`, which downloads it on first start.
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/features/memory-providers.md`: add `hermes plugins install hindsight` to the 依赖 row and the install block, and replace the bundled-era wizard paragraph with a translation of the English paragraph.

## How to Test

1. Check out `ready/docs2-memory-v2` (one commit on `main` @ 330d9d6d). On `main`, `plugin-catalog/hindsight.yaml` pins `eb021da3b2501911e4b57c82b3de1123572a200e` (set by #128442), and `tools/lazy_deps.py` `install_specs()` raises `ImportError`. The old sentence describes an install path that the pinned plugin no longer uses.
2. Read the plugin at eb021da3 and compare it with the new sentences: `hindsight-integrations/hermes/pyproject.toml` dependencies, `embedded.py` `_check_local_runtime()` and `_DAEMON_START_TIMEOUT`, `setup.py` `_check_mode_dependencies()`, and `hindsight-embed/hindsight_embed/daemon_embed_manager.py` `_find_api_command()`. The same files at d56c4ac (#129093) say the same. Not tested: actually starting local embedded mode.
3. Steps from `docs-site-checks.yml`, run on the branch:
   - `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py`, then `git diff --exit-code --stat -- website/docs website/sidebars.ts website/i18n`: clean.
   - `python3 website/scripts/check_doc_links.py`: `OK: no route-style links in hand-authored docs.`
   - `ascii-guard lint --exclude-code-blocks docs` (ascii-guard 2.3.0, the `npm run lint:diagrams` command), run in `website/`: 457 files, 0 errors.
4. Not run: `npm run build:fast`. The changed lines have no `{}` or raw tags outside code spans.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q`: not run. This is a docs-only change and no Python was touched.
- [ ] I've added tests for my changes: N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS). Only the docs scripts were run (see How to Test).

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A
