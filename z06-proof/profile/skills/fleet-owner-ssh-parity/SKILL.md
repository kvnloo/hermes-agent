---
name: fleet-owner-ssh-parity
description: "Use when onboarding owner SSH mesh or shell PATH parity."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [fleet, ssh, tailscale, dotfiles, onboarding]
    related_skills: [home-k3s-fleet, dotfiles-desktop-work, secrets-manager-bws]
---

# Owner-user fleet SSH parity

## When to Use
Use for explicit owned-host SSH mesh enrollment, shell PATH startup parity, and rejoin integration without weakening worker-lane isolation.

## Rules

- Keep owner-user mesh separate from `agentjob` worker enrollment: controller-only TCP2222 and cgroup tailnet egress deny are security boundaries, not connectivity bugs. Never widen them for owner all-to-all.
- Use `scripts/fleet-ssh` (or `fleet ssh`) for explicit public manifest validation, home-local PATH install, managed key/pin installation and read-only outgoing verification. Read `docs/fleet/SSH_PARITY.md` and `config/fleet/ssh-compatibility.json` in the chosen isolated worktree before calling it.
- Admit only explicit owned nodes with authenticated stable Tailscale ID/address/User.LoginName evidence, not all reachable peers. Tagged hosts require a separate ownership verifier. A supplied JSON snapshot does not prove its origin/freshness: the orchestrator must establish both.
- Generate unique source identities locally; distribute public keys only. Pin independently authenticated host public keys/fingerprints with provenance. Reject cloned keys and mismatches; never replace them with keyscan-only TOFU or shared BWS tokens.
- On Linux use owner `kvn`, never root or `agentjob`; phone fake root requires explicit PRoot admission. Phone Linux guest and Android VPN are different Tailscale identities; Tailscale SSH22 is not OpenSSH authorized_keys authentication.
- Prepend POSIX PATH sourcing before bash interactive guards, preserve bash's existing login profile selection, and use fish conf.d without relying on OMF. Guard optional `OMF_PATH/init.fish` with `test -r` for quiet noninteractive startup.
- Test temporary HOME paths with spaces, actual bash login and fish noninteractive, repeated-source PATH deduplication, preservation of unmanaged keys, managed revocation, strict SSH config parsing, private/public identity match, and fail-closed ownership/path drift. Offload suites through `fleet-build --node mbp --light --wait 0`; never edit live profiles as a side effect of IaC tests.
- Aggregate every directed source-to-destination probe externally. One outgoing source or offline file verification never proves all-to-all. Document unreachable owners/ACL-policy mismatches rather than bypassing host verification or changing services.
- Coordinate phone lifecycle ownership via a small shared interface report. Do not overlap supervisor/job/health code merely to add SSH helpers.
