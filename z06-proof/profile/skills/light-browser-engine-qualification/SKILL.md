---
name: light-browser-engine-qualification
description: "Use when benchmarking lightweight agent browser engines."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [browser, benchmarking, testing, evidence]
    related_skills: [agentic-gitops-integration, spike]
---

# Lightweight agent browser qualification

## When to Use

Use for measured comparisons of lightweight engines, agent navigation interfaces, and renderer-versus-DOM routing policies.

Compare actual browser engines separately from agent interfaces. agent-browser defaults to Chrome; current releases also have Lightpanda and experimental Obscura adapters. Verify current primary docs rather than assuming the CLI itself replaces Chrome.

## Evidence procedure

1. Freeze a real static build before timing. A shared preview can be rebuilt by another lane mid-run. Copy it to an owned evidence directory, hash every file, serve it on an owned ephemeral loopback port, and verify hashes afterward. Never pool moving-preview preliminaries into the final cohort.
2. Pin package and engine versions and preserve executable hashes. Use scratch/user-space installations only when that is the task scope. Record CPU count and `/proc/loadavg` for each repetition; do not stop unrelated jobs to improve results.
3. Run at least five fresh-process repetitions per candidate with rotated order. Separate engine-ready time, navigation/DOM time, native snapshot time, total run time and capability probes. State whether the readiness cutoff is DOMContentLoaded, network-idle, hydration, or image decode. Process-cold is not disk-cold.
4. Measure the complete owned process tree, not just Chrome's parent. A Linux subreaper catches detached agent daemons; sum sampled RSS for all descendants and use wait4 CPU accounting for reaped roots/adopted children. Do not double-count waited descendants. RSS is not PSS, and sampled peaks are lower bounds. Exclude the shared HTTP server and monitor consistently. Preserve individual trials and ranges, not only medians.
5. Identify the real browser from its returned user agent and command line. Lighthouse may ignore a presumed `--chrome-path`; use `CHROME_PATH` and verify `environment.hostUserAgent` in its output. Different Chrome builds/launch flags make a setup comparison, not a pure interface-overhead experiment.
6. Probe DOM, real JS/fetch, pointer and DOM clicks separately, snapshots, geometry, screenshots, tracing and GPU context/adapter availability. Lightpanda can return PNGs and bounding boxes without real layout: inspect the image and reject text-only screenshots or synthetic geometry as visual evidence. Playwright `locator.click()` over Lightpanda can fail viewport checks even when raw DOM click works; do not fix visual gates with `force: true`.
7. Port one explicit DOM-only assertion slice. Run identical assertions through the original rendering path and the light engine. Remove a real event handler in an owned response proxy as a seeded failure; require the same failing assertion, then healthy green repeats. Leave existing rendering/keyboard/performance checks intact.
8. Compare snapshot tokens on the exact active target URL, not `context.pages()[0]`; CDP attachment can reveal stale or unmanaged tabs. Save raw text and specify tokenizer. Raw AX JSON is not equivalent to a tool's filtered page-info output or total model-loop tokens.
9. Preserve scripts, lockfile, manifests, logs, screenshots and trace files outside the source tree; commit only scoped pilot/docs on the leased branch. Stop only owned processes and release the cooperative lease after sealing READY.

## Compatibility pitfalls

- On Arch, Playwright's Ubuntu WebKit bundle may require ICU 74 and flite. Extract official distro packages into scratch rather than changing system libraries. Its MiniBrowser wrapper may overwrite LD_LIBRARY_PATH; scratch-only library links inside the bundle can satisfy its loader. Record this workaround and initial failures.
- Lightpanda `serve --port 0` announces the actual ephemeral port in stderr. Parse the owned readiness message rather than probe-and-release a port and accidentally attach to another listener. Disable telemetry/core dumps for private local fixtures when supported.
- Missing executable cleanup must check `child.pid` before awaiting exit; failed spawn has no live process to reap.

## Routing

HTTP/parser contracts need no browser. Pure DOM unit tests may use jsdom/happy-dom. Qualified DOM/JS behavior and text-agent navigation can use Lightpanda, with agent-browser refs when useful. CSS/layout, screenshots, image decode, true keyboard/pointer behavior, Lighthouse and frame traces require a rendering engine, preferably a qualified pinned headless shell. WebKit/Firefox are compatibility lanes, not assumed memory wins. WebGL/WebGPU require explicit workload/adapter proof; 120 Hz acceptance requires the real phone. Do not change Hermes config or migrate credentials merely to adopt an optional navigation lane.
