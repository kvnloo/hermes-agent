---
name: huggingface-hub-storage
description: "Use when storing or copying data in HF buckets."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [huggingface, buckets, datasets, storage, privacy]
    related_skills: [secrets-manager-bws, public-repo-snapshot-publishing]
---

# Hugging Face Hub storage (buckets, repos, large copies)

## When to Use
The owner wants assets, models, eval data or hill-climb outputs kept on Hugging Face, asks which buckets to create, or a `hf buckets cp` / dataset copy keeps failing.

## Standing rules
- **Public-safe only, for now.** Work that may hold personal data stays off HF until an encrypted path exists (client-side encryption such as restic with keys in bws, into a private bucket or B2/R2). Never upload it in plaintext, private bucket or not.
- **Manifest third-party, copy curated.** For other people's models/datasets record repo, revision, licence and consuming project in a manifest instead of mirroring them. Copy only curated subsets the owner asked for and our own outputs. Keep the source's LICENSE file next to any copy.
- **Scan before every upload** for PII and secrets; owner data stays out of public buckets even when sanitized unless he approves.
- **Leave buckets the owner made himself alone** except for the copy he asked for.
- **Tokens:** call `huggingface_hub.get_token()` inline (e.g. inside `$(...)` for a curl header); never print it or put it in argv logs.

## Procedure
1. **Check account limits first:** `hf auth whoami` plus the plan (free plan: no paid storage, private storage capped, public storage best-effort). Say what fits before creating anything.
2. **Create buckets by purpose** (e.g. assets, small models, hill-climb results, public evals), each with a README stating scope, licence policy and "no personal data". Keep the plan as a file under the operations dir.
3. **Copy large repos in pieces, never whole.** A whole-repo `hf buckets cp hf://datasets/<org>/<repo> hf://buckets/<me>/<bucket>/<dir>` of tens of GB / tens of thousands of files fails partway. Use a resumable script:
   - list top-level entries; copy small folders as one `cp` each;
   - for big folders go straight to one `cp` per sub-entry, and skip entries already present (`HfApi().list_bucket_tree("<me>/<bucket>", prefix="<dir>/<folder>", recursive=True)`), so a restart resumes instead of recopying;
   - wrap each `subprocess.run(..., timeout=N)` in `try/except TimeoutExpired` and count it as a failed attempt; an uncaught timeout kills the whole run;
   - record finished keys in `done.txt`; log per item;
   - repo metadata files such as `.gitattributes` may not be copyable ("No files found"); mark them done instead of retrying.
   - **Free accounts get 1000 API requests per 5 minutes.** One `cp` per item burns several, so ~250 items in 6 minutes hits the limit, and an unwrapped `list_repo_tree`/`list_bucket_tree` then raises 429 and kills the run. Pace copies (~1.5 s apart), treat "rate limit" output as sleep-and-retry (not a failed attempt), and wrap every API listing in a backoff retry. Expect ~200 items per 5 minutes on a free account.
4. **Run it as a transient user unit**, not in the terminal: `systemd-run --user --unit=<name> --collect -p Nice=10 -p MemoryMax=1G -p RuntimeMaxSec=21600 --working-directory=<dir> -p Environment=PATH=$HOME/.local/bin:/usr/bin:/bin -p StandardOutput=append:<dir>/unit.log -p StandardError=append:<dir>/unit.log <hf's own python> -E copy.py`. Use the python from the `hf` install (its shebang) so `huggingface_hub` imports; set PATH so `hf` resolves. Attach a background watcher that waits on `systemctl --user is-active` and prints the final tally.
5. **Verify from the server, not the log:** `curl -s -H "Authorization: Bearer $(python3 -c 'from huggingface_hub import get_token;print(get_token())')" https://huggingface.co/api/buckets/<me>/<bucket>` gives `size` and `totalFiles`; compare with the source repo's file count and size.
6. **Offer to drop duplicate formats** (e.g. a KTX2 copy of the same GLBs) before spending quota on them; that is the owner's call.
