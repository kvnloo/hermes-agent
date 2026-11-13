---
name: secrets-manager-bws
description: "Use when saving, checking or auditing keys and secrets."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [secrets, bitwarden, bws, api-keys, clipboard]
    related_skills: [discord-server-admin]
---

# secrets-manager-bws

Use when saving, checking, transferring or auditing API keys and machine credentials in Bitwarden Secrets Manager, or qualifying secure password/action authorization and scoped-vault migration.

## Rules

1. Use bws Secrets Manager for standalone API keys, not bw or browser website-login vaults. Keep secret values and prefixes out of chat, screenshots, DOM captures, tool output and readback files. Transfer authorized machine credentials inside a bounded local process, prefer stdin or the credential broker over argv, unset temporary values and print only key names, IDs and match booleans.
2. Keep personal, login and keyring passwords behind an independently enforced secure-action boundary. Authorize a typed operation rather than returning its secret. Treat masking, same-user files and client whitelists as context protection, not isolation from an agent with shell/root access. Follow references/secure-action-authorization.md and report private transport, privileged execution and biometric approval separately.
3. Check Secret Service on `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus`, including the login collection Locked property. Separate a wrong private bus, a locked collection and a missing desktop prompt. Identify host, account and collection before requesting unlock; use a trusted native flow with owner input outside agent tools and verify both unlocked state and an authorized downstream operation.
4. Bound keyring bootstrap to 15 seconds and stop repeated lookups while locked. Stop only identified hung secret-tool PIDs. Preserve a healthy daemon and existing keyring; recover setup provenance and metadata when the password is unknown. Explain the circular dependency when BWS access itself lives in that keyring, and reserve reset, deletion or reenrollment for explicit authorization. Preserve password strength and keep autologin out of headless-access workarounds. For dated login provenance, inspect `journalctl -b -o short-iso | grep gkr-pam`; correlate the sddm-helper unlock message with `last -F <user>` and `uptime -s`.
5. Obtain BWS_ACCESS_TOKEN from the existing ~/.hermes/bin/hermes-keyring-bootstrap.sh path inside one subshell and unset it there. Inspect the resolved bws-env-exec vault() source if bootstrap metadata is empty rather than asking for tokens. Use the Hermes keys project `ef35bed4-fc4f-42ab-a21f-b4bf013919b7` and ENV_VAR-style names; filter bws secret list JSON to .key and .id because raw list output includes values.
6. Check existing vault key names and profile .env key names before creating records. Read only the owner-authorized live clipboard, requested clipboard history or setup-wizard .env source inside the secret-handling process. Print clipboard entry IDs/lengths only and compare candidate sources in-process. Guard empty or whitespace-containing values before writes.
7. Before creating a provider key, verify the actual signed-in account, organization/project and working BWS destination, including a secret-preserving one-time transfer path. Validate the captured key with the provider API in-process, store it, read the exact record back and compare without disclosure. Re-observe the requested browser's account state; ask only for unavailable login/MFA/unlock interaction, never a pasted key.
8. Make machine-secret writes idempotent: compare the existing exact record and edit only when it differs. Split writing and verification so a nonmatching grep under set -e cannot skip round-trip proof. Report the key label/name, project, record ID, source and match result. Document any unavoidable bws argv exposure instead of describing it as stdin-only secrecy.
9. For an approved temporary device credential, generate it locally, store and round-trip verify in bws before applying it through stdin. Prove password login with the vault copy, then install an SSH key and confirm key-only access. Follow references/device-credentials.md for SSH_ASKPASS, pinned known_hosts and cleanup; keep this machine-credential workflow separate from personal-password handling.
10. Copy only requested keys directly from bws into the intended profile .env at mode 0600, skipping existing names and confirming names only. For an approved new Hermes key, update only the intended live and .files bws-consumers scope, refresh it and report that processes retain old environment until restarted. Keep GOOGLE_API_KEY, GEMINI_API_KEY and OPENCODE_* out of hermes scopes, and separate a gateway restart from credential-write proof.
11. For a plaintext-secret audit, identify the live branch and relevant remote heads, then use scripts/secret_audit.py for paths, pattern names, counts and placeholder classes. Confirm real-looking hits in-process without values, check enabled encryption plugins and plugin data.json, and establish pushed/local and visibility status. Recommend rotation and history cleanup without editing the vault unasked; retain metadata JSON and remove the authorized scratch clone.
12. Recover existing broker source, deployment and prior decisions before designing a replacement. For consume-only actions, have trusted UI display canonical target/operation, authenticate the user and execute inside an isolated broker with narrow authenticated IPC. Bind approval to principal, device, host/origin, operation, nonce, expiry and effective argv/stdin/cwd/environment/script identity; prevent replay and substitution instead of granting an arbitrary root shell or blanket sudo timestamp.
13. Choose supported authentication for the real platform: PAM/polkit on Linux, LocalAuthentication/Keychain plus constrained helper on macOS, or an enrolled device signing target-bound challenges for phone-to-host approval. Verify hardware/policy before promising fingerprints; WebAuthn may use a PIN. For autofill, verify origin/item and preserve the browser/password-manager boundary without exporting the personal vault.
14. Enroll an agent-only vault by immutable ID on a trusted administration device and supply only provider-scoped runtime credentials in a dedicated PROTON_PASS_SESSION_DIR. Inspect matching CLI help/source, roles and session-check side effects before access. Verify provider-side grants and cross-vault denial; keep admin custody, owner sessions and personal vault keys outside the agent host.
15. Migrate only explicitly approved machine secrets and keep BWS unchanged until destination scope, idempotent writes and round-trip comparisons pass. Qualify policy models, executable adversarial tests and live provider evidence separately. Test cancelled/expired/replayed/changed-target approvals, concurrent substitution and canary leakage; report each unverified boundary rather than claiming a universal non-bypass guarantee.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
