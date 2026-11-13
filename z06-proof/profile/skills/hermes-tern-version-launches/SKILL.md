---
name: hermes-tern-version-launches
description: "Use when switching, installing or refreshing Tern UI versions."
version: 2.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [tern, hermes-tern, frontend, channels, plugin-install]
    related_skills: [hermes-agent, tern-serve-real-turn-isolation, session-recovery]
---

# Hermes Tern frontend versions (channels)

## When to Use
Use when the owner wants another hermes-tern UI (upstream, fork main, preview or a feature build), wants a pane switched live, or wants a hermes-tern revision installed into a profile. Also use when explaining why a Tern feature looks or behaves differently between versions.

## Owner's target interface (the spec)
```
hermes -p clean --tui tern       # registry default (upstream)
hermes -p clean --tui mytern     # fork main
hermes -p clean --tui myternp    # fork preview
hermes tern switch <channel>     # live, same pane, same session
```
All of these keep the same profile, history, settings and gateway; only the frontend bundle differs. The rules:
- No `~/.local/bin` wrappers.
- No cloned or per-version profiles.
- No custom HERMES_HOME.
- No per-version Python environment.

Any design that changes which profile, history or gateway he lands in is an ASK. Never announce it in a progress note or completion report: mentioning it is not consent, and isolating preview code does not justify losing shared history. Before deleting any wrongly created profile, check its state.db for his conversations.

## Procedure
1. **Re-anchor on his words.** Grep omp session jsonl and EVERY profile's state.db, including wrongly created profiles, for his user turns about the launch shape. The literal command he typed is the spec.
2. **Read live state.**
   - `<profile>/plugins/.install-metadata.json` and `git -C <plugin> log -1`.
   - `hermes tern channels`.
   - For each running `dist/entry.js`, read `/proc/<pid>/environ` (TERN_PANE, HERMES_HOME, HERMES_TUI_DIR) and argv. That is the bundle each pane really runs.
   - Other sessions install feature SHAs into clean, so check for a live owner before changing the install.
3. **Write the outcome plan** (target commands, invariants, mechanism, known limit, steps, current state) to the artifact dir. Ask all open decisions in one message before mutating anything.
4. **Add or refresh a channel.**
   - Run `git archive <sha>` into `~/.hermes/tern-channels/<name>/<sha>/`, then put the bundle at `frontend/dist/entry.js`.
   - Record `repo/ref/sha/bundle_sha256` in `channels.json`.
   - Copy bundles with Python (execute_code): the terminal lifecycle guard refuses shell commands that reference files over 1 MiB.
5. **Test uninstalled launcher code against the real profile** as a project plugin. Symlink `proj/.hermes/plugins/hermes-tern` to the worktree and set `HERMES_ENABLE_PROJECT_PLUGINS=1`; the project plugin beats the installed one of the same name. Then verify in an owned `tern serve` (rules below).
6. **Ship through preview** (rules below). Then install into the profile (rules below).
7. **Switch panes.** Panes started on an older launcher need one manual relaunch with `scripts/relaunch-pane.sh`. After that, `hermes tern switch <channel>` is a single command the agent may run for him.

Architecture depth (pane wiring, the parts in each half, capability gating, switch protocol and its known gaps): `references/frontend-backend-architecture.md`. Load it before explaining limits or changing the launcher.
Frontend changes (local checks with CI's bun, new dependencies, `.d.ts` shims, the hosted bundle build, drawing owner libraries in Tern image nodes): `references/frontend-builds.md`.

## Rules: backend vs frontend
- **One superset backend per gateway** (the fork) serves every channel. Frontends check `plugin_methods` before use. Which hermes-tern the profile installs is his decision, because the Python half serves every frontend on that gateway.
- **Rebuild fork frontends** from their exact source and `frontend/hermes-src.lock`; a committed dist may be inherited and stale.
  - Offload builds per fleet rules.
  - Reuse deps between branches only when both package.json and bun.lock match.
  - Record the bundle hash separately from the source SHA.
  - If a change touches only Python, the existing bundle stays valid; reuse it rather than rebuilding.
- **When a feature looks wrong, read the component source before tuning colors.** Ported UI pieces in this repo may be hand-rolled imitations rather than imports of the owner's own library. Grep for the import, and compare against the owner's repo (`gh repo view kvnloo/<lib>`; check feature branches and tags for terminal ports). Keep the existing frame cache and state plumbing, and swap only the geometry source.
- **When a channel's bundle is replaced by a fix,** rename the old entry to `<name>-legacy` in `channels.json` instead of deleting it, so he can compare side by side. Re-launch or switch only the pane he asked about, and tell him that his other panes keep the old bundle until they are switched.
- **To find out which agent introduced a bad UI piece and why,** follow `git log --follow` on the file to its commit, then to the PR, then to the session that wrote it (omp jsonl under `~/.omp/agent/sessions/`, ctx, state.db). Quote that agent's own reasoning line and the acceptance test it used. Report the model name, and the missing check that let it through.
- **Before switching his live pane to a new bundle,** render it in an owned serve with a real turn and look at the crops: the default is a light theme with dark ink, and the image sits at the composer's left edge. If his pane is on a hidden tab, prove the switch from the node argv and pane file, and let him look. Don't focus his window to screenshot it.

## Rules: shipping to preview
- A PR into the fork's integration/nightly branch must have that branch in its head history. Merge preview into the feature branch first: its CI checks out the PR head SHA and runs preview-only test files.
- **Fettl gate.** Preview runs a Fettl changed-code gate that publishes no findings in CI. Reproduce it locally with the pinned binary: `fettl check . --diff-source branch:<merge-base>..HEAD --format text`. Pass HOME and XDG_* overrides via `env` for that one command.
  - Never `export HOME` in the persistent terminal: it breaks gh and git auth for the rest of the session.
  - Fix findings for real (narrow excepts, named constants, real names, no `sys.exit` in handlers, env reads through one helper). Do not suppress them.
- Merge preview PRs as squashes, with `--match-head-commit <sha>`. Link the PR with link_pull_request.
- Plugin unit tests: `env -u PYTHONPATH uv run --no-project --python 3.12 --with pytest --with pydantic --with pyyaml python -m pytest`, because Hermes exports a py3.14 PYTHONPATH. The suite's conftest must clear TERN_PANE, because agents run inside real panes. Compare against the base for errors that already existed.

## Rules: installing into a profile
- `hermes -p <p> plugins install kvnloo/hermes-tern --ref <40-char sha> --enable --yes-deps`. The SHA must exist on the remote, so push an install branch first.
- **When `--force` is needed.** Reinstalling over an existing plugin needs `--force`, and `--force` ALSO accepts scanner cautions.
  1. Run the install once without it and save the scan output.
  2. Diff the finding list against the previous install.
  3. Accept only findings you have reviewed, and tell him what was new.
- To keep a feature build (e.g. Ctrl+L/orbs) while adding launcher changes, compose them on top of the feature commit, keeping its qualified bundle. Expose that bundle as its own channel.
- Read back install metadata, the plugin HEAD and the bundle sha256. Then run `hermes -p <p> tern channels` and `<alias> --help` from a plain shell, without project plugins enabled.
- A gateway plugin reload is not proof of every fork feature. Report launch verification separately from inference or feature qualification.

## Rules: owned tern serve verification
- Use a separate TERN_CONFIG_DIR, TERN_DAEMON_SOCKET, XDG_STATE_HOME and control socket. Unset WAYLAND_DISPLAY/DISPLAY and the ambient TERN_* variables. Start it with terminal `background=true`, not `&`.
- Serve shells drop custom env vars, and serve panes have no TERN_PANE. Prefix the command, e.g. `tern ctl --control S run '"TERN_PANE=900001 HERMES_ENABLE_PROJECT_PLUGINS=1 hermes -p clean tern --new"'`.
- Never run bare `tern serve --help`: it starts a serve on /tmp/tern.sock.
- Wait for both the composer and the model label. Prove bundle selection from the node argv, not from the UI.
- For a mid-turn switch, prompt a long terminal tool (`sleep 40; echo TOKEN`), confirm the process with pgrep, switch, then check that the tool row and the reply landed in state.db.
- Save the shots and a RECEIPT.md in the artifact dir. Quit owned viewers and the serve, and remove the test pane files.
- To SEE his live pane without touching it, use grim on its monitor (see linux-compositor-window-capture). Never `tern ctl shot/key` the ambient window.

## Rejected history
An earlier setup forced profiles through `uptern/mytern/myternp` wrappers in `~/.local/bin` and cloned `mytern/myternp` profiles. It was rejected. Its receipts (`/mnt/zer0models/project-artifacts/hermes-tern-simple-20261101/`) are evidence, not approval.
- Native profile clone copies installed plugins.
- Copied Python plugin packages collide in PM's shared workspace.
- Never repair clone fallout by editing source plugin directories or another profile's settings.
