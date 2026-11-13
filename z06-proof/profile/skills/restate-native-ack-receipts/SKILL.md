---
name: restate-native-ack-receipts
description: "Use when qualifying Restate native ACK/runtime gates."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rust, restate, nextest, receipts]
    related_skills: [upstream-contribution, test-driven-development]
---

# Restate native ACK receipts

## When to Use

Use for exact-head Restate CLI/parser qualification and receipt-only native runtime ACK tests without taking over an existing author's production fix.

## Procedure

- Read the exact head's AGENTS.md, owning Cargo manifest, rust-toolchain.toml, CI workflow and lock before selecting gates. Restate uses nextest; a formatter/parser failure is not execution of CLI tests.
- Run toolchain discovery outside a toolchain-pinned checkout, or set an already-installed RUSTUP_TOOLCHAIN explicitly. Even `rustup toolchain list` can synchronize the directory's pinned toolchain. For authorized isolated installation, set RUSTUP_HOME before the first rustup invocation; never retroactively call a default-home install isolated.
- Use an owned CARGO_HOME and per-source CARGO_TARGET_DIR, `--locked`, a shared native-build lock, two Cargo jobs and verified cgroup limits. Classify timeout-before-lock as NOT_RUN, not a compile/test result. Automatically classify test/build/check/nextest commands as heavy rather than relying on an optional caller flag.
- Inspect the exact CI's `cargo hakari disable` step before treating workspace-hack's broad native graph as unavoidable. This officially supported setup empties the generated workspace-hack dependencies and updates that package's lock record. Save the original source and lock first; compare parsed package identities, versions and checksums afterward. Label it a CI setup overlay, not an unchanged-lock run. Do not manually substitute unrelated dependency versions.
- Native GCC errors in krb5-src can arise even for a selected CLI package while workspace-hack is enabled. Preserve the native diagnostic and distinguish the dependency compiler from the selected Rust crate. Do not infer an unavailable rust-sasl checkout after a successful public pinned fetch.
- For receipt-only ACK probes, add a cfg(test) child beside `ServiceProtocolRunner` and exercise the real `bidi_stream_loop`, `handle_message`, and `response_stream_loop`. Keep invoker and SDK channels alive so channel EOF cannot cause a false timeout result. Inspect the emitted requested-ACK proposal and actual outbound ACK header.
- Cover prompt ACK, ACK delayed past SDK inactivity, and no ACK separately. Use a paused Tokio clock and an outer finite virtual-time deadline. Characterize current timing separately from any desired independent runtime-ACK timeout policy.
- Label decoded-message-boundary probes precisely: they execute production loops, but do not prove HTTP transport, partition append latency, SDK error 599, suspend/replay or invocation-attempt count. A full end-to-end requirement remains open until those paths execute.
- Trace the real notification producer and negotiated protocol before calling an injected ACK sequence production-reachable. In the current state machine, `ProposeRunCompletionAck` substitution requires requested_ack and protocol >= V7; older protocols forward `Notification::Entry`. A V5 fixture that directly injects the ACK can characterize the consumer branch but cannot validate the supported producer-to-consumer path, even if all owning tests pass.
- Repair ACK fixtures through `ServiceProtocolVersion::pick`, pin that exact result in `InvocationStateMachine`, feed actual runner command/proposal effects into its trackers, call `notify_entry` at the modeled partition boundary, and forward the received producer output unchanged into bidi. Decode/assert proposal completion ID/value/requested_ack and outbound ACK completion ID; retain V5 Entry-only and wrong-completion/duplicate controls. An assumed Input replay prefix and a modeled partition echo are not real journal or SDK evidence.
- Round-trip fixture command headers through `MessageHeader::try_from(u64)` before passing them to the decoded-message consumer. `MessageHeader::new` leaves requested_ack as None even for command types; production `handle_new_command` requires Some(false/true). Preserve such fixture-construction failures separately from the intended reachability RED.
- Use bounded blocking flock admission for a contended shared native lock. Nonblocking polling can starve behind successive blocking lanes; record pre-lock interruption or timeout as NOT_RUN and never bypass the global lock. Keep native failures, wrapper failures and lock-wait failures distinct.
- Re-read `/proc/<pid>/cgroup` during and after native execution instead of caching a scope path: host supervision can migrate jobs into a shared bounded agent scope and remove the original scope. Save the pre-execution proof immediately, validate effective limits after migration, distinguish native exit from receipt-wrapper failure, and never treat shared cgroup lifetime `memory.peak` as per-command peak RSS.
- Mutation-disable the production inactivity branch and require the delayed/no-ACK probes to fail within their outer bound while prompt ACK passes. Restore exact bytes in a finally block, verify their hash, then run the owning library suite and formatter again. Do not publish the mutation or confuse it with a fix.
- Deliver the pinned source archive, original commit header/tree metadata, test/CI overlay patch, per-file hashes, raw command logs, executed-versus-NOT_RUN claims and an unsent minimal owner note. Cold-extract and apply the overlay, verify file identities, and say separately whether runtime tests were rerun from that restored source. An uncommitted overlay tree hash is not a commit.
- For a test-only candidate from a shallow checkout, keep CI setup outside the commit and export the actual candidate/base objects plus the original shallow boundary. Git bundle verification and clone checkout can succeed while history traversal/fsck fails because the bundle omitted `.git/shallow`. Restore the supplied boundary only in the new owned clone, run `git fsck --strict`, and verify every tested source hash before calling the packet restorable; do not claim pre-boundary history or an offline toolchain bootstrap.
