# ADR 0027: Focused governance trust bootstrap (inactive)

Status: accepted, bootstrap only; focused governance remains inactive.

## Decision

One startup owner resolves an authoritative config home and passes it directly
to `StartupPolicyLoader`. The loader never reads worker environment, board data,
or caller-selected policy paths. From that trusted descriptor it opens
`hermes/orchestration-policy` component by component with `O_DIRECTORY` and
`O_NOFOLLOW`, verifies owner and write permissions, and records device/inode.

`trust-root.json` (0600) pins policy version, key ID, governance content SHA-256,
and the exact manifest byte hash. `active-source-manifest.json` (0600) repeats
the pinned values, has a generation ID, and carries an HMAC-SHA256 over canonical
JSON excluding `mac`. Keys come only through `PolicyKeyProvider`; this change
ships an unavailable default and an explicit in-memory test provider. There is
no environment or plaintext-file fallback.

Every read is descriptor-relative and no-follow. Identity is checked before and
after bounded reads. Reload atomically replaces the snapshot, including replacing
a prior frozen snapshot with DENY after any failure. No snapshot can report
focused mode in this bootstrap.

## Install and future activation ceremony contract

Install (implemented but never invoked automatically): a locally authenticated
operator calls `install_anchor(authoritative_config_home)`. It creates the fixed
directory chain as the current user at 0700. It does not write trust material.

Activation (contract only, not implemented here) must:

1. authenticate the Captain locally without `$USER` or worker assertions;
2. open and validate the fixed anchor descriptor and retain its dev/inode receipt;
3. retrieve the selected key ID from Secret Service/Keel (never env/files);
4. verify governance bytes, canonical manifest MAC, and all trust-root pins;
5. atomically install mode-0600 trust root, manifest, and a separately signed
   ACTIVE receipt binding Captain identity, generation, anchor identity, and all
   pinned hashes; fsync files and directory;
6. restart the startup owner and require its receipt parser to validate the exact
   sealed tuple before focused mode can exist.

Dispatcher create/promote/claim/spawn integration is explicitly deferred.

## Rollback

The local Captain stops the dispatcher, archives the immutable trust material for
audit, removes or revokes ACTIVE, and restarts. Missing/revoked receipt, root, or
key yields DENY/FROZEN, never focused. Reverting governance requires a new signed
manifest, trust-root update, and activation ceremony; pathname rollback is not
authority. This code does not touch a live config home, secret service, process,
or dispatcher.