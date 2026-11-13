---
name: z0bridge-owned-ssh-enrollment
description: Use when extending z0bridge owned-host SSH enrollment.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ssh, z0bridge, tailscale, enrollment]
    related_skills: [home-k3s-fleet, secrets-manager-bws, git-isolated-contribution-guards]
---

# z0bridge owned-host SSH enrollment

## When to Use

Use when designing, implementing, testing or deploying z0bridge's opt-in owned-host SSH enrollment, rotation or revocation.

## Rules

- Discover the live launcher and actual Git worktree first; the running pairing branch can differ from main. Preserve its existing device registry, node-bound credentials, signing authority, and audit sequence rather than inventing another authority.
- Treat authenticated tailnet discovery as identity evidence, never owner admission. Require an explicit owner-authorized stable node ID, target Unix account, platform and daemon port before accepting a node-bound SSH-scoped enrollment.
- Keep client private keys on their originating devices. Submit only public client/daemon host keys, pin first enrollment through the existing private pairing channel, and require explicit owner rotation on either key mismatch. Reject cloned public identities and host keys.
- Use the existing identity signing key with a domain-separated public desired-state signature, bounded freshness and persisted monotonic revision. Include device, credential and scope revocations in that revision domain.
- Distinguish network outages from explicit authority refusals and cryptographic/parser failures. Cache only correctly signed unexpired desired state during outages; delete cached permissions on refusal so the next outage cannot resurrect revoked grants.
- Preserve unmanaged authorized keys and legacy SSH configuration. Use strict dedicated pins and identities, refuse unsafe paths, and serialize local writers with an OS-backed lock that is released on crashes. Document that reconciliation does not terminate existing sessions and needs a running supervised process.
- Validate platform claims against the actual runtime. Native Android is not an sshd host; PRoot guest-root exception must not silently authorize physical-host root. Userspace Tailscale transport and sshd/firewall readiness are explicit deployment prerequisites, not reasons to relax host-key checking.
- Verify only BWS project metadata when configuring a controller project reference. Never propagate full vault access to nodes, place secrets on argv/logs, or call project-reference verification credential storage.
- Exercise actual CLI child processes with isolated HOME/state, real identity HTTP routes and test-only whois/transport fixtures. Run CPU suites through MBP fleet-build. Distinguish fixture proof, real BWS metadata verification and real directed fleet SSH proof.
- Reconcile interfaces before deploying a fleet helper alongside z0bridge. Separate marked fragments are not unified revocation: choose one trust writer unless identity paths, ownership provenance, forwarding/PTY semantics, clear/revoke API and locks have a tested adapter. Never fabricate the other helper's provenance fields merely to satisfy its schema.
