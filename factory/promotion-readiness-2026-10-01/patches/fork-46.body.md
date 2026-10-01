## What does this PR do?

Makes the dashboard chat show its "Please wait while the conversation loads…" notice when the server resumes a session without a `?resume=` param in the URL.

When a `/chat` socket connects without `?resume=`, `pty_ws` can fall back to the channel's active-session file and send a `{"type":"resume","id":…}` control frame before the replay starts (added in #93659 for #93518). `ChatPage` handles that frame with `beginResumeReplay()`, which sets `resumeHydrating`. When no keep-alive PTY is left to reattach, the server spawns a fresh `--resume` PTY that boots just as blank as an explicit resume. The render gate still passed `hasResumeTarget: Boolean(resumeParam)`, though, so on this path the notice never appeared. One way to hit it is reconnecting after the keep-alive PTY was reaped. The user just saw an empty terminal with a blinking cursor until the first PTY byte arrived.

`resumeHydrating` is only set when a resume target exists, either from the URL param or from the control frame. The extra URL-param check therefore protected nothing; all it did was hide the notice on the implicit path. This PR removes `hasResumeTarget` and gates the notice on `hydrating` alone. The reconnect, closed and ended overlays still take precedence. `pty_ws` sends the frame before it decides whether to reattach or spawn. So on an implicit reattach to a keep-alive PTY that is still running, the notice now also shows briefly until the buffered replay or forced redraw arrives. An explicit `?resume=` reattach already behaves this way, and the 30 s `PTY_RESUME_LOADING_MAX_MS` cap still applies.

The gate change was first proposed by detail-app[bot] in kvnloo/hermes-agent#46. This version is rebuilt on main without that branch's unrelated kanban files and replaces its helper-only test with a `ChatPage` integration test.

## Related Issue

Refs #93518. Follow-up to #93659, which added the implicit-resume control frame and started `resumeHydrating` from it, but left the render gate on the URL param.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `web/src/lib/pty-resume-loading.ts`: removed `hasResumeTarget` from `ResumeLoadingOverlayInput`. `shouldShowResumeLoadingOverlay` now returns `false` only when not hydrating, or when the reconnect/closed/ended states apply.
- `web/src/pages/ChatPage.tsx`: the call site no longer passes `Boolean(resumeParam)`.
- `web/src/lib/pty-resume-loading.test.ts`: removed the field from the existing cases and dropped the "hides when there is no resume target" case, which asserted the buggy behaviour.
- `web/src/pages/ChatPage.test.tsx`: a new test uses the real `ChatPage` with the existing `FakeWebSocket` harness. A fresh `/chat` shows no notice, the `{"type":"resume"}` text frame shows it, and the first binary PTY chunk hides it.

## How to Test

1. `cd web && npx vitest run src/pages/ChatPage.test.tsx src/lib/pty-resume-loading.test.ts src/lib/pty-scroll.test.ts src/lib/pty-resume-sanitizer.test.ts src/lib/pty-reconnect.test.ts`: 5 files, 73 tests pass.
2. On `main` at f848940560 (the branch base; the touched files are unchanged on main since) without the fix, the new ChatPage test fails right after the control frame: `AssertionError: expected null not to be null` (the notice is missing). The fresh-chat precondition passes.
3. Negative control: with the fix applied, changing the call site to `hydrating: resumeHydrating && Boolean(resumeParam)` makes the new test fail again with the same assertion.
4. `npx tsc -p tsconfig.app.json --noEmit` is clean. `npx eslint` on the changed files reports 0 errors; the 3 warnings are on untouched lines and also appear on `main`.
5. Not tested: a live browser session (jsdom only) and the full web vitest suite. No Python files changed, so pytest was not run.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass (N/A: web-only change. I ran the targeted web vitest files above, not the full suite)
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

N/A
