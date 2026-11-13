---
name: git-evidence-preservation
description: Preserve local Git evidence before repository cleanup.
---

# Git Evidence Preservation

Use when the user wants to audit, inventory, or preserve local Git state before cleanup, pruning, branch deletion, or any operation that could lose local-only content.

**Core principle:** The working repository must remain UNCHANGED. All inventory and packaging happens OUTSIDE the repo.

## Workflow

### 1. Locate the real repository

The current working directory may not be a Git repo even when the user says "the repo". Search for it:

```bash
# Check if current dir is a repo
git rev-parse --show-toplevel 2>/dev/null || echo "NOT_A_REPO"

# If not, find repos under home
find ~ -maxdepth 4 -type d -name ".git" 2>/dev/null

# Check user's OMP/memory for canonical paths
cat ~/.omp/agent/memories/*/MEMORY.md 2>/dev/null | grep -i repo_name
```

**Pitfall:** Don't trust the user's stated path blindly. The repo may be at a symlink target, an offload mount, or a different path entirely. Verify with `git status` before proceeding.

When the project was moved or exists as several copies under different names, follow `references/multi-copy-inventory.md`. It covers finding copies by remote URL across mounts, grouping them by object store, picking the newest copy, and categorizing branches by lineage.

### 2. Establish baseline state (BEFORE anything else)

Capture the exact state that must be preserved:

```bash
cd /path/to/repo

# Branch and HEAD
git branch --show-current
git rev-parse HEAD

# Full status (tracked mods + untracked + ignored)
git status --porcelain --ignored > /tmp/baseline-status.txt

# Local branches with tracking info
git branch -vv

# Worktrees
git worktree list

# Stashes
git stash list

# Existing tags
git tag --list

# Remote info (for context, not for GitHub inventory)
git remote -v
```

Record: repo absolute path, current branch, HEAD SHA, upstream ref if present, worktree clean status, all tracked/untracked/ignored files, local-only branches, worktrees, stashes, Git version, timestamp.

### Judge age against the intended base, not the tracking-branch counter

`git status -sb` ahead/behind counts commits versus the branch's tracking ref. That ref may be an old feature branch, a rebased fork tip, or a lab branch — not upstream main. Before calling a checkout stale or current:

1. Read the tracking ref name and its commit date (`git log -1 --format='%ci %h %s' <tracking-ref>`). A large behind-count against an old feature ref is a history mismatch, not proof of thousands of newer feature commits.
2. Compare HEAD to the intended base in the same object store: `git rev-list --left-right --count HEAD...<intended-base>`. The left count is unique local commits; the right count is how far behind that base the checkout is. `merge-base --is-ancestor` tells you whether the old tip is even on the newer line.
3. Search sibling worktrees and other local checkouts of the same remote for a tree that tracks the intended base (or the current lab branch) with zero divergence and a later tip. That tree is the promotion or cleanup base. The old checkout is not, even if it is the path the user named first.
4. Do not delete or reset the old tree until `intended-base..HEAD` and the dirty/untracked paths are classified. Unique commits and incident notes can still be the only copy. Do not commit those dirty paths onto a fresh worktree just because the old branch is abandoned.

**Pitfall:** Do not treat "behind N" on a feature tracking branch as upstream drift — the counter follows whatever ref the branch tracks, so a rebased or abandoned feature ref inflates N without describing the current line of work.

### When cleanup is authorized

Classification is not permission to delete the checkout.

0. To back up a dirty worktree to the remote without touching its index, HEAD or files, build a commit from a temporary index: `T=$(mktemp); cp "$(git rev-parse --git-dir)/index" $T; GIT_INDEX_FILE=$T git add -A; tree=$(GIT_INDEX_FILE=$T git write-tree); c=$(git commit-tree $tree -p HEAD -m 'wip: snapshot ...'); [ -n "$c" ] && git push origin $c:refs/heads/wip/<name>`. Set `GIT_AUTHOR_*`/`GIT_COMMITTER_*` when no git identity is configured. Always guard `[ -n "$c" ]`: if `commit-tree` fails, `$c:refs/heads/x` becomes `:refs/heads/x`, a delete refspec. Unpushed local branches back up with `git push origin <branch>:refs/heads/wip/<name>-<date>`. Read back `git ls-remote` and the unchanged `git status` count.

1. Run `git worktree list` before removing anything. If other worktrees share that git directory, leave the directory in place. Archive unique commits with `git format-patch` and copy dirty/untracked paths outside the repo. Removing the main worktree deletes the object store those other worktrees use. After `git worktree remove`, the persistent shell may still be inside the deleted path; the next command fails before it runs unless you pass an explicit existing `workdir`. That failure is a dead cwd, not a missing script.
2. Before replaying an old unique commit onto current main, search that main for the distinctive symbols. A function that now lives in a split module has already landed under another path; do not cherry-pick the old commit on top of it.
3. If the remaining commits conflict, abort the cherry-pick and keep the patch archive. Do not hand-merge a stale UI onto current files during cleanup.
4. A lab SHA or plugin repo is an evidence ref, not an install pin. Record it on the authored registry evidence list. Do not copy it into `tested_ref`. A regenerating docs gate can pass without projecting that field; confirm the generated diff did not silently absorb it.

### Reconcile database records and dirty worktrees before judging recovery value

For recovery from an ancestor project or monorepo, do not restrict discovery to its current checkout and one familiar feature branch. Age is expected in an ancestor and is not a reason to reject reusable work.

1. Capture `git worktree list --porcelain`, refs, stashes and reflogs with `GIT_OPTIONAL_LOCKS=0`. Reconcile registered paths against scoped on-disk worktree directories, including nested and unregistered trees; record missing paths without pruning them.
2. Locate project-local task/orchestrator/audit SQLite stores through source configuration and scoped filename discovery. Open with SQLite URI `mode=ro` and `PRAGMA query_only=ON`; inspect table schemas before selecting explicit task, feature, reference and worktree columns. Never select credential/token fields or dump entire unrelated message tables.
3. Join database feature/task references to worktree paths, branches and actual files. For each existing relevant tree, capture staged, unstaged and untracked status plus diff statistics; inspect selected dirty implementation files as well as committed code. A branch tip alone misses unfinished and local-only features.
4. Before parallel dispatch, enumerate refs and registered worktrees into explicit assignments. Give one lane database/path reconciliation and partition branch families across the others, rather than sending every topic specialist through the same familiar checkout. Inspect branches without worktrees through `git show`/`git diff`, not checkout. Deduplicate identical tips/trees while recording every assigned ref. Keep staged index, unstaged diff and stash WIP distinct: a stash-index worktree is not the stash's complete contents.
5. Produce a coverage ledger: discovered, inspected, deduplicated, partial, deferred, missing, and excluded sources, with reasons. Verify the union of assignments against the discovered ref set. Ref resolution is not semantic code review; record unread portions. Treat database completion labels as leads, not executable evidence. A rejection applies only to the inspected component; do not generalize a shallow scan into 'nothing useful to recover.'
6. Rank small recoverable components as useful-now, useful-later, redundant, unsafe or unreviewed using implementation/test evidence, dependencies, license and integration cost—not novelty or whether they already appear in the current product. Keep useful ideas, working source, partial implementations and duplicate systems distinct. Review licensing at the actual component/reuse boundary: different repository licenses neither permit silent relabeling nor categorically prohibit every reuse. Keep recovered CI/deployment machinery inactive until separately reviewed; prefer a small opt-in local check to a platform transplant.

### 3. Create an archival Git tag only when authorized

Skip tag creation during a read-only scan or best-pieces discussion. If the user authorizes archival ref changes, create a LOCAL annotated tag pointing to current HEAD. This preserves Git commit state only — it does NOT capture ignored/untracked files.

```bash
# Check if tag exists
git tag -l | grep "archive/pre-cleanup"

# If exists and points to this HEAD, leave unchanged
# If exists but points elsewhere, STOP — do not overwrite
# If doesn't exist, create:
git tag -a archive/pre-cleanup-YYYY-MM-DD -m "Pre-cleanup archive anchor." HEAD
```

Rules:
- Do NOT push the tag
- Do NOT create a commit
- Do NOT alter HEAD
- Do NOT overwrite an existing tag pointing elsewhere

### 4. Inventory local-only artifacts

Focus on Git-ignored and untracked material. Use Git-native discovery first:

```bash
# List untracked files
git status --porcelain | grep "^??" | cut -c4-

# List ignored files  
git status --ignored --porcelain | grep "^!!" | cut -c4-
```

Then inspect plausible artifact directories. Look for:
- Reference images, screenshots, screen recordings
- Rendered frames, render sequences
- Blender files (.blend, .blend1)
- Source textures, high-resolution images
- Upscale outputs, Gigapixel results
- Compositing outputs, masks, alpha mattes, depth maps
- Animation exports, videos, GIF/WebP/APNG
- Visual-review artifacts, comparison images
- Performance traces, benchmark outputs
- Locally generated reports, design/source files
- Any assets deliberately excluded from Git due to size

**Pitfall:** Do NOT crawl the entire home directory. Start with Git status, then inspect directories whose names suggest artifacts: `artifact`, `render`, `output`, `capture`, `screenshot`, `reference`, `dream`, `gigapixel`, `blender`, `video`, `frames`, `comparison`, `benchmark`, `perf`, `trace`.

### Reconcile saved-artifact lineage before selecting versions

For best-pieces recovery, inventory both Git history and saved binary artifacts. Capture refs, distinct tips, reflogs, stashes and registered worktrees; missing worktree directories do not erase surviving refs, so do not prune during discovery. Trace each saved scene through its actual builder input path and receipt/hash chain. A feature commit being an ancestor of the current branch does not prove the saved binary was rebuilt from it.

Build a component matrix with donor scene/source, exact feature, render evidence, acceptance scope, rejected alternatives and unresolved approvals. Keep backups, test fixtures and duplicate candidates separate from unique designs. Treat later renders of the same scene hash as additional coverage, not new scene versions. Check reviewed-source hashes before promising reconstruction; a surviving builder may target a later rejected revision.

Present a small provenance-labelled visual shortlist and discuss choices before assembly. Preserve active application state and unsaved edits. Transfer bounded selected components into a new candidate rather than merging every branch or adopting a whole scene because one correction is useful.

### 5. Classify each candidate

Classify conservatively — when in doubt, preserve:

| Classification | Meaning |
|---|---|
| `PRESERVE_UNIQUE` | Local-only artifact with meaningful project info not recoverable from Git |
| `PRESERVE_REFERENCE` | Important visual/source/reference asset even if derivative exists elsewhere |
| `PRESERVE_EVAL` | Screenshot, overlay, review result, performance trace, benchmark evidence |
| `REGENERABLE` | Generated output clearly recreatable from committed source and known tooling |
| `CACHE` | Tool/package/browser/build cache with no unique project evidence |
| `DEPENDENCY` | node_modules, Python environments, downloaded packages, compiler caches |
| `UNKNOWN` | Potentially important but provenance/reproducibility unclear |

### 6. Build machine-readable manifest (OUTSIDE the repo)

Create the audit directory outside the repository:

```bash
mkdir -p ~/quackles-local-archive-YYYY-MM-DD
```

Produce at minimum:

**`manifest.json`** — Top-level metadata plus per-artifact records:
```json
{
  "schema_version": "1.0.0",
  "audit_timestamp": "...",
  "repo_path": "...",
  "current_branch": "...",
  "head_sha": "...",
  "archive_tag": "...",
  "artifacts": [{
    "absolute_path": "...",
    "relative_path": "...",
    "filename": "...",
    "extension": "...",
    "size_bytes": N,
    "modification_time": "...",
    "sha256": "...",
    "git_state": "ignored|untracked|tracked-modified|tracked|outside-repo-local",
    "classification": "PRESERVE_UNIQUE|...",
    "confidence": "high|medium|low",
    "reason": "...",
    "likely_provenance": "...",
    "in_git": false,
    "regenerable": true|false,
    "feature": "Day|Night|Micro Duck|Blender|DreamLoop|visual review|performance|other",
    "image_info": {"width": N, "height": N}  // if applicable
  }]
}
```

**`manifest.jsonl`** — One artifact per line for easy scripting/filtering.

**`summary.md`** — Human-readable summary with HEAD/tag, modification status, counts by classification, most important artifact groups, ambiguous items, cache/dependency directories that don't need preservation.

**Pitfall:** Hash giant dependency/cache trees individually ONLY if they contain candidate project artifacts. Don't hash node_modules/ file by file.

**Reuse existing provenance without upgrading trust:** When a curated manifest already records large-artifact hashes and sizes, preserve the exact assertion plus its source document/pointer and label it reported, not freshly verified. Avoid rereading giant binaries for a metadata-only task; schedule byte verification at an authorized ingest/copy boundary. Keep content-hash equality separate from specimen identity, visual acceptance and publication rights. Blind comparison keys and revealing source names remain custodian-private even when their proof labels are neutral. Git ignore rules are not a privacy boundary.

### 7. Create read-only recovery package (optional, for high-value preservation)

When the user wants a self-contained package:

```bash
# Create package directory
mkdir -p ~/quackles-recovery-package-YYYY-MM-DD

# Create Git bundle for local-only refs
cd /path/to/repo
git bundle create ~/quackles-recovery-package-YYYY-MM-DD/git-bundle/refs.bundle \
  --branches=branch1,branch2,branch3 \
  tag1 tag2

# Copy artifacts preserving directory structure
cd ~/quackles-recovery-package-YYYY-MM-DD
cp -r /path/to/repo/artifacts/* artifacts/  # or use rsync

# Verify SHA-256 of every copied artifact
# (re-hash each file and compare to manifest)
```

### 8. Verify everything

```bash
# 1. Bundle verification
git bundle verify ~/quackles-recovery-package-YYYY-MM-DD/git-bundle/refs.bundle

# 2. Bundle ref enumeration
git bundle list-heads ~/quackles-recovery-package-YYYY-MM-DD/git-bundle/refs.bundle

# 3. Restore test (in temp directory)
mkdir /tmp/test-restore && cd /tmp/test-restore
git init
git fetch ~/quackles-recovery-package-YYYY-MM-DD/git-bundle/refs.bundle \
  '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*'
# Verify branches and tags are accessible

# 4. SHA-256 verification of all artifacts
# Re-hash each file, compare to manifest entries

# 5. Final zero-change check
cd /path/to/repo
git status --porcelain
# Compare to baseline — must be identical
```

**Pitfall:** Always test bundle restore in a TEMPORARY directory, never in the working repo. The test proves the bundle is valid without touching the source.

### 9. Final report

Report:
- Archive tag (name, HEAD SHA, newly created or pre-existing)
- Local-only evidence counts by classification
- Highest-value local artifacts (groups, not every file)
- Safe-to-ignore classes (dependency/cache/regenerable)
- Local Git risk (local-only branches, stashes, worktrees, unpushed commits)
- Manifest location (absolute paths)
- Integrity check result (zero changes confirmed or not)

## Tooling notes

**Python for hashing and manifest building:**

```python
import hashlib
def get_file_hash(path, chunk_size=65536):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()
```

**Getting image dimensions (optional, when cheaply available):**

```python
from PIL import Image
with Image.open(path) as img:
    return {"width": img.width, "height": img.height}
```

**Clipboard for Wayland (when xclip unavailable):**

```bash
cat summary.txt | wl-copy
```

## Docs-versus-code promotion audits

For local branch promotion risk, use `references/docs-promotion.md`. Inspect each tip's generator and CI boundaries before classifying documentation; a generated file can become generator-owned only on a later branch. Never run a mutating or networked check during a read-only inventory.

## What this skill does NOT cover

- GitHub PRs, issues, remote branches, Actions runs, Pages deployments, review comments
- Fetching/pulling unless absolutely required to understand local repo (normally unnecessary)
- Any command that stages, commits, pushes, deletes branches, modifies .gitignore, runs formatters, regenerates assets, rebuilds the site, or cleans caches

Authorized recovery of commits that may already be on GitHub is `git-lineage-recovery`: prove the tip with `git ls-remote` (it does not update refs) and the commits API, then push only absent commits. Stay here for read-only inventory. Do not fetch or pull just to answer whether a SHA is published.

These can be done separately. This skill is strictly LOCAL evidence preservation.

## References

- `references/classification-guide.md` — Detailed classification criteria and example artifacts
- `references/manifest-schema.md` — Complete manifest JSON schema with all optional fields
