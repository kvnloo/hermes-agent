---
name: clean-publication-adapter-gate
description: Use when publishing generic code from private branches.
version: 0.1.0
author: Kevin (kvnloo), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [git, privacy, adapters, publication]
    related_skills: [git-evidence-preservation, github]
---

# Clean publication with private adapters

## When to use

Use after a publication audit finds private history or project-derived defaults, when a clean replacement branch is explicitly authorized. Do not rewrite, merge or push private development branches to sanitize them.

## Procedure

1. Record worktree HEADs and dirty status with `terminal`. Verify the authorized public base against the remote. Create a separate worktree directly from that base; transfer selected tree changes, never private commit ancestry.
2. Extract project policies, default identities, report globs, live-layout rules, UI queue maps, specialist taxonomies and source-database adapters into a private directory outside public repositories. Preserve running service ownership; moving a CLI does not authorize restarting or replacing its server.
3. Make the generic engine accept an explicitly selected trusted adapter. Fail closed on invalid adapter paths and unsupported intake. Never auto-discover executable adapters from imported data. Ship fictional fixtures rather than renamed real records. Move live-data verification and project-derived recipes privately.
4. Test default isolation, explicit adapter behavior, unknown input rejection and synthetic live polling. A chat importer must validate the full batch, retain exact receipts/null bindings, share the owner lock, reject conflicting IDs, append durably and read back; dry-run by default and never manage service lifecycle.
5. Freeze only event/calibration streams into scratch with immediate source/copy hash checks. Compare original and adapted CLI JSON on the same paths for every requested command/element. Fix only the clock for generated timestamps. Hash real artifacts freshly; a stat-guarded per-run cache avoids rehashing large archives for every command. Retain all diffs privately. Do not run report materializers on live data alongside an owner server.
6. Run complete Python, Node, lint and optional browser gates with real fixture servers. Check browser cases actually ran. Commit only generic changes directly above the public base.
7. Enumerate `git rev-list --objects BASE..CANDIDATE`; inspect every commit, tree and blob, including filenames and messages. Scan private paths, real trial/element/source IDs and raw/JSON-escaped owner quotes. Reject binary blobs. Secret-scan both history and exported full outgoing objects; a clean tip or secret scan alone is not privacy clearance.
8. Exempt only exact unchanged lines or tree entries proven present at the same public-base path. A new tree can contain already-public case-study names: compare canonical `git ls-tree BASE:path` entries, not broad filename allowlists. Record exemptions separately from new findings.
9. Require zero new privacy, quote, secret and binary findings, clean tests and verified private-state preservation before pushing the single authorized ref. Open the explicitly named draft/base/repository only; read back remote SHA and PR draft/head/base fields. Append evidence to the private audit.

## Pitfalls

- A scrub commit does not remove private ancestor objects.
- Generic-looking tests can retain real identifiers and project-specific assertions; move those assertions privately and replace them with genuinely synthetic coverage.
- Remote tracking refs may be absent despite a valid public branch. Fetch only the required ref after verifying its remote SHA.
- Updating a private wrapper is reversible; hot-swapping a running materializer is not equivalent and requires separate authorization.

## Verification

Retain private source snapshots, exact JSON comparisons, test receipts, all-object inventory/scans, base ancestry proof, preserved-worktree comparison and the verified draft PR URL. No scene or owner approval follows from these technical gates.
