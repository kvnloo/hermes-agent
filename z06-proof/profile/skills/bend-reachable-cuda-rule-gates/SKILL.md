---
name: bend-reachable-cuda-rule-gates
description: "Use when proving Bend reachability or CUDA rule parity."
---

# Reachable rules and capped CUDA evidence

Load `bend:workflow` and the local toolchain lock. Bend 2.0.34 is not Bend 1/HVM; inspect `bend guide` and `bend base`. Use `bend version`, not `--version`.

## Reachability proofs

- Define reachability from `start` through actual `step` applications, not freely constructible terminal values. Check the declared winner's score. Preserve lawful cap exceptions: 30–29 refutes unconditional win-by-two for capped badminton.
- Prove `Inv(start)` and `Inv(g) -> Inv(step(g,event))`, then induct over traces. Factor symbolic finish predicates into Boolean parameters and prove a helper by cases. Failed reflexivity is not a language impossibility. An already-terminal branch returns the explicit invariant hypothesis.
- Use `List<&2, Event>` when induction both replays and recurses on a trace; default `List<Event>` is affine/Type. Mark reused typed helper parameters `+` and duplicate matched tails explicitly. Paired law defs use inferred arguments; put reusable recursion into a typed helper and call it from the paired law.
- Keep LAWS imported by PROOF. Save an intentional new-law sabotage failure, revert, and recheck. Run `bend PROOF.bend --verdict` alone: 2.0.34 rejects combining it with `-o`; export `.bendtt` separately. Host clang must precede Lean's bundled clang.
- A snapshot adapter may isolate HOME while a shell wrapper resolves `$HOME/.bend/bin/bend.bin`; record the adapter failure and use direct CLI verdict evidence, never fabricate an adapter PASS. On groot the wrapper now execs `bend.bin` from its own dir, so `hermes bend verify` works; the in-process `bend_verify` tool can still fail with `lean` missing from the Hermes process PATH (adapter error = no evidence).
- A wildcard `case _:` in a proof does not refine the scrutinee (the goal stays `f(x, e)` with e abstract). Proofs that split on an n-constructor event must list every constructor; generate them (see z0intelligence `bend/work_item_fsm/gen_proof.py`).
- `A & B` and `{a == b : T}` are `Type`, so they cannot be reused with `+`. For a reachable invariant that pick-lemmas must pass to both branches, make it a Boolean `inv_b(s)` reflected through `T(b) -> Data`, and convert to readable spec predicates only in the final law.
- A def must be declared above its callers; a destructuring `(a, b) = f(..)` is a match on a computed value (refused); use `Pair.fst(A, B, p)`.
- Prove laws are load-bearing with a mutation script that copies the project to a temp dir, applies one string mutation per law, and requires `SOME PROOFS FAIL`; Bend reports only the first failing def, which may be a helper rather than the falsified law.

## CUDA receipts

- On Arch CUDA hosts export `CUDA_HOME=/opt/cuda` for every build. GPU work needs `!`, native `bend file.bend -o binary`, and adjacent `binary.gpu`.
- Require >=2 GiB free; wait/retry occupied devices. Use `--gpu 1GB`, never uncapped defaults. An explicit size fails rather than silently falling back. For an `on` probe, a final `--gpu 1GB` preserves the cap.
- Compare identical binaries with GPU off and capped GPU; save stdout, exits, timings, binary/cubin/source hashes and concurrent `nvidia-smi` process samples. A 2^14-leaf tree gives 4^7 seven-event tapes per bang, one tape per leaf. Aggregate checksums are not per-tape equality. Shared-host startup-dominated timings are not speedup benchmarks.
- Keep experiments out of production imports. Oracle agreement is not correctness. Kernel verdicts cover emitted books, not source/compiler equivalence (`source_semantics_attested=false`).
