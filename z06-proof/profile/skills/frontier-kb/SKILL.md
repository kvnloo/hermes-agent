---
name: frontier-kb
description: Unified public-research knowledge base. Search and write notes via Postgres CAS. Use when the user asks about harness research, SWE-bench, SWE-2, secrets/portals, or to store a literature/permanent claim. Do not write markdown files in the git vault under contention.
---

# frontier-kb

Operational store is Postgres. Git/Obsidian is the review export.

## Connect

DSN: env `FRONTIER_KB_DSN` or `DATABASE_URL`.

- On host 0 (groot): loopback `127.0.0.1:55442`
- On mbp / PAIR-routed agents: Tailscale `100.113.138.100:55442`
- Password lives in `~/.config/frontier-kb/env` (mode 0600). Never paste it into chat or git.

Writer id: `KB_WRITER=<harness>-<host>` (example `omp-mbp`, `hermes-0`, `firstmate-mbp`).

CLI (from the frontier-kb checkout):

```
python scripts/kb_store.py search --q "SWE-2"
python scripts/kb_store.py get --id perm-20260910-swe-2-is-a-posttrained-model
python scripts/kb_store.py put --id <unique-id> --path literature/<file>.md --title "..." --type literature --body "..."
python scripts/synapse_loop.py fire --id <note-id> --actor $KB_WRITER --kind agent
python scripts/synapse_loop.py loop
```

Human learning cluster: [[domains/learning-acceleration]]. GraphQL contract: `graphql/schema.graphql`. Frontend: `kvnloo/humanity-vault`.

## Rules

- New notes: unique `id`. Never reuse an id.
- Updates: `put --cas <version>` from `get`. On `cas_conflict`, re-get and retry.
- Do not `write()` `atlas/home.md` or `domains/*.md` from 100 agents. Those are regenerated from `links`.
- `ingest` / `export` are operator/batch only (advisory lock). Agents `put` / `get` / `search`.
- Keel SQLite is the mesh envelope log, not this store. NVIDIA PAIR (Personal AI Router) is the inference router. Neither replaces `FRONTIER_KB_DSN`.

## Schema (required frontmatter)

`id`, `title`, `type`, `status`, `created`, `updated`. Types: `literature`, `permanent`, `harness`, `moc`, `inbox`.
