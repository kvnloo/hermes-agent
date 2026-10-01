## What does this PR do?

Corrects four MCP install/connect descriptions that no longer match the code on `main` (checked against `main` at `aeff051a18`). Each row quotes the doc text being replaced and the source that contradicts it.

| # | Doc on main | What it says | What the code does |
|---|---|---|---|
| 1 | `website/docs/user-guide/features/tool-search.md:190-193` | "The same tool also installs, enables and authorizes local MCP servers from the catalog (targets with `mcp: true`), so it is present whether or not you are signed in" | `manage_connections` is registered with `check_fn=lambda: gateway_config.connectors_available()` (`tools/connectors/tool.py:132-146`). `connectors_available()` (`tools/connectors/gateway/config.py:82-106`) returns False unless `tools.connectors.enabled` is on **and** the identity is the Nous free tier (`is_guest_state`) or a Portal token carrying the `managed_tools` claim (`managed_tools_rolled_out`, same file :68-79). Signed-out sessions never see the tool. |
| 2 | `website/docs/user-guide/features/mcp.md:122-123` | "Hermes prompts at install time and writes the value to `~/.hermes/.env`. Non-secret values (base URLs) go to the same file." | `_prompt_env_vars` saves only `spec.secret` values to `.env` (`hermes_cli/mcp_catalog.py:468-495`); `install_entry` inlines every `secret: false` value into the server block (`:794-798`, `_inline_non_secret_value` at `:498`). `hermes mcp install` / the CLI picker (`mcp_picker.py:107`) and the dashboard/Desktop catalog endpoint (`web_routers/mcp.py:561`) call `install_entry`. The chat setup card's non-OAuth install does the same split itself (`tools/connectors/mcp.py:165-171`, `:183`). One path still differs on `main`: the card's OAuth install (`start_install_oauth`, `tools/connectors/mcp.py:124-140`) saves every value to `.env` and keeps the `${VAR}` refs. Both shipped `secret: false` values (n8n-official's server URL, Asana's client ID) belong to OAuth entries, so a chat-card install of either does not match this text until #122780 lands. |
| 3 | `website/docs/user-guide/features/mcp.md:246-261` | "prompts for the Client ID / Client secret, stores them in the profile's `.env`, and writes only `${VAR}` references to `config.yaml`", example shows `client_id: "${ASANA_CLIENT_ID}"` | `optional-mcps/asana/manifest.yaml:28-30` declares `ASANA_CLIENT_ID` with `secret: false` (its own comment: "non-secret values (client id below) are inlined into config.yaml"), so the installed block carries the literal client id; only `client_secret` stays a `${VAR}` ref. |
| 4 | `hermes_cli/plugins_activation.py:40`, `hermes_cli/plugins_loader.py:196`, `plugins/AGENTS.md:70`, `website/docs/developer-guide/plugins/index.md:1585-1587`, `website/docs/developer-guide/gateway-internals.md:310` | a mid-run plugin's `mcp_servers` stay deferred "until `mcp.reload`" | There is no `mcp.reload` (the RPC is `reload.mcp`, `tui_gateway/contracts/tools_mcp_plugins.py:137`; the command is `/reload-mcp`). Install surfaces call `activate_plugin_now` → `load_and_go_live` (`hermes_cli/plugins_activation.py:96-173`), which connects the plugin's MCP servers in place, sets `activation["live_now"] = {"mcp_servers", "skills"}` and drops `mcp_servers` from `deferred` (:161-163). Only a process that did not run it (the messaging gateway's `reload-plugins` verb, `gateway/run_plugin_rewire.py:81-118`) still reports them as deferred; there `/reload-mcp` picks them up because discovery includes portable plugin servers (`tools/mcp_tool_config.py:431`). |

Rows 2-3 trail #117647 (secrets-only `.env` for catalog installs); row 4 trails #119644 (`load_and_go_live`).

Docs and docstrings only; no behaviour change.

Best merged after #122780.

## Related Issue

No upstream issue. Supersedes my earlier PRs #127377 and #127378 (rows 2-3) and #127382 (row 4), which I closed unmerged to combine them here. Row 1 is new. Searched open PRs/issues for `manage_connections`, `non-secret`, `ASANA_CLIENT_ID`, `mcp.reload`, `load_and_go_live`. Related: #122780 (open) makes the chat card's OAuth install use the same secrets-only split. The mcp.md text here matches every install path once it lands. #125130 and #119358 touch other sections of `mcp.md` / `tool-search.md`.

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `website/docs/user-guide/features/tool-search.md`: `manage_connections` is gated like connectors (enabled config + free tier or `managed_tools` claim).
- `website/docs/user-guide/features/mcp.md`: non-secret catalog values are inlined into `config.yaml`; Asana example shows an inlined client id and a `${ASANA_CLIENT_SECRET}` ref.
- `website/docs/developer-guide/plugins/index.md`: adds the "Live in open chats now" (`load_and_go_live`, `live_now`) step; `deferred` keeps tools/prompt, with `mcp_servers` deferred only where `load_and_go_live` did not run.
- `website/docs/developer-guide/gateway-internals.md`, `plugins/AGENTS.md`, docstrings in `hermes_cli/plugins_activation.py` and `hermes_cli/plugins_loader.py`: replace `mcp.reload` with the actual behaviour.

No zh-Hans changes: the zh-Hans `mcp.md`, `plugins/index.md` and `gateway-internals.md` do not contain these passages (no catalog/Asana section, no mid-run plugin-loading section), and there is no zh-Hans `tool-search.md`.

## How to Test

1. Compare each "What it says" quote with `main`, then read the cited source lines.
2. `python3 website/scripts/check_doc_links.py` → `OK: no route-style links in hand-authored docs.`
3. Docstring edits: `python -m py_compile hermes_cli/plugins_activation.py hermes_cli/plugins_loader.py` passes, and `scripts/run_tests.sh tests/gateway/test_late_plugin_rewire.py tests/tui_gateway/test_plugins_manage_late_activation.py -q` → 6 passed (`test_plugins_manage_late_activation.py` asserts `activation.live_now.mcp_servers`, the row 4 behaviour).

Not run: the Docusaurus site build, and no live catalog or plugin install. Rows 1-3 were checked by reading the cited source.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs-only; ran the two plugin-activation test files above, not the full suite.
- [ ] I've added tests for my changes. N/A, docs only.
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
