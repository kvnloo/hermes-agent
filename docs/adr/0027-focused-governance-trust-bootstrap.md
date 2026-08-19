# ADR 0027: Focused governance trust bootstrap (inactive)

Status: readiness candidate only. Focused governance remains inactive and the
production provider intentionally returns no key.

## Authority boundary

The launcher resolves the authoritative Hermes home before accepting worker,
CLI, environment, or board input. It inherits a read-only, fully sealed memfd
(the future systemd `LoadCredential=`/Keel broker handoff). At module startup a
private closure captures the authoritative home and inherited descriptor once.
`create_startup_policy_loader()` is a zero-argument production factory. It
chooses the closed Keel/SecretService provider internally; callers cannot pass
or construct a home, descriptor, provider, mode, token, or authority object.
Later environment/CLI mutation is irrelevant. The explicit test factory rejects
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
mtime, ctime, and link count are captured before/after reads. Immediately before
publication, under the same generation/publication lock, both document names are
opened into a pinned pair before either is accepted. Opposing open-order passes
reread and hash both documents, compare complete descriptor metadata, compare
both no-follow directory entries, revisit both descriptors, and recheck every
anchor component. Final document descriptors remain open through snapshot
commit, detecting replacement, chmod, ctime, hard-link, and inter-document swaps.

The snapshot's authority is the authenticated envelope, validated content, and
pinned descriptor set—not mutable pathnames after commit. An OS actor can rename
a pathname after the final set validation, but that cannot alter the bytes in the
already committed immutable snapshot; a later reload observes the changed entry
and denies it. This is not a claim that pathnames remain frozen after commit.

Each reload reserves a strictly increasing local generation before validation.
Publication is compare-and-swap by that generation. A failure publishes DENY
for its own generation; an older successful validation can never overwrite a
newer DENY or snapshot. The returned snapshot is immutable.

The approved K3 receipt tuple is consumed as a deterministic binding digest over
anchor identity, envelope generation/nonce, trust-root hash, manifest hash, and
governance hash/version. This bootstrap does not parse or grant authority from
`ACTIVE`; the digest is evidence only and does not duplicate Captain authority.

## Surface proof and inactivity

The disposable test-only surface harness calls the real Kanban `create_task`,
`promote_task`, and `claim_task` operations against an isolated SQLite board and
the real `subprocess.Popen` boundary with a sentinel. It captures one startup
snapshot and applies the identical fail-closed predicate to all four surfaces.
Tests record stacks, events, rows, and the sentinel: DENY produces no body, DB,
or subprocess effects while an explicitly test-only ACTIVE fixture performs
exactly the four scoped operations. The harness refuses production mode.

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
