---
name: local-usage-sync-audit
description: Use when usage totals or a local usage meter look wrong.
author: Hermes curator
license: MIT
version: 0.1.0
metadata:
  hermes:
    tags: [usage, sync, collectors, audit]
    related_skills: [systematic-debugging]
---

# Local usage sync audit

## When to Use

Use when a dashboard or `sync` command is missing models, days, or harnesses, when a quoted total or share looks too small, or when a local usage bar is blank or a provider shows disconnected. A blank bar is not a token-sum miss — use "Blank bar or disconnected provider" before re-summing. The goal is a labeled miss (path gone, path not passed to this command, schema drop, no adapter, rank-metric mismatch, a slice quoted as the whole window, an empty config shadowing a real one, or a fingerprint block blamed on the key), not a restatement of the unit file.

Do not print session text, credentials, or a full sync payload. Report model ids, day counts, and token sums only.

## Procedure

1. Identify the running collector, its actual data sources, and the code revision it serves before editing. For T3, inspect the server's open database and persisted usage-scan source roots rather than assuming the checkout or legacy database is live. Treat Cribble and T3 as independent collectors; importing a conversation does not establish usage coverage. Then read the installed command's argument parser and the scheduled unit side by side. A directory list in the unit is not what a foreground sync scans. If collector path flags are rejected unless the run is the scheduled/background form, the interactive command uses only the process environment (`HERMES_HOME` and similar), not the unit's list.
2. Stat every configured path and every live sibling the program could scan (profile dirs, not just the roots named in the unit). A configured path that does not exist is a miss. A live home absent from the list the command actually reads is also a miss.
3. Resolve symlink chains with `readlink -f` before calling a store missing. A moved directory that still resolves is present. Keep looking for the real miss.
4. When the user names the harnesses a model comes from, verify each named store separately. Finding the model id in one store does not prove the others are counted.
5. Inventory harness homes the collector may or may not know: Hermes, Codex/ChatGPT desktop, Claude, Grok, Gemini, Kimi, OpenCode, Cursor, and any local CLIs with their own data dirs (for example omp, dsh). A home with transcripts and no collector adapter is invisible.
6. Run the collector offline (`--json`, no upload) on the suspect home and on the default home. Then open the uploader's normalizer and see which fields become the named model list. If the collector takes one home env var, do not comma-join homes into it. Scan the harness-specific subcommand once per home. Run the unified daily report once, with that env var set to a nonexistent path, so an unset value cannot fall back to the default home and double-count it.
7. Report the miss class and the rank metric. Quota exhaustion is not token volume. All-time history can still name an older model first even when the recent window is the missing model. If the collector prices an unknown model id at zero, that is a missing catalog row, not the model's price. Say the id is unpriced. Never call the model cheap, lower-cost, or free. A cost ranking will not match a token ranking, and a cost chart will bury the unpriced id.
8. Before quoting or subtracting totals, align host/device set, reporting window, time zone, token-field semantics, and deduplication. Label recovered historical receipts as historical; do not substitute them for a fresh comparable baseline. Name the source, the days that have files, the days that do not, and the field summed. A model total from one collector for the days that exist is not the week's usage across harnesses or devices. If the user says the week is too small, re-sum that field and list the other named stores before answering.
9. Read the card's own labels before interpreting shares. Bars that do not sum to 100%, or that say partial or legacy, are not a measured harness split. Open the wire builder: if per-agent token counts are stripped and only a name list plus a day total is uploaded, the site cannot attribute the day.
10. For Codex rollouts, sum only `token_usage_record.payload.usage`. See `references/rollout-token-fields.md`. Do not sum nested copies, `turn_token_usage`, or every `thread_token_usage`.
11. If a displayed total fell after a replace-in-place sync, the rewritten days got smaller. Check the card's device count; other devices are not replaced. A hard `--all` day cap is not unlimited history. Compare the oldest local session date to the uploaded range before saying history is complete.

## Blank bar or disconnected provider

A blank desktop usage meter, or a provider that shows disconnected, is not a collector-path miss. Do not restart the bar or re-sum tokens until the CLI error and the provider response body are known.

1. If the CLI says the config is not in the correct format, stat the config path the tool prefers once a file exists. A zero-byte or whitespace file shadows a real config and fails decode; a missing file often validates. Copy the real config over the empty file, mode 600. Do not symlink that runtime file into a synced dotfiles tree if it can also receive a session cookie.
2. A provider HTTP 403 whose body is Cloudflare error 1010, or another bot challenge, means the client was fingerprinted. Python urllib's default User-Agent is a common cause. Retry the same key with a normal User-Agent before rotating the secret or rewriting config. Set that User-Agent in the local fetcher.
3. Load still-unset provider keys from the vault into the refresh process only. Do not write a secrets file, do not copy a key into config, and do not print key material. If the vault entry name and the fetcher's env var differ, map the existing entry. Do not create a second secret to match a name you invented.
4. Done is the cache the bar reads, not the wrapper exit code. Confirm the connected flag, model count, or remaining balance in that file. Restart the bar process only if it keeps a stale widget snapshot.

## Claude subscription usage with an inference-only token

A meter reporting "Claude OAuth access token missing" (codexbar `--source oauth`, burn-pace) means none of the Claude config dirs holds a login.
1. Check each config dir's `.credentials.json` without printing secrets: `claudeAiOauth.accessToken` length, `expiresAt`, refresh-token presence and `scopes`. An empty token everywhere means logged out; the session readers still work.
2. A long-lived `claude setup-token` token (`sk-ant-oat…`, often the `ANTHROPIC_TOKEN` Hermes runs on) carries only `user:inference`. `CODEXBAR_CLAUDE_OAUTH_TOKEN=<it>` fails with "scope requirement 'user:profile'". Don't keep re-minting tokens to fix that.
3. Read usage from inference response headers instead. Send one `max_tokens: 1` Haiku call to `/v1/messages`:
   - Auth: `Authorization: Bearer <token>`, `anthropic-beta: oauth-2025-04-20`, and the Claude Code system prompt.
   - Usage: read `anthropic-ratelimit-unified-7d-utilization` and `anthropic-ratelimit-unified-5h-utilization` (each a 0–1 fraction) plus their matching `-reset` headers (epoch seconds).
   - A 429 still carries these headers, and a window's headers are absent while it is inactive.
   - Map them to codexbar's row shape (`usage.secondary` = 7d with `windowMinutes: 10080`; `usage.primary` = 5h with 300) so `z0int.posture.pools_from_codexbar` consumes them unchanged.
   - Cache the probe for about 10 minutes.
   `~/.local/bin/burn-pace` implements this as its fallback (`claude_from_headers`).
4. When two stores hold differently valued tokens (a profile `.env` and the BWS scope), compare them by hash prefix, and prefer the one the live process has (`/proc/<pid>/environ`, names and hashes only). Report the duplicate so it can be removed; don't silently pick one.

## Pitfalls

- Host layout since 2026-11-01: `~/.claude` is a symlink to `/mnt/zer0models/home-offload/kvn/claude-home`, the single personal home (the old `~/.claude-home` was merged in and removed). `~/.claude-work` is the separate work (team) home; never merge it. Collectors list exactly these two. Adding the physical path as well as `~/.claude` scans the same files twice.

- Do not treat the scheduled unit as the foreground command's config. Flags reserved for the background run are not applied to an interactive `sync`, so the shell's `HERMES_HOME` (often one profile) is the whole Hermes scan.
- Do not comma-join Hermes homes into `HERMES_HOME`. ccusage keeps one directory from that string, so every other home is dropped. Scan `ccusage hermes daily` once per home. Do not loop unified `daily` per home: that report also contains Codex, Claude, and Grok, so those totals multiply by the home count. An unset or empty `HERMES_HOME` falls back to `~/.hermes`; a missing path excludes Hermes from the unified scan.
- Scope a comma-separated `CLAUDE_CONFIG_DIR` (accepted by ccusage/tokenmaxxing) to the collector process only, never to a shell or shared unit. Claude Code reads the whole string as one path. It then creates a literal directory like `~/.claude,/home/...` and reports "Not logged in". A directory with a comma in its name proves the leak.
- Stop the sync timer before a corrective full upload. A later `--days N` run replaces those days in place with whatever the collector emits then.
- Do not stop at "the symlink still works." Follow the chain, then diff configured roots against live profile siblings. The current profile is often the one never added to the list.
- If source files contain the model id but the dashboard does not, compare JSON shapes before blaming paths. A `models` object keyed by model name is not a `modelsUsed` or `modelBreakdowns` array. The uploader drops a non-array, so those tokens upload unlabeled and cannot win a named-model ranking.
- Hermes usage for this host is in `state.db` table `session_model_usage` (model, call count, token sums, first_seen, last_seen). Empty `sessions/*.jsonl` does not mean the profile has no usage. Query aggregates only; do not read message text.
- ChatGPT desktop session logs on this host are Codex rollouts under `~/.codex/sessions`. `~/.config/Codex` is the app profile, not the usage ledger.
- Extra Claude config dirs set only on the scheduled unit are skipped by an interactive sync unless that env var is exported in the shell.
- Never narrate a missing catalog price as the model's cost. A $0 booking for an unknown model id is a hole in the price table. The user hears "lower cost" as a claim about the model.
- Do not defend a share the card marks partial. Names without per-agent token counts cannot produce a real harness split. A 0% or 1% bar is an attribution failure until the wire payload carries counts.
- Do not answer "is that the whole week?" by repeating the slice already quoted. Re-sum the field, list missing days, and add the other named stores.
- Verify Pi-family directory discovery against both Pi and OMP's native history roots; a compatible transcript parser does not imply discovery of the other harness's directory. Before widening discovery, check representative usage records and preserve explicit directory overrides so an isolated account does not silently become a whole-home scan.
- Inspect the usage ledger's temporal granularity before building a daily reader. When `session_model_usage` contains cumulative session/model/task counters with first/last timestamps, do not assign the lifetime counter to its last-seen day: that invents daily attribution. Require dated events for time-window charts, or expose coarse lifetime accounting separately and label it.
- Do not scan a Hermes root `state.db` and a profile that already contains those session ids. Confirm overlap before adding a home. Retired profiles may exist only as `state.db` inside a backup archive: extract the usage DBs, confirm ids do not overlap live sessions, and point collector config at that root. Do not restore them as live profiles.
- Patches inside the installed package are wiped by a package reinstall. Durable path lists belong in user collector config, not only in the unit's ExecStart.
- Do not debug the bar widget while an empty config file is what the CLI is decoding. The overlay is not the break until the CLI validates.
- Do not print a key to prove it loaded. Presence is a boolean. A 403 with the key present is not a bad key until the response body is read.
- Do not upstream a User-Agent or vault-load change that only the local fetcher needs. File upstream only for a contract reproduced in current upstream source.
