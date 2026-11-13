---
name: job-application-materials
description: "Use when drafting job emails or portfolio sites for Kevin."
---

# Job application materials (emails, cover letters, portfolio sites)

## When to Use
Kevin pastes an application email/cover letter draft, asks to "pull context on the job app",
or wants a portfolio/contribution site changed to support an application.

## Procedure
1. **Pull prior context before editing.** Canonical repo:
   `/mnt/zer0models/workspace/zer0/products/hermes-jobapp/` — read `docs/` (latest
   `EMAIL-DRAFT-*.md`, `APPLICATION-PACKET.md`, `STORIES-*.md`, `docs/recovered/` handoffs).
   Then `session_search` ("<company> job application") for decisions made since. The recovered
   handoffs hold hard rules (role choice, which number leads, who is/isn't recruiting, which
   inbox is the door); check a new draft against them and name any conflict in one line.
2. **Treat his pasted draft as settled.** Edit only what he flags plus typos; don't rewrite
   his voice or restructure. Give the replacement sentence/paragraph ready to paste.
3. **Refresh every number live** with skill_view(name='github', file_path='references/contribution-metrics.md').
   Numbers in old drafts are stale; never reuse them.
4. **Convey depth before tallying breadth.** Describe product surfaces, architectural problems,
   and work carried across project boundaries; a repository count alone understates sustained work.
   Keep only a few meaningful numbers when they help. Distinguish issue triage waves, technical
   comments, PR reviews, authored PRs and authored/co-authored commits on main; none substitutes
   for another. Never infer user reach or impact from activity counts, and don't cite the GitHub
   calendar total (private/own-repo padding).
5. **Check the employer's current application instructions before packaging.** Read its careers
   and relevant role pages; return the required inbox, subject format and materials with source
   links. Match the role to Kevin's stated intent rather than silently applying for adjacent roles.
   Frame solo-founder range as willingness to work across product, design, engineering,
   infrastructure and onboarding, not a claim of mastery of every role or multiple applications.
6. **Save and show the scoped revision.** Preserve the prior settled draft when making a new
   version, record evidence sources outside the email body, link the full draft, and show changed
   paragraphs ready to paste. Keep the opening, structure and closing unless explicitly changed;
   a request for one list item should remain one list item, not another sentence. Reviewing or
   finalizing a draft is not permission to send it. When Kevin asks for just a sentence or the
   missing paragraph, return only that paste-ready text; omit explanations, repeated draft links
   and status boilerplate. When he asks where to put an addition, identify the exact paragraph
   it replaces or follows rather than rewriting the whole email.

## Voice and product thesis
- Ground breadth in what the apps do for people: connect agent frontends with concrete uses such
  as video production, garden management and smart-home device visualization. Distinguish apps
  built on Hermes from changes landed in Hermes core, and ongoing work from shipped capability.
- Describe ephemeral UI as a **human-facing** immersive interface, not an interface for the agent.
  Explain how widgets, visual comparisons and video make context quick to understand and act on
  instead of forcing the person to read a wall of text. Avoid portraying a chat box alone as the
  intended product experience.
- Explain flow as context transfer in both directions: rich output helps the human grasp state;
  speaking, drawing, pointing and selecting help the model understand intent without a long
  written prompt. Pair predictable deterministic controls with context-specific ephemeral UI;
  they should feel continuous and manage attention. Group flow adds multiple humans and agents
  coordinating work through conversation; it does not replace this individual interaction thesis.
- Connect the agent's environment to the human experience: repositories preserve decisions,
  working state and evidence as memory; infrastructure removes avoidable bottlenecks; small-model
  work should give larger models room to do great work, not merely advertise cost savings.
- Use `z0` in application prose when discussing Kevin's broader work. Keep detailed internal
  project names for evidence notes when they would distract the recipient.
- Calibrate commercial interest to the concrete signal Kevin supplies. If contacts are asking
  about enterprise support for their companies, say that directly; don't dilute it into personal
  app adoption or inflate it into promised contracts, a sales pipeline or signed customers.
  Prefer a natural statement of inbound interest followed by willingness to help bring Hermes
  into those environments. Keep this as evidence of cross-functional range, not an unrequested
  application for a sales, product-management or forward-deployed role.
- Place event gratitude and enthusiasm for learning from a named team member in the closing
  when requested. Replace an existing generic enthusiasm paragraph rather than stacking both,
  so the ending stays personal without repeating the same sentiment.

## Portfolio / contribution site
- Public site: `kvnloo/gh-contrib-archive` → https://kvnloo.github.io/gh-contrib-archive/
  (Next static export, Pages via workflow; `data/public.db` is the public-safe DB). Check its
  last commit date — its data goes stale; say so when linking it.
- Direction Kevin wants: a featured section of his pinned OSS repos; each repo page takes that
  project's own site theme and lists in-progress work (open PRs with actionable status, most
  actionable first), landed work grouped by area, and collapsed discussion — strong attention
  management, not a flat ledger. Pinned repos come from his profile (scrape, see reference).
- Multi-hour builds: confirm before starting; delegate_task needs his approval (Codex billing).

## Pitfalls
- Keep private data rules: public sites show public-repo detail only; real usage/trace numbers
  need his OK before going public.
