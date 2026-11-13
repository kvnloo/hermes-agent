---
name: making-of-case-study
description: Use when writing a project's story, making-of or pitch site.
---

# Making-of / process case study

Turn a long agent-built project into a "How this was made" post that traces the whole process and how the approach changed over time. The owner wants a short, high-level visual story with collapsible sections for anyone who wants the full depth. They especially value the comparison walkthroughs (reference vs render sheets, tiled-critic worst-tile sheets, before/after crops) as artifacts in the post.

## Procedure

1. **Locate inputs.** Find the existing process page in the site repo (e.g. `app/process/page.tsx`) and the history sources:
   - the artifacts tree (process dirs, run ledgers, round dirs);
   - repo `git log --all` and branches;
   - GitHub issues/PRs;
   - past sessions (`session_search`);
   - skills that encode lessons learned.

   Ask the owner for any external style reference link rather than guessing. Agency case studies on Behance (e.g. BUCK's Airbnb pages) are a good pacing model: big visuals, concept -> references -> look dev -> technical breakthroughs -> credits.

2. **Fan out history tracers, one per lane** (~5 lanes: site/product, rendering foundations, the lead scene's loop, sibling scenes and the hardest scene, infrastructure plus how the agents worked).
   - When the owner asks for Sonnet workers, run them as Hermes one-shots, because `delegate_task` children use the profile's pinned model:
     `hermes chat --oneshot -Q --provider anthropic -m claude-sonnet-5 -t file,terminal,vision,session_search,web --max-turns 120 --query-file prompts/<lane>.txt > trace/<lane>.log`
   - Run all lanes in parallel from one script (`( ... ) &` per lane, then `wait`), started as a background terminal job with notify.
   - Each prompt says READ-ONLY and names one output file. Each trace has six sections:
     1. dated timeline with evidence (path/commit/PR/session id);
     2. learning arc: approach -> what went wrong -> what was learned -> what changed, with numbers;
     3. owner corrections and decisions, short quotes with dates;
     4. 12-25 best artifacts with absolute path, pixel size and caption, all verified to exist;
     5. tools, scripts and skills that emerged;
     6. contradictions and gaps.

3. **Check the traces.** Before writing, check word counts and section presence. Run a small Python check that every cited image path exists; hand missing ones to the writer to replace or drop.

4. **One writer agent** builds the page on a new local branch from the branch the site will ship from. Local only: no push or PR without the owner's OK. The brief:
   - **Structure:** the top level is a hero plus ~8-12 chapters, each a few sentences plus one strong image. Every chapter has collapsible deep dives built on native `<details>/<summary>` (keyboard, screen-reader and no-JS friendly): timeline, learning arc, corrections, artifact gallery with captions.
   - **Content:** keep it in one structured data file (e.g. `content/process.ts`) so it is easy to update when unfinished parts land; mark them "in progress".
   - **Accuracy:** verify every number and claim against the cited primary evidence; where traces disagree, check the source; list unverifiable claims in the report.
   - **Quotes:** use only a few direct owner quotes, tasteful, and list them for owner review.
   - **Images:** copied, never moved; WebP at most ~1600 px wide, quality ~82; fixed dimensions, lazy loading and alt text; a total budget of ~25 MB; no local paths or private data on the page.
   - **Style:** the site's own typography, colour tokens, spacing and nav, at the same premium level as the rest of the site. The owner rejects anything that looks like a toy.

5. **Verify.** Unit tests, typecheck, lint on touched files, static build (including a non-empty basePath), the existing page contracts, and headless screenshots at desktop 1440 and mobile 390 (top, an open deep dive, a gallery). Also a Lighthouse mobile run: full-size sheets give a slow LCP on phones, so serve responsive smaller sizes before publishing.

6. **Show it.** A child's background server dies when the child exits. Relaunch the static server yourself (`python3 -m http.server <port> --bind 127.0.0.1 --directory out` as a background process), check it returns 200, and open the page in the owner's browser.

7. **Report.** Give the branch and commit, chapter outline, image count and total weight, the quotes for approval, perf numbers and the open layout questions.

## Personalized story/pitch site for one reader

The owner rejects a page that just shows the artifacts. It reads as shallow and generic. The page must tell why the work exists and where it inevitably leads, in the reader's own terms.

1. **Two research workers in parallel, read-only, each writing one markdown file:**
   - **Reader dossier:** background and timeline, GitHub activity over the last 3 months, a few hundred X posts clustered by theme with short dated quotes and links (`twitter-cli`, e.g. `twitter user-posts <handle> -n 200 --json`), what resonates versus what makes him close the tab, and his current open problems.
   - **Story brief:** the repo map with public/private visibility, a dated milestone timeline, the owner's goals in his own words, an IMPLEMENTED / DRAFT / DIRECTION chain from foundation to payoff, and the experiments to link.
   - Both workers: never invent URLs; every link must be fetched or returned by a tool.
2. **Give every diagram its intent.** Answer "what is this meant to convey?" before drawing it. Mine the model for the motive: for example, a law or guard table whose entries record the real incident they prevent, with counts. Lead with that, not with the shape of the graph.
3. **Run the real artifact.** When the work compiles to something the browser can run (e.g. Bend-emitted JS plus its JSON adapter), let the reader execute it and try to break a rule, rather than replaying a canned animation. Label anything that is only a projection.
4. **Link, don't re-display.** Link evals, reports and PRs with one exact number and a caveat each, instead of rebuilding their charts.
5. **Use the owner's real design system.** Take it from the build he actually runs plus his real screenshots, and copy its component recipes (for Dash, `company-os-visual-language` → `references/dash-web-port.md`). Don't take it from a design doc's summary or from tokens alone: matching colours without the glass and pill treatment still reads as wrong to him.
6. **Publish only after review.** Link only public repos. An independent privacy and accuracy reviewer must pass the page: no private paths, hosts, people or location; numbers match their sources; proof and maturity limits are kept. Show the owner before publishing. Write the page so it already passes these checks, which reviewers reliably fail:
   - **Shipped bundles leak too.** A byte-identical copy of an already-public file still fails the no-host or no-device rule. Scan every shipped file, compiled JS and metadata included, not just the page source. Republish a minimized build that is checked against the original and describe it as recompiled, not "byte-identical".
   - **No universal claims:** say "selected modeled loops", not "every step". Label designs as proposed or not built. Don't say demo rows feed a real queue.
   - **Name the authored code:** say what comes from emitted code and what an authored adapter labels. Call a recorded tape playback.
   - **Counts mean exactly what they measure:** "no recorded X" is not "X was reused" or "vanished". Keep the evidence-gap caveat next to the number.
   - **Mark invented dialogue** as hypothetical and illustrative. Use the scenario's own vocabulary (e.g. off, not asleep). Don't publish the owner's inventory counts unless he has approved them.
   - **Quote exactly:** no punctuation inside the quote marks that the source lacks, a date next to each quote, and attribution to the specific project quoted.
   - **Simplified diagrams say so:** list the valid edges they leave out.
   - **Demo inputs must match their labels:** test every "stale" or "wrong" shortcut at the edge values (e.g. `max(0, head-1)` equals the head at 0).
   - **Check links:** `curl -sI -L` every href. Use the DOI when a publisher returns 403.
7. **Take ownership cleanly.** If another agent built the earlier version, have it stop, write a handoff (sources, review rules, publish route) and stop pushing before you edit.
8. **Phone-first before publishing.** The owner reads these on his phone and treats "not mobile-friendly" as urgent. Play every interaction at 360 and 390 px, not just the static layout, and keep the result of each move in view (see `rendered-ui-qualification`, mobile interaction rule).

## Product catalogs and personal app stores

1. **Resolve the existing portfolio before designing.** Recover the checkout from history, confirm its Git remote/worktrees, read its UI and deployment workflow, and add a sibling route rather than replacing an existing showcase. Check active product and film owners; reuse their artifacts without duplicating implementation.
2. **Build a coverage ledger before cards.** Combine the current public profile, canonical component/suite registries, prior work inventories, and project-specific owner history. Track each candidate as included, private/excluded, superseded, or evidence-missing. Paginate repository discovery until the intended scope is covered; an arbitrary metadata window is not an inventory of everything.
3. **Design an Explore surface.** Use browse/search, meaningful categories, product detail pages and direct try/watch actions. Keep content in a structured manifest with stable IDs, source links, role, maturity, demo type and media provenance. Distinguish original products, downstream modifications and upstream collaborations.
4. **Give each product its own evidence.** Recover the actual feature work, screenshots, existing films and playable surface before writing its page. A monogram plus generic repository description is an index entry, not a finished product showcase. Report media and playable-demo coverage separately from the number of generated detail routes; one shared film does not satisfy a catalog-wide video requirement.
5. **Separate launch targets from source links.** A fork's homepage often points to the upstream author's service, so never present it as the owner's deployed prototype without verification. Label runnable demos, interactive mockups, recorded playback, audit snapshots and source-only projects distinctly. HTTP success establishes reachability, not correct content, served revision or working interactions.
6. **Keep discovery private and publication allowlisted.** Private reports may identify candidates, but do not copy their prose, inventory metrics, operator paths or captures into the bundle. Include only reviewed public-source records and separately approved media. Preserve original media and credit upstream authors.
7. **Verify navigation and behavior, not just data.** Check the deployment copy rules and subpath-relative assets; test deep links, search, combined filters, empty state, dialog close/focus restoration and video pause on close. Exercise pointer and keyboard paths at desktop and phone widths, then inspect screenshots. Scripted DOM events and route loops are useful code checks, not substitutes for rendered visual review or user-action acceptance.
8. **Deliver against the requested coverage.** Keep the catalog's missing products, per-product media gaps and unverified demos explicit. Call a broad first index a partial implementation until the intended inventory and product experiences are covered; route count alone is not completion. Keep local preview, committed source and public deployment as separate delivery states.

## Archive-backed application portfolios

- Pin the contribution archive ref and database digest before aggregating. Count public discussion comments, reviews, inline comments, issues and PRs separately; distinguish upstream repositories from account-owned coordination and fork work. Activity totals do not establish accepted changes, manual authorship, or complete historical coverage.
- Treat closed PRs as lineage questions, not failures or merges. Read supersession comments and successor changes before crediting salvaged work; preserve the authors of the stronger replacement.
- Parse the full available public snapshot programmatically, then read selected substantive conversations. Disclose that selection rather than claiming every archived comment was read. Select cases that show reproduction, review response, changed hypotheses, maintenance and collaboration, not only volume.
- Lead an employment story with the person's motivation and the product area they want to own. Let visual projects, native interaction work and reliability follow-through support one thesis instead of producing a chronological warehouse of repositories.
- Keep private source, local preview and recipient-accessible deployment as separate states. A private repository URL is not an application website link; noindex is not access control. Obtain publication approval and review source captures/excerpts for operator details before public hosting.
- Reserve the personal-recording slot for the actual person. Provide short speaking notes and real b-roll boundaries; never fabricate their face, voice, interview or an employer endorsement. Mark proposed first-person copy for owner review.
- When browser action selection is unavailable, preserve the blocker and use DOM simulation only as a separately labeled code-level check. Render screenshots remain visual evidence; simulated clicks do not become browser or device acceptance.

## Expert handoff site from a handoff doc

When the owner asks for a site that carries a handoff doc to one expert (e.g. a k8s reviewer):
- Make each doc section a chapter, and use the doc's own numbers.
- Make the single most explanatory failure interactive (e.g. an eviction-threshold calculator that shows why pressure never cleared).
- Under each question, link what our own agents' research already concluded, labelled research-only.
- Add a copyable plain-text brief that the reader's coding agent can use.
- Before using a number, check it against the source PR or issue. Footnote counts that disagree between sources rather than picking one silently.
- Replace device nicknames with roles, even when public PR titles contain them.

## Research log: a master post over many studies

When the owner asks to bring a research blog up to date and add one master post that tracks every eval, goal and idea:
1. **Inventory the publication gap first.** List posts per channel branch (`git ls-tree origin/<b> posts/`), study branches whose diffs add `studies/` or `posts/`, and open study PRs. Check how the site renders posts. If each post needs a bespoke page, markdown-only posts were never published, so add a generic renderer for `posts/*.md` before writing anything. Prerender with a dependency the build already installs, rather than adding a new package that changes the lockfile.
2. **Fan out read-only harvesters, one per area cluster** (memory/cost, governance/laws, speed/UX, and work outside the repo). Each writes `entries.json` with id, title, area, question, status, date, finding (exact numbers), caveat, pinned links, why it matters and post slug. Each drafts full posts only where evidence is frozen or there's a clear negative result, in the blog's existing voice and frontmatter. Health-adjacent studies get engineering aggregates only.
3. **Derive "in focus" yourself.** Harvesters mark nearly everything interesting. Flag an entry as in focus only when the ranked focus section cites one of its exact links (or one of its PRs or artifact pages), and show a neutral "why it matters" line on every card.
4. **Don't silently drop updates.** A harvested update to a post that already has a bespoke page won't render. Publish the new sections as a separate dated update post that links back to the original.
5. **Review the numbers independently before the PR.** One read-only reviewer opens 2–4 cited sources per post and checks every headline number, plus a sample of log entries and every link's HTTP status. Harvested drafts reliably mislabel a denominator (a total rate presented as the usable rate) or flatten a small change into "no change". Re-check each flagged number against the source JSON yourself before editing.
6. **Gate the renderer with a test** that prerenders every post (title, toc anchors present as heading ids, lede extracted, wide tables wrapped) and checks that log entries are complete, have unique ids and link only posts that exist. Run it on the base revision for the red half of the receipt.
7. **Run a privacy grep** over every post and data file, then split the commits (renderer, restyle, content, review fixes). Follow the repo's channel rules: agents open the PR, and the owner merges to the default branch. If the feature channel has drifted from the default branch with unrelated conflicts, don't resolve someone else's drift. Target the default branch as a maintainer-review PR, as earlier publication PRs did, and say why in the PR.

## Publishing several artifacts to one Pages repo

Use one subpath per artifact (e.g. `<repo>.github.io/<site>/<artifact>/`). Make the root a small index linking all of them, styled like them, instead of a redirect to one.
1. Check `git rev-parse origin/gh-pages` equals your local branch.
2. Add a worktree on `gh-pages` in scratch.
3. Extract the source branch: `git archive <src-branch> | tar -x -C <artifact>/`.
4. Commit with the source SHA in the message and push.
5. Poll `gh api repos/O/R/pages/builds/latest` until `status=built` for that exact commit.
6. `curl` every page and asset with a `?v=<sha>` cache-buster, then rerun the headless desktop and mobile pass against the live URL.
7. Re-sync the shared design CSS into sibling artifacts when one gets a fix (e.g. mobile rail changes).
