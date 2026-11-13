---
name: vercel-cli-deploy
description: Use when deploying and verifying static web applications.
categories: [deployment]
---

# Static deployment and external-asset acceptance

Use for CLI-controlled Vercel deployments, static-export verification and portable
asset delivery across local, subpath and CDN-backed surfaces.

## Standing boundaries

- Treat a successful build, deploy receipt, homepage or ready flag as necessary but
  insufficient. Prove the actual user interaction on the exact deployed artifact.
- Deliver a stable hosted URL for a finished website unless the owner explicitly
  requests a local/private preview. A loopback or Tailscale URL depends on a live
  local process and the reader's network membership; label it as a preview, not a
  durable delivery. Preserve private visibility when choosing hosting, and publish
  only the approved runtime files—not source archives or reference media by default.
- Preserve intentional product-source versus deployment-branch divergence. Identify
  the integration contract before choosing a base; never synchronize branches or
  use the default branch merely for convenience.
- Keep runtime fixes, acceptance-test repairs and hosting plumbing in focused
  commits. After an incident is accepted, keep a hygiene-only request hygiene-only;
  do not redeploy or reopen visual/product work without current authorization.
- Keep raw masters, private binaries and recovery evidence outside application Git
  and uploads. Preserve source checksums and register only approved derivatives.
- Report commands, real exit codes, exact SHAs/URLs, rendered-state evidence and
  anything NOT RUN. Desktop emulation is not physical-device acceptance.

## Procedure

### 1. Reconstruct authority before building

Inspect repository instructions, deployment configuration, current refs, worktrees
and dirty/ignored evidence. Read relevant change diffs, not only titles or prior
agent claims. Check the fetch refspec: a single-branch clone does not refresh every
branch merely because `git fetch` succeeded. Refresh the refs needed for the task
without deleting recovery work or altering another worker's checkout.

Use an isolated checkout of the intended commit. Record:

    git rev-parse HEAD
    git status --porcelain
    git diff --name-status <product-ref>..<deployment-ref>

Capture full identifiers directly from tool output. Distinguish a clean source
checkout from an output directory containing untracked local artifacts.

### 2. Establish the asset and build-time contract

Determine whether clients request an external origin directly or use an app-host
rewrite. Do not change a working architecture to simplify the verifier. Keep one
canonical path resolver and the explicit manifest/app-origin plus configured-origin
allow-list; do not permit arbitrary HTTPS assets.

Preserve logical manifest paths and normalize the logical prefix exactly once.
Test the complete production path from manifest parsing through concrete tile
planning, not just isolated resolver helpers. A parsed absolute URL and a raw
logical path are different interfaces.

Set public build variables before the build that emits client JavaScript.
`NEXT_PUBLIC_*` values are normally embedded by Next.js at build time: setting
one only on a static server or changing a hosting variable does not update an
already built client. Rebuild/redeploy after a build-time origin change unless the
application explicitly implements a separate runtime configuration channel.

See `references/asset-origin-abstraction.md` for the path contract and
`references/external-origin-patterns.md` for direct-origin versus proxy choices.

### 3. Prove the local production artifact

Run existing deterministic unit/integration gates with production imports, then
build the exact source with the intended public configuration. For `output:
"export"`, serve `out/` with a static server rather than `next start`.

Use the repository's one-command acceptance harness only after inspecting and
exercising it. Its name does not prove free-port selection, readiness, cleanup or
exit-code propagation. Auto mode should bind an OS-assigned port; an explicitly
requested occupied port must fail rather than reuse or kill an unrelated listener.
Readiness must identify the expected artifact, not merely any HTTP response.

Run the behavior that previously failed, including settled detail loading and
navigation/re-entry where relevant. Monitor uncaught browser errors independently
of application debug state: an app can report `errors: []` while a render callback
throws. Never weaken later assertions into startup-only acceptance.

See `references/static-verification.md` for server ownership and browser evidence.

### 4. Inspect upload scope and project linkage

Use the project's approved CLI invocation; where it uses an ephemeral Vercel CLI,
start with `npx vercel@latest --help` and record the version. Check identity and the
linked project/scope before deploying:

    npx vercel@latest whoami

Inspect the explicitly intended project/scope before creating or linking anything.
A hostname returning 404 does not prove that its project name is unclaimed; use
`project inspect` or `project ls` to resolve ownership. For a clean
`<name>.vercel.app` URL, stage only the approved compiled static files in a dedicated
directory and select the project explicitly, rather than inheriting its folder name.
After confirming current CLI help, the supported no-link workflow is:

    npx vercel@latest project inspect <name> --scope <team>
    # Only if the intended project does not exist:
    npx vercel@latest project create <name> --scope <team>
    npx vercel@latest deploy <static-dir> --project <name> --scope <team> --dry --json
    # After inspecting the dry-run inventory, when production publication is authorized:
    npx vercel@latest deploy <static-dir> --project <name> --scope <team> --prod --yes --logs

Create/select the project before the dry run: an unlinked directory without an
explicit existing project may be rejected before inventory. Explicit `--project`
selection avoids pulling environment files solely to deploy a static folder.
Where repository workflow requires `vercel link`, inspect any environment files it
creates/pulls and exclude them from upload; confirm `https://<host>/.env.local`
returns 404 afterward. Confirm current flags with command help and never print
authentication files or token values.

Use supported deployment dry-run/file-list facilities before uploading. Save their
output outside the app checkout and inspect actual inclusion of masters, render
workspaces, recovery packages, local evidence and credentials. Do not assume
`.gitignore` and `.vercelignore` have identical behavior. Version durable inclusion
rules when the repository owns that contract; use temporary exclusions only for a
truly temporary deployment workspace.

Keep secret ignores broad: `.env*` plus `!.env.example` allows the example without
exposing newly named environment files. Ignore status, tracked status and existence
are separate facts; verify each with the appropriate Git/filesystem check.

### 5. Deploy and exercise preview

When authorized, deploy preview and capture its immutable URL/ID and build logs:

    npx vercel@latest deploy --yes --logs

Verify that the remote build received the required configuration; a local shell
variable alone is not proof of the remote build environment. Read the deployment
back and verify its served build identity and manifest.

Exercise real browser input without asset-route fulfillment/proxy mocks. Record
requested URLs, response statuses, request failures, console errors, `pageerror`,
state after each action, and screenshots or a trace. Require that the client
requests and paints the expected detail—not merely that a manually fetched CDN
tile exists. Assert every critical response result in the final pass/fail condition.

A direct app-host asset 404 is acceptable only when that URL is outside the explicit
serving contract and the application correctly uses the external origin. A 404 on
an actual application asset request is a failure. Static export does not itself
prove that a hosting-layer rewrite exists or is impossible.

### 6. Promote only when authorized and verified

After required preview gates pass, promote/deploy through the repository's release
procedure. Preserve the tested source/configuration and exact commit identity.
For an authorized CLI production deploy, the usual entry point is:

    npx vercel@latest deploy --prod --yes --logs

Read back the resulting deployment/alias, then repeat acceptance on the actual
production hostname. For public delivery, request the production alias without
cookies or authorization, then exercise it in an incognito browser: an authenticated
CLI request or a deployment-protection label does not establish anonymous access.
Check redirects, content type, build identity and real product/navigation actions.
For an unchanged static build, compare uploaded runtime files byte-for-byte against
the tested output. Report prior full-suite results and the new-host smoke test
separately; do not imply the full suite was rerun remotely. Verify reload and final
asset requests; do not substitute a CLI READY state for live acceptance.
If a check is blocked or fails, preserve the failure and do not claim completion.

### 7. Close with evidence, not process narration

Give a compact report of source/deployment identities, exact URLs exercised,
commands and exit codes, interaction/visual outcomes, artifact paths, branch/tree
state and remaining failures or NOT RUN gates. Keep issue completion proportional
to proven acceptance; a merged historical change is not fresh evidence.

## References

- `references/asset-origin-abstraction.md` — logical paths, resolution boundaries and build-time configuration.
- `references/external-origin-patterns.md` — serving modes, CORS and origin availability.
- `references/vercel-route-syntax.md` — inspect, publish and validate routing changes safely.
- `references/static-verification.md` — owned static server and real browser acceptance.
- `references/private-share.md` — protected deployment plus a shareable bypass link (use instead of GitHub Pages for private repos); Hobby has no team members.
- `references/cost-and-exposure-audit.md` — answering "will this bill me / can it be hacked": plan, functions, env, headers, local bridge, GitHub runners and secret scanning.
- `references/github-security-settings.md` — turning on secret scanning, push protection and Dependabot via `gh api`, with readback.
- `references/reviewer-feedback.md` — collecting reviewer notes from a protected site into GitHub Issues (index issue, ESM function, verification).
