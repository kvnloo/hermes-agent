---
name: light-browser-routing
description: Use when picking a browser engine for agent tests.
version: 1.0.0
metadata:
  hermes:
    tags: [browser, testing, lightpanda, agent-browser, performance]
---

# Light browser routing

Route DOM/JS checks to Lightpanda and rendering checks to chrome-headless-shell; keep full Chrome only where it is needed. The owner finds full Chrome heavy and slow. Measured on the Quackles pages (5 repeats, frozen build, 2026-10-15; evidence in project-artifacts/quackles/process/site-2026-10-15/lanes/light-browser/REPORT.md):

| Engine | Whole-tree RSS | Run |
|---|---:|---:|
| Chromium + Playwright (old default) | ~1,054 MiB | 1.54 s |
| chrome-headless-shell + Playwright | ~614 MiB | 1.05 s |
| Lightpanda raw CDP | ~108 MiB | 0.49 s |
| agent-browser --engine lightpanda | ~119 MiB | 0.50 s |
| agent-browser default (Chrome) | ~1,684 MiB | 1.58 s |

## Routing

1. DOM/JS-only checks (filters, events, links, text, a11y tree, agent text navigation): Lightpanda. Via `agent-browser --engine lightpanda` or Playwright `connectOverCDP` to `lightpanda serve`.
2. Anything that depends on rendering: layout/visibility, real pointer hit-testing, screenshots, image decode, Lighthouse, Chrome traces/frame timing: chrome-headless-shell (Playwright `executablePath`). Lighthouse works with it.
3. WebGL/WebGPU, vault/login flows, visual acceptance: the full browser tool / Kevin's Chrome or Zen.
4. 120 Hz feel: a real phone. Emulation is not proof.

Escalate to the next tier the moment a check needs geometry, pixels or an unsupported API. Never claim a visual or perf pass from Lightpanda: its screenshots are text-only and its geometry is synthetic. Playwright pointer clicks fail viewport checks on Lightpanda; use DOM clicks or agent-browser refs.

- Serve local-file review artifacts through an owned temporary loopback HTTP server for Lightpanda structure checks; file URLs can fail with UnsupportedProtocol. Bind port 0, capture the actual port, close the CLI session and server in finally, then use the original file URL for headless-shell visual checks.
- Before full-page screenshots of a lazy-image review gallery, make images eager, await each element's decode, scroll each major section into view and allow two animation frames before returning to the top. naturalWidth/complete or decoding separate Image objects alone can pass while offscreen images remain unpainted in the screenshot. Inspect a lower-page crop visually.
- Pass a function expression, not a bare expression string, to Playwright wait_for_function on strict-CSP pages. Its string-evaluation path can trip unsafe-eval even when ordinary page.evaluate works; do not weaken the page CSP to fix the test.
- Audit every LOOK and CLEAR thumbnail URL, including variants hidden in collapsed portfolios, rather than only the initially visible image src values. Keep absent render modes explicit; never reuse LOOK as CLEAR.

## Installed (user space)

- `~/.local/bin/lightpanda` 1.0.1 (`lightpanda serve --host 127.0.0.1 --port <p>`)
- `~/.local/bin/agent-browser` 0.39.1 (Rust CLI + daemon). It is an agent interface, not a lighter engine: its default still launches Chrome for Testing (~/.agent-browser/browsers). Always pass `--engine lightpanda` for the light path.
- chrome-headless-shell: `~/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell`

## Quick use

```sh
agent-browser --engine lightpanda open http://127.0.0.1:43219/learn/
agent-browser snapshot        # a11y tree with @refs; `snapshot -i` may be empty right after open
agent-browser click @e3
agent-browser close           # always close; the daemon keeps lightpanda running otherwise
```

The Quackles repo pilot lives on branch chore/light-browser-tests (learning explorer check: 0.12 s / 98 MiB vs 1.03 s / 1,053 MiB, same red/green result as Chromium).
