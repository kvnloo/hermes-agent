# Hermes × Tern: reference dashboards

**Feature branch:** `feat/tern-reference-dashboards` → `feat/tern-omp-parity`.  
**Coordination:** [issue #637](https://github.com/kvnloo/hermes-agent/issues/637), [RFC #510](https://github.com/kvnloo/hermes-agent/issues/510), [roadmap #509](https://github.com/kvnloo/hermes-agent/issues/509).

## What is implemented

Both dashboards are **native, opt-in Tern sheets** over the existing `ui-tsp` session. They do not modify the gateway or run new tools in response to opening.

| Command | Reads | UI | Truth boundary |
|---|---|---|---|
| `/map`, `/map <query>` | `./graphify-out/graph.json` | Most-connected symbols, source files, relationships, EXTRACTED / INFERRED / AMBIGUOUS / UNKNOWN provenance; arrows inspect, `r` refresh, Escape closes | Code dependencies only, **not** agent communication or task progress. Full force graph remains in Graphify's `graph.html`. |
| `/machine`, `/host-health` | `./.hermes-dashboard/machine.json` | Snapshot timestamp, update count, risk-marked packages, disk, problems and events | **Snapshot only**, never live or continuously scanning. Unavailable, unclassified and unchecked are never displayed as healthy/zero. |

Opening never runs Graphify, `pacman`, `journalctl`, an LLM, any installation/update, or an external network request. There is no ambient polling; pressing **Refresh** rereads only the same bounded local path. Sessions, approvals and tool authority remain Hermes-owned. An approval/clarification opens above these sheets. Each sheet is independent of the composer and stops displaying old data if the owning session changes.

### Generate the Graphify map

In the **project you want to inspect** (not automatically in the Hermes source checkout):

```sh
# Original Graphify-Labs implementation, with its own project/installation requirements:
uv tool install graphifyy
graphify update .
```

Graphify output is expected at `graphify-out/graph.json`. The native inspector loads nodes and `links`/`edges` with explicit confidence. Do not treat it as a live Hermes swarm graph. `graphify-out/graph.html` provides the external full graph. Check Graphify's own instructions before using its installer; past versions of `graphify hermes install` modified `AGENTS.md` and no installer is invoked by our UI.

### Generate a real machine snapshot

From any local project directory on the machine being inspected:

```sh
mkdir -p .hermes-dashboard
node /path/to/hermes-agent/ui-tsp/scripts/machine-snapshot.mjs > .hermes-dashboard/machine.json
# Optional: count accessible journal error sources, but do not export raw messages.
node /path/to/hermes-agent/ui-tsp/scripts/machine-snapshot.mjs --journal > .hermes-dashboard/machine.json
```

The collector reads local, nonprivileged disk stats and, where installed, `pacman -Qu` / `pacman -Qq`. `--journal` explicitly opts in to aggregated error counts from `journalctl`; raw log text is **not** exported. It does **not** use sudo, alter installed packages, open a browser, start any network access, or write a file itself. Shell redirection above is an explicit local write. Non-Arch systems return `updates_checked=false` (not zero pending updates).

Schema v1:

```json
{
  "schema": 1,
  "captured_at": "2026-10-20T14:00:00Z",
  "machine": "my-machine",
  "os": "Linux 7.x",
  "updates_checked": true,
  "problems_checked": false,
  "disk_percent": 62.4,
  "available_gib": 169,
  "installed_packages": 1342,
  "updates": [{"package":"example","from":"1.0","to":"1.1","risk":"unclassified"}],
  "problems": [],
  "events": []
}
```

The numbers and package above describe the **schema, not a live machine**; they are never bundled as default UI readings. The collector intentionally does not infer update risk from package names. If another known, trusted classifier supplies a `risk` label (`high`, `medium`, `low`), the sheet can show it as a snapshot assertion, **not** as an independently verified claim.

Keep `.hermes-dashboard/` and `graphify-out/` out of git in the inspected project: system package inventory, hostnames or graph details can be sensitive. This feature cannot publish or share these local files.

## Original authors and actual reference evidence

**Graphify-Labs**, via [ArchiveExplorer's 20-second video/post](https://x.com/ArchiveExplorer/status/2111474680502661298). Observed: clustered force-style code graph, selecting dependency nodes, displayed path/trace and a command/report pane. The author's post specifies provenance and the `GRAPH_REPORT.md`/`graph.html` artifacts. Earlier downstream donor: `tern-hermes-orchestration-wave2.patch` for `thefullctx/hermes-for-tern`, with previous Python `/map` tests; the active TypeScript adapter here is an independent port, not a copy/paste patch.

**HANCORE (@hancore_linux)**, via [25.46-second original video/post](https://x.com/hancore_linux/status/2112280684773388365). Observed: Arch/Omarchy “rumb” machine-health screen; six upper metrics (pending, problems/day, since upgrade, owner updates, disk/packages, pre-update checks), central eye/radial severity ring and modular groups, three lower lists (updates, problems, journal/live events), bottom keyboard legend. The tweet says only “working on a new TUI project”; **no verified public source code** or exact risk-scoring algorithm. This feature **adapts the information hierarchy**, not the artwork, code, or unverified risk logic. Tern's semantic UI is not claimed to be pixel-identical.

### Agent Reach / CI evidence, 2026-10-20 UTC

- [HANCORE CI](https://github.com/kvnloo/oss-factory/actions/runs/39435553675)
- [Graphify CI](https://github.com/kvnloo/oss-factory/actions/runs/39435562493)

Both CI runs installed Agent Reach, but `twitter tweet` returned **not_authenticated** (no browser cookies in isolated Actions). Both `yt-dlp` runs downloaded the original public videos; frames were extracted and the videos were separately inspected. FxTwitter yielded matching post text and media metadata. **Agent Reach did not retrieve either post itself.** REA was installed but not run (neither author provided a public demo site). Raw video and ephemeral CI artifact are **not** copied into this repository.

## Acceptance status

- Source readers: bound the JSON file size, element counts, string lengths, displayed rows; reject symlinks and missing/corrupt data; no raw reader error disclosure.
- Tests: `npm --prefix ui-tsp run typecheck`, `npm --prefix ui-tsp test -- src/__tests__/reference-dashboards.test.ts`, `npm --prefix ui-tsp run lint`.
- CI: `.github/workflows/tern-reference-dashboards.yml` tests this branch; review its **exact-head** result.
- **Not yet proven:** a signed-in native Tern host, full visual parity with HANCORE's custom TUI, real-world Arch package data or Graphify end-to-end invocation. Do not claim these based on fixtures.
