# ADR 0027: Focused governance trust bootstrap (inactive)

Status: readiness candidate only. Focused governance remains inactive and the
production provider intentionally returns no key.

## Authority boundary

The launcher resolves the authoritative Hermes home before accepting worker,
CLI, environment, or board input. It inherits a read-only, fully sealed memfd
(the future systemd `LoadCredential=`/Keel broker handoff) and constructs
`LauncherPolicyState`. `create_startup_policy_loader()` is the sole production
factory. It chooses the closed Keel/SecretService provider internally; callers
cannot pass a path or provider. The private test factory rejects
`production=True`.

The authenticated `PolicyBootstrapEnvelope` binds:

- config-home anchor device/inode;
- exact trust-root SHA-256;
- governance SHA-256 and version;
- Keel key ID, nonce and monotonic envelope generation;
- effective and expiry epochs.

The envelope descriptor must be read-only, owned by the service uid, regular,
bounded, and sealed against writes, growth, shrink, and further seal changes.
There is no environment, pathname, CLI, plaintext key, or caller-provider
fallback.

## Descriptor and reload invariants

The home and both fixed anchor components are opened descriptor-relatively with
`O_NOFOLLOW`. Every component must be uid-owned mode 0700. Trust root and
manifest must be uid-owned regular mode 0600. Device, inode, uid, mode, size,
mtime and ctime are captured before/after reads. Immediately before publication,
every still-open descriptor is revalidated and the complete pathname chain is
reopened and compared, detecting replacement, chmod, ctime and swap races.

Each reload reserves a strictly increasing local generation before validation.
Publication is compare-and-swap by that generation. A failure publishes DENY
for its own generation; an older successful validation can never overwrite a
newer DENY or snapshot. The returned snapshot is immutable.

The approved K3 receipt tuple is consumed as a deterministic binding digest over
anchor identity, envelope generation/nonce, trust-root hash, manifest hash, and
governance hash/version. This bootstrap does not parse or grant authority from
`ACTIVE`; the digest is evidence only and does not duplicate Captain authority.

## Surface proof and inactivity

`FocusedPolicyFixture` is a disposable test-only adapter over the real Kanban
create, promote, claim and process-spawn callables. It captures one startup
snapshot and applies the identical fail-closed predicate to all four surfaces.
Tests prove a later reload cannot mutate that startup snapshot and no surface is
called under the shipped FROZEN/DENY posture.

The config schema remains `mode: governance_only` and
`activation_supported: false`. No dispatcher import or live gate, credential,
config write, service restart, receipt installation, or activation is included.

## Future activation and rollback

Activation remains a separate Captain ceremony: authenticated operator identity,
exact sealed pack and revision, validated Keel key, signed ACTIVE receipt, fsync,
and startup restart. Rollback revokes that receipt and restarts the owner.
Missing, expired, replaced, or unverifiable material always yields DENY; valid
governance material without the unimplemented activation ceremony remains
FROZEN.
