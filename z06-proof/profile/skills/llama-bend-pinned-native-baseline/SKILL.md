---
name: llama-bend-pinned-native-baseline
description: "Use when qualifying pinned llama.bend CPU baselines."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [bend, inference, baseline, provenance]
---
# Pinned llama.bend native baseline

## When to Use

Use for exact-head llama.bend native acceptance or real-model CPU baseline qualification under bounded shared-host resources, without global toolchain changes.

## Procedure

- Freeze the exact requested Git heads before execution. Distinguish a fork candidate rebased onto `devel` from the live upstream `devel` SHA; never silently substitute them.
- Read `scripts/setup.sh`, `reference/models.py`, requirements, native Makefile, generator timing code, and current contribution policy. A parser's unit tests do not establish native inference or permission to publish a tooling PR.
- Inventory live CPU, memory, disk and tools. Download public release artifacts into an owned artifact directory with explicit byte caps, release/model revision metadata and verified hashes. Do not run setup scripts that overwrite global Bend/Lean installations.
- Put pinned Bend and Lean in an owned HOME. Keep host clang ahead of Lean's bundled clang: Lean's release can include a clang without standard C headers, causing `stdbool.h` failures. Prove the include failure and the working host compiler before adjusting only the runner PATH.
- Preserve Python requirement pins. uv's first-index policy can reject a valid PyPI numpy pin when a PyTorch extra index contains an older numpy. If both official indexes are intended by the repository's pip requirements, explicitly use pip-equivalent multi-index resolution, lock every resolved wheel hash, preflight wheel sizes, download with caps, then install offline with `--require-hashes`. Never fix resolution by changing versions.
- Download the exact model revision and verify LFS SHA256 plus Git blob IDs for small files. Run the unmodified prep conversion/check functions against those files; record any download-stage bypass explicitly. Reuse model/oracle data between named heads only after verifying identical oracle source and model pins; compile native executables separately.
- For independent cold-source qualification, create fresh detached worktrees and verify every tracked blob against its exact commit. Reuse large pinned weights/oracles and the Python environment by symlink only after hashing them; copy the small model metadata into each owned data directory because unmodified `prep.py --check` regenerates tokenizer tables. Cold source/build does not mean cold page cache or fresh model/tool setup.
- Verify installed Bend/Lean archive members and wheel payloads against already hash-checked local archives when full toolchain provenance is required. Map wheel `.data/purelib` and `.data/platlib` to site-packages and `.data/data` to the environment prefix (for example SymPy's man page); explicitly exclude installer-rewritten wheel RECORD/entrypoints with a reason. Never redownload large artifacts just to requalify them.
- Execute the full named Python suite and actual `make check`. Preserve initial failures and partial runs, and report default fuzz counts from actual logs rather than README historical claims.
- Put heavy work behind a shared native-build lock and all benchmark executions behind one shared benchmark lock. The actual service must own these locks (e.g. `systemd-run ... flock LOCK COMMAND`), not only an RPC wrapper: the wrapper can die while systemd descendants continue. Set `RuntimeMaxSec`, `KillMode=control-group`, CPU/memory limits, and a pre-execution RAM floor. Use tracked background plus wait for commands longer than the tool RPC ceiling. Explicitly stop and read back only owned services after interruption.
- Recheck available RAM inside the service after acquiring both shared locks and before each heavy command; an admission check performed before lock wait can become stale. Retain a lock-busy attempt as NOT_RUN and use a bounded retry rather than bypassing another lane's lock.
- Run official `make bench`, then separately capture raw generation with explicit threads. Record every command's exit, expected token IDs/count, finite monotonic timestamps, decoded-text boundary, and early EOS behavior. Keep the official benchmark and the raw captured sample distinct.
- Audit stdout-only reporting separately from benchmark acceptance. A timing parser cannot infer producer exit, intended token count or oracle IDs; truncated, wrong-ID or failed-producer captures may still be valid diagnostic input. Require an external gate for those invariants and reject every malformed token row rather than merely selecting regex matches. Exercise an actual nonzero-exit replay control without presenting the replay as inference.
- For live oracle validation, invoke the repository's unmodified `bench_ref.main()` with only its output ROOT redirected into evidence storage; compare the resulting IDs to committed expectations and captured generation without rewriting tracked files.
- Explain timing boundaries: model-load timing is not process startup; first generated timestamp starts after load/tokenization and includes prefill/cache setup; decode intervals exclude load/prefill but include printing and clock quantization. A shared-host quota-limited run is a diagnostic baseline, not a speedup claim.
- Before finishing, verify clean tracked source, exact heads, manifest hashes, native command exits and absence of owned processes/locks. Keep global tool versions unchanged and do not publish without separate authority.
