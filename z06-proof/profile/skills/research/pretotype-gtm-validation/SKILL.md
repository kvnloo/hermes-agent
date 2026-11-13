---
name: pretotype-gtm-validation
description: Use when planning pretotypes, ICP or a sales pitch.
---

# Pretotype and go-to-market validation

For turning a product idea into an ICP, positioning, a sales motion and a set of cheap demand tests (pretotypes, demo videos, fake doors) before building the real thing. Kevin builds these for agency/B2G products as well as consumer ideas.

## When to Use
- Asked who the ICP is, how to sell or pitch a product, or what a pitch deck should contain.
- Asked to build pretotypes, mock demos, demo videos or fake-door pages to validate demand before real functionality exists.
- Pair with `company-os-visual-language` for any visual artifact in Kevin's style.

## Procedure
1. Re-anchor on locked decisions first: read the project's anchor/brief artifacts and repos (`gh repo view`, ANCHOR/ADR docs). If the new direction contradicts a locked scope or an earlier brief, name the conflict and its owner instead of silently building on it.
2. Ground the buyer in primary public documents, not blog summaries. For public agencies, search the agency site for board/committee packets: quarterly operations reports (KPIs, peak speeds, revenue, trip mix), contract amendments (what they already pay for, e.g. enforcement staffing), pilot reports and vendor project pages (who is already engaged). Extract exact numbers with their source URL; these anchor demos and pitch slides. See `references/b2g-buyer-research.md`.
3. Map the ICP as roles, not names: economic buyer (board/committee + program office), day-to-day users, champions, influencers (county commissions, integrators, consultants), and incumbents to partner with rather than attack.
4. Position with April Dunford's order: competitive alternatives (usually status quo) first, then unique attributes, value themes, best-fit customers, category last. Pitch = setup (market point of view) then differentiated value.
5. Write each idea as Savoia's XYZ hypothesis ("at least X% of Y will Z"), hypozoom to a local xyz testable this month, pick one pretotyping technique per idea, and define the skin-in-the-game signal that counts (money > reputation > time; opinions count as zero).
6. Write Mom Test interview scripts per persona: questions about their past behavior and current workarounds, no pitching, and every call ends in a concrete commitment or advancement.
7. Build the pretotypes as one repo: docs (research, ICP, positioning, playbook, scripts), one brief per pretotype (persona, pain evidence, XYZ, technique, demo shot list, metric, CTA), real geometry/assets with mocked metrics, demo renderers, recorded videos and a gallery with a fake-door CTA per pretotype.
8. Verify every rendered demo with real screenshots or recordings before reporting.

## Rules
- Watermark every frame of mocked data as simulated and never put invented accuracy, savings or performance figures in front of a buyer; leave those slots visibly blank until measured. Real public figures may be shown with their source.
- Use real geometry and real asset locations (roads, cameras) with mocked metrics on top, so the demo feels concrete without claiming data you do not have.
- Do not pitch into a lane where the buyer already has an engaged vendor; reframe as complementary and list that vendor as a partner.
- Keep the repo name generic while the product name is open. Before proposing any brand name, web-search it for existing companies in adjacent markets; most short compound names are taken.
- Create project repos in the canonical products store (`/mnt/zer0models/workspace/zer0/products/<project>/<repo>`), private on GitHub by default, with repo-local git identity (`git config user.name/user.email` in the repo, never global).
- Decide low-stakes choices (codenames, structure) yourself; ask only about visibility/publication or locked constraints.
- Expand every agency or buyer acronym the first time it appears in a message or artifact ("BAIFA, the agency that runs the I-880 Express Lanes"); the user researches the market through you and will not know the acronyms.
- When asked for brand ideas, give 4-5 names with a mark, a tagline and a one-line conflict check each, and recommend one; let the brand be swappable in demos rather than baked into assets.

## Building the account list and CRM
- Build the account universe from public program lists, not search: grant/award lists (e.g. Caltrans Local HSIP funded-project xlsx, USAspending API by assistance listing for federal grants) joined to population and the product's own measurements. Score in a script with the criteria in code and a `why` column per account; rank, don't hand-pick.
- transportation.gov award pages block curl and the browser (Akamai 403); use `api.usaspending.gov/api/v2/search/spending_by_award/` with `program_numbers` and `recipient_locations` instead.
- CRM: CSV in the project repo is the source of truth; Kevin's local Twenty CRM (`/workspace/zer0/services/twenty-crm`, workspace `company_zer0`) is a mirror. Its API key must be created by a human; ship a `--export` (Twenty CSV import) path plus an idempotent `--apply` sync that waits for the key file.
- Contacts: record source URL, date and confidence per person; publish email/phone only when an official document does.
- Real-data pretotypes (e.g. a per-city data health check) may show measured facts about public data, but product-accuracy claims stay limited to the product repo's claims register.

## References
- `references/frameworks.md` — condensed Savoia, Mom Test, Dunford and govtech pilot rules with the technique table.
- `references/b2g-buyer-research.md` — where to find agency buyer evidence and what to extract.
- `references/ca-crash-safety-b2g.md` — California crash-safety programs, incumbents and beachhead (CrashIQ).
