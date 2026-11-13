---
name: public-repo-snapshot-publishing
description: Use when publishing a private repo publicly, PII-free.
version: 1.0.0
metadata:
  hermes:
    tags: [git, github, privacy, publication, pii]
    related_skills: [github, clean-publication-adapter-gate, agent-ready-public-repo]
---

# Public repo snapshot publishing

## When to Use
The owner asks to put a private working repo on GitHub publicly ("fine to keep it public, just don't leak personal data or PII"). The private repo keeps its full history. The public repo gets scrubbed snapshots only. For extracting a clean branch with private adapters, see clean-publication-adapter-gate instead.

## Procedure
1. Inventory first: run `git ls-files`, group files by top-level directory, and list every image or binary. Grep the tracked tree for absolute home/data paths, tailnet hostnames and IPs, chat/user ids, the owner's name, emails and internal profile names. Decide excludes by directory, not file by file.
2. Write a publisher script in the private repo, e.g. `tools/publish_public.py [--push]`:
   - Build from `git show HEAD:<path>` for tracked files only, never from the working tree, so other agents' uncommitted edits stay out.
   - EXCLUDE: home and room photos, runtime `data/`, deployment units and host launch scripts, judge/run transcripts that embed absolute paths, and owner review decisions.
   - Keep path rewrites and banned literals in a GITIGNORED rules file (e.g. `data/publish/rules.json`: `{subs: [[regex, repl]], banned: [regex]}`). If they live in the script, the script trips its own scanner and publishes the private strings. Keep only generic secret shapes in code: bot tokens, sk-/ghp_/AKIA/csk-/gsk_, private-key headers, JWTs. Refuse to run if the rules file is missing or empty.
   - Rewrite private paths to placeholders, plus the tailnet host and IPs, the owner's first name and internal profile names. Use a negative lookahead to keep well-known ranges such as 100.64.0.0/10 intact in code.
   - After rewriting, scan every text file against banned plus generic patterns and ABORT with file:line on any hit. Refuse unknown file types instead of copying them.
   - Re-encode images with metadata stripped (`vips copy in 'out[strip]'`).
   - Stage into a sibling checkout (`<repo>-public`, its own `.git`), commit with the noreply identity, and push only with `--push`.
3. Iterate without `--push` until it stages cleanly. Then grep the staged tree for the owner's name, profile names and leftover placeholders in runtime code, and fix the rules.
4. Contact-sheet every published image and inspect it with vision for people, faces, documents, screens and family photos.
5. If any commit in the public checkout was made before the rules were complete, delete that checkout's `.git` and republish. The first pushed commit must be clean, because a later scrub commit does not remove earlier objects.
6. Scan `git log -p --all` of the public checkout with the private banned list and require zero hits. Then run `gh repo create owner/name --public --description ...`, add the remote, push, and read back the URL, visibility and remote SHA.
7. After later private commits, re-run the publisher with `--push`. The scan gates every publish.

## Pitfalls
- Host-specific helper scripts get placeholder paths and won't run from the public copy. Tell the owner, or make them env-driven in the private repo.
- Test assertions that mention private strings (e.g. checking an API hides a data path) get rewritten too. Keep them meaningful, e.g. assert on a field name instead.
- A static file route that serves a whole data folder can expose indexes and source paths even when the API redacts them. Narrow it to the asset subfolder before publishing or sharing.

## Report
Give the repo URL, the commit, what was excluded and what was rewritten, the scan result, and any functional side effects of the scrub.
