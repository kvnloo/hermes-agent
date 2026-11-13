---
name: public-safe-snapshot-sync
description: Use when syncing or pulling a public-safe snapshot.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [github, sqlite, privacy, actions, snapshot]
    related_skills: [github, rolling-integration-gitops]
---

# Public-safe snapshot sync

## When to Use

Use when a committed public database or snapshot is derived from a private ledger, and the user wants that public copy kept current or downloaded locally. Also use when they say the history is already in the database, or that the sync should run on the remote rather than as a local historical walk.

If the repository is theirs and the missing job is already specified, implement the remote incremental sync. Do not stop at the open issue.

## Procedure

1. Confirm which file is the committed public snapshot and which file is the private ledger. The private ledger is usually gitignored. Read the publisher before scheduling anything.
2. If the publisher deletes the public snapshot and copies from the private ledger, do not run that command on a fresh checkout or in Actions. The runner does not have the private ledger, so the publish step replaces history with whatever the empty or partial private file contains.
3. Read the high-water mark from the committed public snapshot (`MAX` of updated or created time). If that mark is missing, refuse a full historical ingest unless the user explicitly asks for a first load.
4. Add an incremental job that opens the public snapshot in place. Fetch only records newer than the mark, with a short overlap. Upsert. Redact private rows with the same opaque id the existing publisher already uses, so a repeat sees the same row instead of a duplicate. Fail closed when visibility is unknown. Throw if the row count shrinks. Checkpoint WAL and close before committing, and commit only the public snapshot.
5. Schedule that job on the branch that already deploys the site, plus `workflow_dispatch`. Let the existing pages workflow deploy on the snapshot push. Do not add a second publisher.
6. The job's checkout is stale by the time a queued ingest finishes. Copy the snapshot aside, fetch the default branch, check out that tip, copy the snapshot back, commit, and push that tip. A push from the original checkout is rejected and the ingest is discarded. If the ingest already wrote the file and only that push failed, publish the file before reporting the job as unfinished.
7. Cross-repo contribution queries need a token broader than the workflow `GITHUB_TOKEN`, which is limited to the current repository. Set it with `gh auth token | gh secret set <NAME> --repo <owner>/<repo>`. Never print the token, and never put it in the workflow file. The job should exit if the secret is empty.
8. Do not claim the ledger is current until the run finishes and a fresh read shows the high-water mark moved. A queued run is not a sync. A CLI that can join the snapshot is not a live view: the serving process has to open that file on each request, or the page will not show it.

## Local copy

Use this when the user wants the public snapshot on disk. The private ledger is not in git, so it cannot be downloaded. Do not offer an encrypted upload of that ledger unless they explicitly change that boundary.

1. If the repository is public, clone or update it from the public HTTPS URL. Run git with the ingest token and `GITHUB_TOKEN` unset, and `-c credential.helper=` so the user's saved GitHub credential is not attached. A public fetch does not need that credential, and the credential may be the same token that can read private repositories.
2. Refuse a remote URL that embeds a token or user:password. Never put the ingest secret in the remote.
3. A fresh download checkout gets an empty local `credential.helper`. Do not apply that to a working checkout that must push. A cleared helper blocks later pushes. Keep the download checkout separate from the dev checkout.
4. On update, fetch with `+<branch>:refs/remotes/origin/<branch>` and check out `origin/<branch>`. Fetching only into `FETCH_HEAD` leaves the remote-tracking ref behind, so status looks diverged even when the tree matches the remote tip. Refuse the update if the checkout has local tracked changes.
5. After the pull, require `git hash-object` of the public snapshot to equal `git rev-parse HEAD:<path>`, and require the snapshot's privacy mark. Then print the row count and high-water mark. Do not claim it includes commits the remote job has not finished.

## Read-only preparation snapshots

When scope is preparation/remote-read only, leave existing archive checkouts and their Git refs untouched. Resolve the published branch to a commit, read the public snapshot's expected Git blob ID, and download that commit-pinned file into the authorized receipt directory using public HTTPS without credentials. Verify the Git blob hash, privacy marker and SQLite `quick_check`; record the row count and public high-water mark. Open the standalone committed file with `mode=ro&immutable=1` (not a live WAL-backed ledger). Keep newer targeted GitHub reads in a separate timestamped evidence overlay: a verified download is not a remote ingestion, deployment, or proof of activity beyond the published watermark. Reuse a known checkout inventory and recheck selected paths instead of repeating a filesystem-wide discovery.

## Pitfalls

- GitHub search stops at 1000 results and can report no next page at the cap. Count the window first. If the count is over 800, split the date range and query each slice. If one day still exceeds the cap, fail. Do not paginate to the cap and treat that as complete.
- Newest-first connections can stop when the newest stamp on a page is older than the watermark. Search is not ordered that way. A date qualifier has to be in the query, and a relevance-ordered page is not an overlap check.
- The first catch-up after a stale mark can be large. That does not mean the job should fall back to a full historical ingest. Later runs are the overlap window only.
- Do not store private titles, excerpts, repo names, or real node ids in the public snapshot. A missing `isPrivate` is private.
- If an incremental refresh of a redacted yearly or aggregate total returns no private count, keep the previous redacted total. A public-only response is not evidence that the private total became zero.
- A shallow update (`fetch --depth 1 +<branch>:refs/remotes/origin/<branch>`) alternates between working and `[deleted] origin/<branch>` / `not a commit` because the stale ref survives. Run `git update-ref -d refs/remotes/origin/<branch>` before every update (in a small wrapper script), rather than retrying after failure. Verify with three consecutive runs, and verify refusal by pointing origin at a URL with embedded credentials.
