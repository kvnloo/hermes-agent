## What does this PR do?

Docs-only. Seven statements in the Desktop docs no longer match the code on `main`. Each item below gives the old text, the source that contradicts it, and what the new text says. No behaviour changes. File:line references are to f848940560 and still match current `main`.

#### Desktop plugin SDK: adoption of marker-less copies

- Old: `website/docs/developer-guide/desktop-plugin-sdk.md:1383-1385` says a marker-less `desktop-plugins/<id>/` folder that holds a `plugin.js` "is a standalone plugin you installed by hand and is never overwritten."
- Source: `materializeDesktopHalf()` in `apps/desktop/electron/desktop-plugins-root.ts:221-228` compares such a folder's `plugin.js` with `sameFile()`; if the bytes match it calls `writeDesktopHalfMarker()` in place and adopts the folder (#112450), otherwise it leaves the folder untouched.
- New: keeps "never overwritten" and adds the case of a pre-marker copy of the package's own half, which the next **Rescan** adopts in place. Pinned by `desktop-plugins-root.test.ts` ('adopts an unmarked copy of its own half that a pre-marker install left behind'). Behaviour changed in #121714 (4dc7a23690); docs were not updated.

#### Reasoning Blocks

- Old: `website/docs/user-guide/desktop.md:251` says Reasoning Blocks off "shows answers only".
- Source: `apps/desktop/src/components/assistant-ui/thread/message-parts.tsx:155-158`: the tool feed follows `display.tool_progress`, never `show_reasoning`.
- New: the parenthetical is removed. Pinned by `use-hermes-config.test.ts:70` ('mirrors display.tool_progress independently of show_reasoning'). Behaviour changed in #126479 (8f21606116); docs were not updated.

#### Markdown line breaks

- Old: `website/docs/user-guide/desktop.md:46` says two trailing spaces make a hard line break and an ordinary newline stays a soft break.
- Source: `remarkSoftBreaks()` in `apps/desktop/src/lib/remark-soft-breaks.ts:7-35` splits prose text nodes on newlines into `break` nodes and leaves code, inline code and math alone. It is registered in `REMARK_PLUGINS` (`apps/desktop/src/components/assistant-ui/markdown-text.tsx:104`).
- New: a single newline in prose renders as a line break; code, inline code and math keep their own whitespace. Pinned by `remark-soft-breaks.test.ts` ('turns single newlines in prose into line breaks', 'leaves code and math nodes untouched'). Behaviour changed in #124345 (9b17e80970); docs were not updated.

#### Linux/Wayland: NVIDIA proprietary driver

- Old: `website/docs/user-guide/desktop.md:199` says a local Wayland session always launches with `--ozone-platform=wayland`, and the override sentence names only `desktop.ozone_platform_hint: x11`.
- Source: `apps/desktop/electron/entry.ts:37` sets `nvidiaProprietaryDriver` when `/proc/driver/nvidia/version` exists. `defaultBackend()` in `apps/desktop/electron/wslg-launch.ts:47-53` lets an explicit `x11`/`wayland` hint win and otherwise picks `x11` for that driver, `wayland` for everyone else (#126013). The config hint reaches it as `ELECTRON_OZONE_PLATFORM_HINT` (`hermes_cli/main_desktop.py:1651-1652`).
- New: adds the NVIDIA exception (XWayland by default), and the override sentence now names a hint of `x11` or `wayland`. Pinned by `wslg-launch.test.ts:91` ('defaults the NVIDIA proprietary driver to x11 unless the user chose wayland'). The WSLg paragraph is unaffected: `/proc/driver/nvidia` is absent under WSL. Behaviour changed in #127048 (e050902e7c); docs were not updated.

#### Update all instances order

- Old: `website/docs/user-guide/multi-connection-desktop.md:293-295` says **Update all instances** dispatches `hermes update` to every eligible connection in parallel.
- Source: `updateConnectionsBeforeLocal()` in `apps/desktop/electron/update-order.ts:7-22` runs the non-local connections with `Promise.all`, then the local one. It is used by the `hermes:connections:update-all` IPC handler in `apps/desktop/electron/main.ts`.
- New: remote and SSH connections update first, in parallel, then local once they have settled, with the reason (the local update hands off to an updater that waits for the app to exit). Pinned by `update-order.test.ts` ('a local handoff waits for remote updates that outlive its exit deadline'). Behaviour changed in #105129 (f429fef30c); docs were not updated.

#### Bot Screen display binding

- Old: `website/docs/user-guide/features/bot-screen.md:376-378` names only cua-driver and headed-browser spawns as inheriting the published `DISPLAY`/`XAUTHORITY`/D-Bus env.
- Source: `_make_run_env()` in `tools/environments/local.py:726-740` merges `tools.bot_desktop.runtime.published_env()` while the Bot Desktop runs (#125830) and drops `WAYLAND_DISPLAY`.
- New: also names GUI apps the agent launches from a local `terminal` command while the screen is up. Pinned by `tests/tools/test_local_env_bot_desktop.py` (`test_running_bot_desktop_display_rides_along`); not run here, verified by reading `tools/environments/local.py`. Behaviour changed in #128246 (89dd61a281); docs were not updated.

#### HERMES_DESKTOP_NVIDIA_SWIFTSHADER

- Old: `website/docs/reference/environment-variables.md:588` describes the SwiftShader fallback as applying to driver series with a broken EGL probe (`580.x`), with `1` as the hatch for a future series "not yet in the closed list".
- Source: `apps/desktop/electron/linux-nvidia-egl-fallback.ts:10-24` explains that the driver-major gate was replaced by a behavioural one (#124255). `decideNvidiaEglFallback()` (`:183`) boots with hardware GL and engages the fallback only after a witnessed GPU-process death; the result is sticky per app version and full driver version.
- New: the entry describes the behavioural probe, says it is re-probed after an app or driver update, and makes `1` the hatch for a broken host the probe has not caught. Pinned by `linux-nvidia-egl-fallback.test.ts:61` ('boots with hardware GL on a first launch (no marker): the 580 series is probed, not assumed broken') and `:92` ('a driver update re-probes hardware GL once'). Behaviour changed in #128337 (d9f0a399a0); docs were not updated.

None of the edited passages has a zh-Hans translation (the zh-Hans `environment-variables.md` has no `HERMES_DESKTOP_NVIDIA_SWIFTSHADER` row).

## Related Issue

No open issue tracks these. Supersedes my earlier docs PRs #127359 (Reasoning Blocks) and #127360 (Markdown line breaks), both closed. The behaviour changes these docs now describe came from #121714, #126479, #124345, #127048, #105129, #128246 and #128337.

Related: #128505 adds a 580-series section that still describes the removed driver-major gate; the env-var row here follows the behavioural probe from #128337.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/developer-guide/desktop-plugin-sdk.md`: marker-less folder adoption.
- `website/docs/reference/environment-variables.md`: `HERMES_DESKTOP_NVIDIA_SWIFTSHADER` row.
- `website/docs/user-guide/desktop.md`: Markdown line breaks, Linux/Wayland NVIDIA default, Reasoning Blocks.
- `website/docs/user-guide/features/bot-screen.md`: display-binding consumers.
- `website/docs/user-guide/multi-connection-desktop.md`: Update all instances order.

## How to Test

1. For each item above, read the cited source on `main`. The old text contradicts it; the new text matches.
2. apps/desktop vitest, run on f848940560 (sources identical on this branch, which is docs-only): `electron/update-order.test.ts electron/wslg-launch.test.ts electron/linux-nvidia-egl-fallback.test.ts electron/desktop-plugins-root.test.ts src/lib/remark-soft-breaks.test.ts src/app/session/hooks/use-hermes-config.test.ts` -> 6 files, 57 passed.
3. Ran the docs-site-checks generator/diff step (`python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py`, then `git diff --exit-code -- website/docs website/sidebars.ts website/i18n`: clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run: `npm run lint:diagrams` (no diagrams touched) and `npm run build:fast`. The added lines contain no MDX-sensitive `{}` or raw tags outside code.
5. Python tests were not run; the bot-screen item was checked against source only.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass (not run; docs-only change, targeted vitest files listed above)
- [ ] I've added tests for my changes (N/A, documentation only)
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Based on f848940560; merges cleanly onto main at aeff051a18 (5 files, +15/-8).
