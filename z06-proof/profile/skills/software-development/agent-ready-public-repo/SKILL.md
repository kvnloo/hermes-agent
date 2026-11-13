---
name: agent-ready-public-repo
description: Use when making a repo public or agent-bootstrappable.
---

# Public, agent-ready repositories

For "make it public / build in public" and "make it AI-native so any agent knows how to set it up".
Goal: a fresh clone on another machine, opened by any coding agent, reaches a working, tested
state with one command, and nothing private leaks.

## Procedure

1. **Audit every commit before flipping visibility**, not just the tree:
   `git grep -n -I -i -E '<private names>|api[_-]?key|secret|token=|ghp_|sk-' $(git rev-list --all)`.
   Also grep for machine paths (`/home/<user>`, mount roots) and names of private sibling projects.
   Report what remains in history and offer a rewrite; do not force-push silently (open worker
   branches are based on the old history). Feature branches become public too.
2. **Move machine-specific config out of the repo**: user project lists, local paths and URLs go
   to `~/.config/<app>/...`; commit a `*.example.json` with a working demo entry plus a reference
   of every supported field. Code reads the user file, falling back to the example.
3. **Ship demo data that is generated, not committed**: a small script (e.g. ffmpeg lavfi test
   sources) so an empty library still opens. Never commit large media.
4. **One idempotent setup script** (`npm run setup` -> `scripts/setup.sh`): check required tools and
   versions (fail with a clear MISSING list), list optional ones, install, build, create demo data
   if empty, import, run the fast tests, print the single next command. `--check` = `npm run doctor`.
5. **Tests must exit non-zero on regression** (assert expected values, not print JSON); the
   default `npm test` is fast and needs no logins; real-subscription tests get their own script.
6. **Prove it from a fresh clone with an isolated HOME**:
   `git clone . $TMP/repo && HOME=$TMP/home bash scripts/setup.sh` — catches dependence on your
   own config, caches and paths.
7. **Agent instructions**: `AGENTS.md` (setup command first, what the app is, layout, commands,
   where user data lives, hard rules: performance budgets, security, licences, no secrets), with
   `CLAUDE.md` and `GEMINI.md` as symlinks to it. Workflow-level; do not restate code.
8. Flip visibility with `gh repo edit OWNER/REPO --visibility public --accept-visibility-change-consequences`
   and read it back with `gh repo view --json visibility`.
9. **Ask about the licence at flip time** (recommend the upstream's, e.g. MIT): a public repo with no
   LICENSE is not open source, so nobody can legally use or contribute. Do not pick one silently.
10. **Verification harness anyone can run** (`npm run verify`): temp HOME, generated demo data, its
    own server on a free loopback port with a throwaway token, Playwright journeys that assert real
    values (durations, seek positions, bytes on disk unchanged, 390 px no overflow, console clean),
    `report.json` + screenshots, teardown of only what it started. Pair it with a repo-local verify
    skill (`.agents/skills/verify-<app>/SKILL.md` + `features/*.md`, symlinked from `.claude/skills`
    and `.cursor/skills`). Look at the screenshots; a green exit with a broken layout is a failure.
    Include a viewport-matrix journey (e.g. 2560x1340, the user's real window size, 1440x800,
    1366x680, 1280x640, 1024x700, 768x960, 390x780) asserting: desktop app shell has no document
    scroll, primary work areas (canvas, timeline) fully inside the viewport, every panel reachable,
    and at all sizes no horizontal scroll, no clipped leaf text without ellipsis, nothing off-screen.
    Testing only one desktop size plus phone width misses the long-scrolling-page failure.
    Write `report.json` with repo-relative paths and `<home>`/`<tmp>` placeholders so evidence can be
    committed without tripping the local-path check.
11. **CI mirrors local gates**: local-path check, doctor, build drift (`git diff --exit-code dist/`),
    fast tests, verify, add-on tests; upload the evidence. Run perf as `continue-on-error` trend only
    (shared runners are too noisy to gate on). Watch the run to green before reporting.
12. **Community files**: CONTRIBUTING (setup, proof required per PR, perf numbers for hot-path
    changes, private security reporting), issue forms (bug/feature/perf), PR template with the
    verification checklist, and a ROADMAP parity table against named competitors whose status
    column is checked against the code (shipped only if it exists).

The local-path guard is `scripts/check-no-local-paths.sh` in this skill; copy it into the repo.

## Public snapshot of a private repo (separate public repo)

When the owner wants "everything public, no personal data" but the private repo must keep its history:

1. Write a fail-closed publisher (`tools/publish_public.py`): read only committed blobs at HEAD (`git show HEAD:path`), drop excluded paths (home photos, `data/`, deploy units/launch scripts that encode the host, judge/evidence JSON full of absolute paths), rewrite host strings to placeholders, strip image metadata (`vips copy in out[strip]`), refuse unknown file types, then abort if any banned regex survives. Commit into a sibling `<repo>-public` checkout and push only with `--push`.
2. Keep the host-specific rewrite rules and banned literals (paths, tailnet host, user ids, first name, internal profile names) in a gitignored private rules file: a publisher that contains the literals fails its own scan, and publishing the list leaks it.
3. Ban generic secret shapes too (bot tokens, `sk-`, `gh*_`, `AKIA`, `csk-`, `gsk_`, PEM headers, JWTs). Allowlist well-known ranges the code needs (e.g. CGNAT `100.64.0.0/10` in an IP check) explicitly instead of loosening the IP rule.
4. Before the FIRST push, if any earlier staging commit was made with weaker rules, delete the public `.git` and regenerate: one dirty ancestor commit leaks forever. Then scan `git log -p --all` of the public repo with the private banned list and look at every published image yourself.
5. Create with `gh repo create OWNER/NAME --public`, push, and read back URL/visibility/remote SHA. Re-run the publisher after later feature batches.

## Pitfalls

- Re-run the privacy audit on **every branch before it merges** to public main, not only at flip
  time: agent workers write evidence JSON/logs full of absolute paths and private project ids. Scrub
  with a regex to `<local>/basename`, re-validate every JSON file, move source-media paths into a
  gitignored `*.local.json`, and keep the CI local-path check so it cannot recur.
- Tests that spawn the app's own server must not write the user's real config or discovery files
  (e.g. `~/.config/<app>/bridge.json`): a test run silently repoints the user's live clients at a
  dead test port. Spawn with `--no-config` or a temp HOME, and assert the user's file is byte-for-byte
  unchanged after the run.
- Tests and perf suites must be hermetic: anything that opens the maintainer's real library or a
  named private project fails for every contributor. Generate fixtures of the same size instead and
  prove it with `HOME=$(mktemp -d)`.
- Playwright's bundled Chromium has no H.264 decoder, so video journeys time out at readyState 0 in
  CI; install and use Chrome (`npx playwright install --with-deps chrome`, `channel: 'chrome'`).
- `gh` API calls share one rate limit with every agent on the account; poll CI sparingly.
- Before shipping third-party example media (upstream examples, sample films) on a public site,
  audit each item's licence individually: an MIT repo can still bundle footage, photos, music or
  people's likenesses it cannot relicense. Publish only verified items, credit author + licence +
  source link on each, and list unclear ones for the owner.
- A hosted (static) build of a local-first app shows only the visitor's own local data (folder
  access or their own local server) plus explicitly licensed examples: no accounts, no uploads,
  never the maintainer's library. Pass any local-server token in the URL fragment, not the query.

- Hermes treats `AGENTS.md`/`CLAUDE.md` as protected instruction files: writing them needs the
  user's approval, and a timed-out prompt is a refusal. Ask in chat first, never route the write
  through the terminal, and do not create the symlinks (they dangle) or mention the file in the
  README until it exists.
- READMEs for this user: short, first person, in his voice: the origin/why in two or three
  sentences, then minimal run instructions. No status lines, "X-agnostic" taglines, importer or
  agent tables, or security essays; that depth belongs in AGENTS.md/docs.
