---
name: api-key-secret-storage
description: "Use when checking or saving API keys in bws."
version: 1.0.0
metadata:
  hermes:
    tags: [secrets, bitwarden, bws, api-keys, clipboard]
---
# API key / secret storage (Bitwarden Secrets Manager)

"Bitwarden" for API keys means **Bitwarden Secrets Manager (`bws`)**, not the password-manager CLI `bw` and not the Hermes browser vault (that only holds website logins bound to an origin). Do not propose installing `bw` or ask for a master password.

## Hard rule
A secret value never reaches tool output or chat. Hold it only in shell variables inside a `( ... )` subshell; print lengths, booleans, ids, key names. Compare values in-shell (`[ "$a" = "$b" ]`). `unset` at the end.

## Procedure
1. Load `secrets-manager-bws` for current credential discovery. `BWS_ACCESS_TOKEN` no longer lives in profile `.env` files; the keyring bootstrap supplies it. Bound bootstrap execution to 15 seconds because headless sessions can hang waiting for the keyring. Inspect the active `bws-env-exec` implementation if access fails: approved consumers may use private `$XDG_RUNTIME_DIR/bws-secrets/<scope>.env` caches. Print key names only, never cached values; do not modify consumer allowlists or credential infrastructure just to unblock a provider test. If the requested key is not available, report the access blocker instead of claiming the vault contains no key.
2. Check existence: `bws project list -o json | jq -r '.[]|"\(.id) \(.name)"'` and `bws secret list -o json | jq -r '.[]|"\(.key) project=\(.projectId)"'` (keys only, never `.value`). Keys are ENV_VAR style in the "Hermes keys" project.
3. Name the secret after the env var Hermes already uses: grep names only, `grep -oHE '^(export )?[A-Z_]*<SERVICE>[A-Z_]*' ~/.hermes/profiles/*/.env` (e.g. Fish Audio setup writes `FISH_API_KEY`).
4. Source the value, in this order:
   - Clipboard: `wl-paste -n`. Live clipboard can advertise text types yet return 0 bytes once the source app closes.
   - Clipboard history: `cliphist` is running. Select only matching entries: `cliphist list | grep -i <service> | head -1 | cliphist decode`. Count first without printing: `cliphist list | grep -ic <service>`. Never list or decode other entries.
   - The value the setup flow just wrote to the profile `.env` (check mtime matches the setup).
   Strip `KEY=` prefixes/quotes/whitespace; abort if empty or contains spaces.
5. Create or update: `bws secret create <KEY> "$v" <projectId> --note "<service> API key"`; if it exists and differs, `bws secret edit <id> --value "$v"`; if equal, change nothing.
6. Verify by reading back in-shell: `[ "$(bws secret get <id> -o json | jq -r .value)" = "$v" ] && echo verified`.
7. Report: key name, project, secret id, verified yes/no, and which source was used (value never displayed). If a different source than the user named was used, say so and offer to update.
