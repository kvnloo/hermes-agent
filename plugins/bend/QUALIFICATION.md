# Bend verification qualification hold

The public `bend_verify` tool remains experimental. No exact compiler/kernel
release has been admitted for trusted proof results. A compatible version and
stable process-local hashes are necessary checks, not evidence of compiler
semantic correctness.

The adapter now refuses remote, BendHub, malformed, and unsupported imports in
the reachable project input closure before invoking Bend. Adjacent `LAWS.bend`
and transitive local helpers are checked too. `import Base` belongs to the
compiler distribution; it is **not** covered by the project input manifest.
This parser is a conservative supported-input restriction, not an OS network
sandbox or a guarantee against a compromised compiler.

The public tool preserves raw `execution_verdict`, hashes, and diagnostic
results, but changes a raw pass to `success: false`, `verdict: unqualified`,
`code: unqualified_bend_release`. Failures, timeouts, and instability retain their
original classifications. There is no environment or tool-argument bypass.
Low-level core/session functions remain available to downstream experiments;
their raw pass must not be presented as an admitted proof result.

## Before removing this hold

Qualify an exact artifact containing the upstream semantic correction, against
the frozen semantic oracle and the existing regression/lifecycle corpus. Bind
the receipt to the complete compiler distribution, bundled `Base`, runtime
inputs, kernel source and kernel artifact. Enforce those admitted identities
before and after verification; hashing only a CLI launcher is insufficient.
No version-range rule or unverified self-reported hash may replace this gate.

Then validate the extracted standalone plugin at its exact commit through the
public Hermes lifecycle and catalog validator. No core integration or catalog
submission is authorized by these adapter tests alone.

Tracking: downstream #324 / #325 and upstream NousResearch/hermes-agent#131689.
These changes implement dependency refusal and an explicit **admission hold**;
they do not claim the release qualification itself is complete.
