---
name: z0-public-artifact-sites
description: "Use when publishing z0 artifact sites or z0evals posts."
version: 0.1.0
author: Hermes Agent
license: MIT
---

# z0 public artifact sites and the z0evals blog

**Owner rule: z0evals publishes measurements.** Simulated turns (e.g. `devReplay`) and replay or model-based estimates are never headline evidence. Run the real system on real workloads (real provider turns, real devices) and measure; label any remaining proxy as a proxy and replace it before calling the study done. Don't propose "measure for real later, if someone asks". When a measurement replaces a proxy in an existing post, rewrite the title, subtitle, stat strip and "how sure we are" around the measured number, keep the proxy sections only as "(upper bound)"/"(proxy)" with the gap stated, and add the missing-coverage caveat (e.g. one provider so far) to the limits list.

## Where things live
- **z0intelligence artifacts:** Pages on the `gh-pages` branch of public kvnloo/z0intelligence. Each artifact gets its own subpath: `/bend-autoresearch/` (Victor) and `/k3s-fleet/` (Advith). The root `index.html` lists them.
- **Artifact sources:**
  - `/workspace/zer0/products/victor-bend-demo` (branch story-v2)
  - `/workspace/zer0/products/k3s-fleet-brief`
  - Publish with `git archive <src> | tar -x -C <gh-pages worktree>/<subpath>`, push, then wait for `gh api repos/kvnloo/z0intelligence/pages/builds/latest` to report built for that commit.
- **z0evals blog:** public kvnloo/z0evals, a Next.js static export in `web/`.
  - `scripts/build_posts.py` prerenders `posts/*.md` to `web/data/posts/*.json`. `app/[slug]` renders every post that lacks a bespoke `app/<slug>/page.tsx`.
  - The master research log is `/log/` (`web/data/research-log.json` + `research-focus.md`).
  - `preview` has diverged from `main`, so publication PRs go to `main` and Kevin merges.
  - **Preview a PR on the existing GitHub Pages site, never Vercel:** push the PR head as branch `pr-<n>` (`pr-*` support is in main's pages.yml). Pages publishes it at `https://kvnloo.github.io/z0evals/wip/pr-<n>/` next to `/`, `/next/`, `/dev/` and `/nightly/`. The `github-pages` environment admits `pr-*`. Delete the branch to drop the preview.

## Filing by area and technique
The owner's "organize z0evals" means these categories.
- **Area:** every post and log entry has exactly one, naming the system under test. Product areas come first (`hermes`, `small-models`, `generative-ui`, `device-use`, `applied-math`), then the cross-cutting ones (`memory`, `governance`, `fleet`, `research`).
- **Technique:** the second facet, 1–3 per entry, naming how the work improves the system:
  - `output-format`, `context-reduction`, `model-routing`, `local-inference`, `caching-reuse`
  - `scheduling`, `algorithmic`, `search-optimization`, `formal-methods`, `measurement`

`docs/areas.md` says which to pick. Each facet's list in `web/lib/areas.ts` / `web/lib/techniques.ts` must change together with `build_posts.py` `AREAS` / `TECHNIQUES`, and a test checks that they match. Put new research-log entries into an existing category; a new area or technique needs a reason that none of the existing ones fit.

## Dash look
Don't build from token values alone. Copy the recipes in Dash's phone tree (find it from the running Metro's cwd, e.g. `.worktrees/dash-20261020`):
- `GlassSurface.tsx`: glass fill + a top sheen gradient + a hairline border with a brighter top edge (rgba 255,255,255,.18) + a drop shadow.
- `golden-nav.ts`: gold at 68% opacity, a white-36% rim, an inset specular highlight, a bottom shade and a glow.
- Background is flat `#0c0c0a`. Selected segments are neutral glass; gold is for the nav pill and primary action only.
- Real phone screenshots are in `~/.dash/attachments`. Pixel-sample them.

## Running a research-linked evaluation before publication

1. Resolve the announcement to the primary paper, release page, implementation and checkpoint. Separate source-reported benchmark scores, analytical projections and results actually reproduced; a roofline projection is not measured throughput.
   - Check availability concretely before designing anything: `curl https://huggingface.co/api/models?author=<Org>&sort=lastModified&direction=-1`, the GitHub search API over the org's repos by method keywords, and a grep of the paper text for `release|open-source|code is|checkpoint`. Put the answer ("no public weights or code; paper says X") in the FIRST report, followed by the options: when weights/code are released, the authors' harness on the paper's model (cloud GPU if it exceeds 12 GB); otherwise a cheap training-free proxy, or re-training the method ourselves at small scale. The owner otherwise asks "is it not possible with their trained model?" next, and he prefers the faithful reimplementation over a proxy.
   - "Recreate the evals they did" means map every benchmark in the paper's eval table to run or skip on this hardware, with the reason (agentic SWE/Terminal benchmarks, 80K-token reasoning budgets and 128K+ context subsets do not fit sub-4B models on 12 GB), and run the feasible subset with the official generators/datasets at pinned revisions. Recipe in `references/attention-feasibility.md` §6.
2. Read the current source repo's instructions and model manifest before choosing the experiment. Pin the exact checkpoint and identify whether it is a base model, trained specialist or production backend; matching a model family does not evaluate the deployed decision system.
3. State the experimental scope before running. If the released method is unavailable and a proxy is useful, label it a **feasibility comparator**, not a reproduction or performance bound. Record what finding would justify the next experiment rather than silently substituting the proxy for the requested method.
4. Smoke-test the smallest cell and verify mathematical invariants before launching the matrix. Use fresh output paths, append completed batches, and make the importer reject duplicate identities and incomplete expected cells. Retain stopped attempts separately; zero completed rows means no result, not a capability failure.
5. Freeze paired trial outcomes and document the unit of analysis. Heads, layers, overlapping prefixes and multiple configurations on the same task are dependent observations; report distinct tasks/documents separately from diagnostic row counts. Derive aggregates, paired regressions, uncertainty and charts in code with a drift-check mode.
6. "Run evals with z0evals" means carry it through to a reviewable z0evals PR: study + post + issue + PR to `main` + `pr-<n>` preview link, in the same turn. The owner's next ask after a local-only handback is "link me the preview". A PR to main is not publication (Kevin merges), so this needs no extra permission; production code, other repos' remotes and live services stay untouched. A source base SHA identifies the starting tree, not new uncommitted harness code: hash the executed script before launch and preserve its exact bytes, dependency versions, inputs and raw-output digests. Keep later reporting edits separately identifiable. Stop owned experiment jobs before handing back a completed run.

**Paid compute: free credits only, never real money (owner rule).** Rented GPUs (Modal) may spend only the workspace's monthly free credit, which sibling sessions share. Before launching, state the GPU type, count, $/hr and the projected total against the remaining credit, and start `scripts/modal_budget_guard.sh` so it stops this study's apps below the credit line. Cut optional arms (e.g. the quadratic dense 10M ladder) before the cap, not after. Without that up-front statement he is surprised by parallel GPUs.

When code, image and weights ARE released but the paper's model exceeds the local GPU (e.g. 27B), run the authors' own harness on Modal: [references/released-harness-on-cloud-gpu.md](references/released-harness-on-cloud-gpu.md) (budget check, Slurm→Modal shims, offline HF pitfalls). Prefer this over a small-model proxy when the owner asks to follow the paper.

For attention-method comparators and small-scale reimplementations, use [references/attention-feasibility.md](references/attention-feasibility.md) for correctness checks, the distillation/eval recipe, shared-GPU and long-pipeline handling, Hub publication of trained weights, and interpretation limits.

Trained weights and adapters go to the owner's Hugging Face account (`kvnloo`, the CLI is signed in), not only to a local checkpoint dir; link the Hub repo from the study README and post.

## Publishing a z0evals study + post
1. Make your own worktree from a fresh `origin/main` (other sessions often hold the shared z0evals checkout), with repo-local commit identity.
2. `studies/<id>/`: `manifest.yaml` (schema `schemas/study-manifest.schema.json`: schema_version `z0eval.study.v1`, id, title, status, created, sources with repo+commit, questions, artifacts with path+kind+sha256), `README.md` (reproduce, files, what it does not show), `data/` and `scripts/`. Recompute sha256 after every artifact edit; `scripts/validate.py` checks them.
3. Import data through a sanitizing step, never a raw copy: `scripts/import_aggregates.py <ops-dir>` reading a fixed allowlist of raw files and writing only totals/medians/CIs. Trim model answers, redact provider account ids (e.g. Groq `org_…` inside 429 errors), and drop private paths, device names and internal tool names from script docstrings. Map user-named instances (ACP agent instance ids, profile names) to public families by pattern, never by listing the literal names in the script, and fail on an unmapped one.
   - Have the sanitizer write every raw string it refused to copy to a private denylist. Fail the publish if any denylist string appears verbatim in the output. Regex greps miss project names and titles, but they show up as exact leftovers. The ephemeral-ui-kit skill's `references/trace-cards.md` has a worked pipeline.
   - A number you cannot reproduce from raw data (e.g. a live-DB replay whose rows have since changed) goes in its own data file with a `provenance: source-reported` field, and the post says it was transcribed, not re-run.
4. `posts/<id>.md`: lowercase voice, frontmatter (title, subtitle, study, status, author "zer0 research", date, mock_data, toc ids matching `{#id}` headings). Link data files and downstream repos.
   - Derive every cited number in a study script (`scripts/figures.py` → `data/derived.json`) with a `--check` mode that fails on drift; copy table rows from the source write-up rather than re-rounding them yourself, so the reviewer can match them line for line.
   - When source docs disagree because they used different metrics (e.g. a noisy `/proc` counter vs an exact syscall tap), cite the consistent metric and say in one sentence why the other number differs, even if a brief quotes the other one.
   - Charts: inline SVG in a `<figure class="figure">` between `<!-- figure:<name> -->` markers that the study script splices in. Use hex colours (CSS `var()` does not work in SVG presentation attributes), viewBox about 420 wide, text at least 11 px, no long text lines inside the SVG (put notes in `<figcaption>`), so it stays legible and inside 360 px.
   - If the post accompanies an upstream post (discussion, issue comment), read the posted body and keep the post consistent with its framing, numbers and corrections; describe open upstream PRs as open, and never call an experiment's base "current main" when experiments were cut from different SHAs (list each base in the sources table).
5. Local gates (skip only the Next build, CI runs it): `validate.py`, `audit_web_source.py`, `build_site.py`, `build_site_data.py`, `build_posts.py`, and the `test_pages_publication` / `test_build_posts` unittests. Generated `web/data/*.json` stays uncommitted.
6. Create an issue, push, open the PR to `main` with the receipt block; after each push, update `head_revision`.
7. **Folding new research answers into a living study** (for example ChatGPT wave comments on a tracking issue):
   - **Read every comment yourself.** Match each to its tag by its first line, and use the comment's `html_url` as the source. For a tag with no comment, check the dispatch log and report it as pending.
   - **Spot-check the claims you will record with `gh api`:** pin equivalence (`compare/<a>...<b>` file list), current HEAD and blob SHAs, and that every named code path exists at the cited ref. Answers are model reading; only checked facts count.
   - **Edit the files:**
     - Record the reconciled pins in `candidates.json` and the manifest `sources`.
     - Add a candidate only with a named code path and a falsifier.
     - Put a candidate with no hot path on a `watch` list.
     - Record negative fits as killed candidates with `REJECTED_FIT`.
     - Append to the ledger, never rewrite it. Label local results others ran as `MEASURED_LOCAL_SOURCE_REPORTED` with `artifacts_in_repo: false`.
   - **Finish:** recompute the manifest sha256s, run `validate.py`, `build_posts.py` and the build_posts unittest, push, then patch only `head_revision` in the PR body (`gh pr view --json body` → sed → `gh pr edit --body-file`).

## Merging stalled z0evals PRs
- Integrate them on one branch first: merge each PR head with `--no-ff` in dependency order, run the python gates (`build_posts.py` catches cross-PR breakage such as a post filed under an area another PR removed), then open ONE integration PR to main. Its `validate` job runs the full `next build` + `audit_web_export`; merging it marks every included PR merged, as long as each PR's base is main (retarget dev- or stack-based PRs with `gh pr edit N --base main` first).
- A `pr-*` preview of a branch that adds required pages fails in pages.yml: the branch's `audit_web_export.py` audits the main channel built from old main. Use the integration PR's CI instead, and preview only after it lands.
- Post areas live in `web/lib/areas.ts` + `build_posts.py` `AREAS` (docs/areas.md says which to pick). T3 Code studies go under `hermes`.
- Markdown posts can open with `<div class="stat-strip" markdown="0">` stat cells and fold wide tables in `<details class="more" markdown="1">` (CSS in globals.css). Tables with fewer than 4 columns fit phones; wider ones scroll.
- Delete stale `pr-*` preview branches after their PR merges; pages.yml rebuilds every one on each run.

## Preview link before merge
The owner asks for a preview URL; offer one unprompted. Use the Pages `pr-<n>` branch (see "Where things live"), re-pushed after every PR push:
```bash
git push -f origin HEAD:refs/heads/pr-<n>
```
The `pages` run takes about 4–6 min (`gh run list --branch pr-<n>`, then `gh run view <id> --json status,conclusion`). Poll it in separate short calls (`sleep 45` or less each): long single sleeps in the terminal get SIGTERM'd under host memory pressure and lose the call. Then confirm `curl` returns 200 at `https://kvnloo.github.io/z0evals/wip/pr-<n>/<slug>/` and grep the HTML for the post's headings (add `?v=N` to dodge cache). Do the 360/390 px mobile check on this URL.

## Rules
- **Commit identity:** author as `Kevin Rajan <7121943+kvnloo@users.noreply.github.com>` (set with repo-local `git config`). Never invent a name from the `kvnloo` handle.
- **Privacy:** no device nicknames (groot/MBP/S25/S22), `/mnt` paths, tailnet IPs, private repos (oss-factory, z0bridge, sft-svlm) or health readings. Grep every shipped file, including compiled JS metadata.
- **Review before publishing:** run an independent reviewer that checks every number against pinned sources, and fix what it finds before reporting done. It reliably catches real errors; recurring ones are in `references/number-review.md`, with the brief and the in-turn run command. Rerun the review after any substantive rewrite instead of letting it review a moving file. List each corrected number in the final answer and in a PR comment.
- **Mobile check:** follow rendered-ui-qualification step 3: every viewport slice of the post at 360–393 px (touch emulation), on the `pr-<n>` preview, plus per-element overflow via `getBoundingClientRect` (SVG has no `offsetLeft`). Also log `.section-bar-label` per slice; it must name the section on screen. z0evals post-shell specifics:
  - `build_posts.py` marks tables with ≥4 columns or code cells as `table.stack` (cells get `data-label`), and phones render each row as a label/value card. The stack CSS must override the sticky first-column rule (`width`, `position`, `box-shadow`) or cells fill ~70% of the card with a stray hairline. Give `td code` `overflow-wrap: anywhere` so branch names don't clip.
  - Posts are lowercased globally. Byte units are wrapped in `.u` by `build_posts.py` to keep their case; any new unit-like token that must keep case needs the same treatment (SVG text is exempt in CSS).
  - A `.figure` is one card: strip the glass surface from the inner `.chart-svg`, and bump chart text on phones (a 420-unit viewBox drawn ~330 px wide shrinks 11-unit text to ~8.6 px).
  - Shell commands go in fenced blocks, not inline code, inside callouts.
- **z0evals builds:** run on the MBP via fleet-build. Inside the job, create a venv and install `requirements.txt`, because the MBP lacks PyYAML.
  - The local npm 12 refuses `--package-lock-only` updates, so avoid adding npm deps.
  - If the MBP sits just under its floor, exit 75 repeats; lower `--mem` to 3G.
- **z0evals CI:** `ci.yml` and `pages.yml` both have to run `scripts/build_posts.py` before `next build`. Otherwise `app/[slug]` has no params and the static export fails. The `receipt` check needs a ```yaml block in the PR body with issue, base_revision, head_revision (the exact current head) and non-empty tests.red AND tests.green (a text-only fix still states the wrong text as red). Update it after every push. `gh pr edit --body-file` triggers a fresh receipt run (it listens on `edited`); `gh run rerun` replays the OLD body and fails again. The check isn't required, so `gh pr merge` succeeds even when it fails: read `gh pr checks` before merging.
- **Harvest subagents mark almost everything `interesting`.** Derive the log's "in focus" flag from links the focus section actually cites, not from their flag.
- **Harvesting experiments into the log:** collapse per-commit run folders into one entry; skip QA receipts, chores, personal (home, health, wardrobe, productivity) and one-host incident postmortems; `interesting` is a bool in research-log.json and the log JSON is `indent=1`. When a word in the owner's request matches no workstream in the thread ("organize scrutiny"), read it as the nearest active one (here, the categories) or ask in one line. Never build new machinery, such as a multi-model review pipeline, around a likely typo: it costs a turn to tear down and he has to notice it first.
- **A server page can't import constants from a `"use client"` module** (they arrive undefined). Shared tables go in `web/lib/`.
