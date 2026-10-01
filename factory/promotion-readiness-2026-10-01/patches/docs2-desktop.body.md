## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs(desktop): cover marker-less copies of a package's own desktop half

- **Was:** website/docs/developer-guide/desktop-plugin-sdk.md:1383-1385 — "while a marker-less folder that *does* hold a `plugin.js` is a standalone plugin you installed by hand and is never overwritten."
- **Source on main:** apps/desktop/electron/desktop-plugins-root.ts:208-229 materializeDesktopHalf(): a marker-less target with plugin.js is compared via sameFile() (:222); equal bytes -> writeDesktopHalfMarker() in place and return target (adoption, #112450); different -> left untouched.
- **Check:** Doc says such folders are always the user's; source adopts byte-identical pre-marker copies.
- **Now:** Corrected clause keeps 'never overwritten' and adds the in-place adoption case. vitest electron/desktop-plugins-root.test.ts 'adopts an unmarked copy of its own half that a pre-marker install left behind' passes on main.
- **Mirrors:** No zh-Hans copy of desktop-plugin-sdk.md.
- Drift introduced by 4dc7a23690 (#121714).

### docs(desktop): drop stale "off shows answers only" claim for Reasoning Blocks

- **Was:** website/docs/user-guide/desktop.md:251 — "shows or hides the model's thinking in the transcript (off shows answers only)."
- **Source on main:** apps/desktop/src/components/assistant-ui/thread/message-parts.tsx:154-158 'The tool feed ... follows display.tool_progress, never show_reasoning'; use-hermes-config.test.ts:70 'mirrors display.tool_progress independently of show_reasoning'.
- **Check:** Parenthetical promises an answers-only transcript; tool feed remains.
- **Now:** Parenthetical removed. vitest use-hermes-config.test.ts passes on main.
- **Mirrors:** No zh-Hans desktop.md.
- Drift introduced by 8f21606116 (#126479).

### docs(desktop): correct markdown line-break behavior to match soft-breaks plugin

- **Was:** website/docs/user-guide/desktop.md:46 — "**Markdown line breaks** follow Markdown semantics: two trailing spaces create a hard line break; an ordinary newline stays a soft break."
- **Source on main:** apps/desktop/src/lib/remark-soft-breaks.ts:7-35 (text nodes split on newlines into break nodes; code/inline code/math untouched); applied in markdown-text.tsx:104 REMARK_PLUGINS. Commit 9b17e80970 postdates the doc line (blame 55ad5afa12, an ancestor).
- **Check:** Doc describes behaviour the renderer overrides.
- **Now:** Bullet rewritten to the soft-breaks behaviour. vitest src/lib/remark-soft-breaks.test.ts passes on main.
- **Mirrors:** No zh-Hans desktop.md.
- Drift introduced by 9b17e80970 (#124345).

### docs: cover NVIDIA proprietary driver defaulting to XWayland on Linux

- **Was:** website/docs/user-guide/desktop.md:199 — "On a local Wayland session ... Hermes launches with `--ozone-platform=wayland` so Electron does not fall back to XWayland."
- **Source on main:** apps/desktop/electron/entry.ts:37 nvidiaProprietaryDriver = linux && existsSync('/proc/driver/nvidia/version'); wslg-launch.ts:43-53 defaultBackend(): explicit x11/wayland hint wins, else nvidiaProprietaryDriver ? 'x11' : 'wayland' (#126013). desktop.ozone_platform_hint reaches it as ELECTRON_OZONE_PLATFORM_HINT (hermes_cli/main_desktop.py:1651-1652).
- **Check:** Doc states wayland unconditionally.
- **Now:** NVIDIA exception added; override sentence now lists a hint of x11 or wayland. vitest wslg-launch.test.ts 'defaults the NVIDIA proprietary driver to x11 unless the user chose wayland' passes on main.
- **Mirrors:** No zh-Hans desktop.md; the WSLg paragraph is unaffected (no /proc/driver/nvidia under WSL dxg).
- Drift introduced by e050902e7c (#127048).

### docs: correct Update all instances dispatch order to remote-then-local

- **Was:** website/docs/user-guide/multi-connection-desktop.md:293-295 — "dispatches `hermes update` to every eligible connection in parallel:"
- **Source on main:** apps/desktop/electron/update-order.ts:7-22 updateConnectionsBeforeLocal(): Promise.all(non-local) then Promise.all(local); used by the connections:update-all handler, main.ts:16776-16779.
- **Check:** Doc says fully parallel.
- **Now:** Doc states remote/SSH first (parallel), then local, with the reason. vitest electron/update-order.test.ts passes on main.
- **Mirrors:** No zh-Hans multi-connection-desktop.md.
- Drift introduced by f429fef30c (#105129).

### docs(bot-screen): include terminal GUI launches in display-binding consumers

- **Was:** website/docs/user-guide/features/bot-screen.md:376-378 — "every cua-driver and headed-browser spawn for that profile inherits them"
- **Source on main:** tools/environments/local.py:725-740 _make_run_env(): merges tools.bot_desktop.runtime.published_env() while the desktop runs (#125830) and drops WAYLAND_DISPLAY.
- **Check:** Consumer list omits terminal GUI launches.
- **Now:** Bullet adds GUI apps launched from a local terminal command.
- **Mirrors:** No zh-Hans bot-screen.md.
- Drift introduced by 89dd61a281 (#128246).

### docs: correct NVIDIA SwiftShader fallback to behavioral probe, not 580.x series

- **Was:** website/docs/reference/environment-variables.md:588 — "routes rendering through SwiftShader on driver series with a broken EGL probe (`580.x`, #40077): `1` forces the fallback on — the recovery hatch if a future series reintroduces the crash but is not yet in the closed list"
- **Source on main:** apps/desktop/electron/linux-nvidia-egl-fallback.ts:10-24 ('The gate used to be a driver-major set ... So the gate is now behavioral (#124255)'), decideNvidiaEglFallback() :183-260 (override, sticky fallback marker per app+driver version, booting-marker engage).
- **Check:** Doc describes the removed driver-major list.
- **Now:** Entry describes the behavioural probe. vitest linux-nvidia-egl-fallback.test.ts ('the 580 series is probed, not assumed broken', 'a driver update re-probes hardware GL once') passes on main.
- **Mirrors:** No zh-Hans copy of this variable.
- Drift introduced by d9f0a399a0 (#128337).

## Related Issue

Supersedes our own parked docs PRs #127359, #127360 (closed to keep the review queue short); no open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/developer-guide/desktop-plugin-sdk.md`
- `website/docs/reference/environment-variables.md`
- `website/docs/user-guide/desktop.md`
- `website/docs/user-guide/features/bot-screen.md`
- `website/docs/user-guide/multi-connection-desktop.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: apps/desktop vitest: electron/update-order.test.ts electron/wslg-launch.test.ts electron/linux-nvidia-egl-fallback.test.ts electron/desktop-plugins-root.test.ts src/lib/remark-soft-breaks.test.ts src/app/session/hooks/use-hermes-config.test.ts -> 6 files, 57 passed.
3. Docs CI equivalent: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` (clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run here: the Docusaurus build (`npm run build:fast`); added lines contain no MDX-sensitive `{}`/raw tags outside code.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass — targeted files only (listed above); docs-only change
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-desktop` @ 58f1374abe9b, 5 files changed, 15 insertions(+), 8 deletions(-).
