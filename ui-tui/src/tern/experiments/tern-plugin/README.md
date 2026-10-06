# Hermes A fixture lab — optional Tern launcher

On Variant A this command now launches the worktree's executable native fixture,
not an installed `hermes` command. See [the native preview runbook](../NATIVE_PREVIEW.md)
for installation, direct launch and verification limits.

```bash
tern plugin link /absolute/path/to/hermes-tern-a/ui-tui/src/tern/experiments/tern-plugin
tern plugin reload
```

Focus a Tern pane inside the A checkout, then use **Open Hermes A fixture lab** or
`Ctrl+Alt+Shift+H`. It checks for the fixture entrypoint before arranging a new tab:
fixture left, manifest/tests upper-right, scratch shell lower-right.

The preview does not read or write Hermes sessions/configuration, so the old
worktree-local `HERMES_HOME`/`HERMES_RUNTIME_DIR` overrides are no longer necessary
for this launch. B/C remain separate scaffold branches.

The Luau launcher and actual host layout still require live Tern verification.
CI verifies the TypeScript CLI directly with a fake Tern peer; it does not prove
that this plugin loads or that its geometry is correct. The direct command in
`NATIVE_PREVIEW.md` is the reproducible entrypoint independent of the plugin.

Credit: Stencil Labs for Tern/TSP and the layout/plugin APIs.
