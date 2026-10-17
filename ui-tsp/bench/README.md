# Measured App frame pacing

## Decision

Keep the ACK-driven build gate, plus pane visibility and final-close handling.
On `groot`, the credits=1 replay falls from **1249.92 ms to 794.06 ms** (median
of five fresh-process runs; **36.47% less replay time**). Visible wire traffic
is unchanged: this is an avoided-build win, not a bandwidth claim. Credits=8
visible is **no measurable change** (overlapping ranges; median 1.47% slower).
Hidden replay is about 92% faster, with zero builds while hidden.

`77e7129cff` was cherry-picked with `-x` as `b2ff496021`, preserving Kevin
Rajan's authorship. Its two tool-card follow-up commits are unrelated and were
not ported. The candidate keeps current `setImmediate` burst batching instead
of introducing microtask batching. It adds no timer, polling or hot render loop.

## Reproduce

```sh
# Node 26.7.0 used for the receipts (Node >=22 with Promise.withResolvers required).
export PATH=/mnt/zer0models/hermes-wt/preview-homes/tern-frontend/tools/node-26.7.0-linux-x64/bin:$PATH
npm --prefix ui-tsp run bench:frame
npm --prefix ui-tsp run bench:frame:compare
# Counter gate: deliberately fails on baseline with 502 !== 127.
node ui-tsp/bench/run.mjs --source-ref=b7fa64fe82 --assert-win
node ui-tsp/bench/run.mjs --assert-win
```

`compare.mjs` rotates baseline/donor/candidate across five rounds (ABC, BCA,
CAB, ABC, BCA), using a fresh Node process per side and the same four scenarios
inside each process. It reads just `app.ts`/`frame.ts` from the pinned revisions;
all other runtime source is identical between these variants. No source checkout
is mutated. `run.mjs --build-only` prints the instrumented standalone bundle for
profiling. Generated bundles and isolated Hermes homes use `$TMPDIR`.

## Machine and method

- Host: `groot`, Intel Core i9-10900KF @ 3.70GHz, Linux `7.2.9-1-cachyos`,
  Node `v26.7.0`, SDK `@stencil-hq/tern` 0.1.0. This is Kevin's real host,
  not a renderer implementation or a remote benchmark machine.
- Host was shared: load averages before 5.53/5.75/5.77 and after 6.25/5.91/5.83;
  ten CPUs were available to the process. Existing desktop/agent workloads
  were not stopped. The interleaving and ranges expose noise rather than
  attributing the small credits=8 difference to pacing.
- One real `App`, fake gateway emitter, actual SDK `Surface`, reconciler and
  `encodeJson`. Terminal ACKs are simulated, **not measured native paint ACKs**.
  No provider calls, live pane, live socket, gateway process or real filesystem
  session is used by the benchmark.
- Seed: 1,000 settled transcript entries (500 users + 500 assistant answers),
  then the welcome entry and one live turn. Exactly 5,000 Unicode text deltas,
  20 tool starts, 20 completions and message start/complete: **5,042 events**.
  Ten deltas per event-loop ingress burst; one cumulative ACK after every four
  bursts, with credits=1 or 8. Hidden cases withhold ACKs and resume at the end.
  Fixed wall-clock dates and first welcome tip remove wire-byte noise; the
  high-resolution performance clock remains real. Splash and blobs are off.
- Wire bytes are **encoded frame bytes including APC framing**, not estimated
  JSON size. Handshake/open/close traffic and actual terminal painting are not
  part of the reported normal replay.
- `JS/frame` accumulates all synchronous App builds **and SDK ACK-flush work**
  since the previous transmitted frame. This includes discarded blocked builds;
  otherwise the baseline would look artificially cheap by timing only its
  blocked `render()` calls. p50/p95 use nearest-rank percentiles; table values
  are medians of each run's percentiles, not pooled quantiles. The small hidden
  sample includes cold transcript construction and the final accumulated frame;
  its high p95 is not an animation latency claim.
- Replay time is actual elapsed App streaming/ACK/drain work, without artificial
  sleeps or terminal paint delay. Fake-terminal wire reconstruction happens
  **after** the timed region. `runs.jsonl` contains every raw number and failure
  aborts the command instead of producing a successful row.

## Results

Five runs per row. Builds, frames, bytes and semantic counts were deterministic
across all five runs. `Total JS` and replay durations are milliseconds.

| Variant | Credits | Hidden | Builds | Frames | Wire bytes | JS/frame p50 / p95 ms | Total JS ms | Replay ms (min–max) | Text updates merged | Tool running snapshots merged |
|---|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 1 | false | 502 | 128 | 746273 | 7.938 / 11.960 | 1145.23 | 1249.92 (1202.20–1346.29) | 4860 | 0 |
| baseline | 8 | false | 502 | 503 | 773888 | 4.645 / 7.111 | 2632.76 | 2735.16 (2649.74–3122.07) | 4500 | 0 |
| baseline | 1 | true | 503 | 4 | 731538 | 4.945 / 579.014 | 620.29 | 663.00 (645.12–741.08) | 4980 | 20 |
| baseline | 8 | true | 503 | 12 | 735678 | 4.553 / 557.094 | 639.38 | 683.14 (671.09–770.81) | 4972 | 19 |
| donor | 1 | false | 127 | 128 | 746273 | 4.973 / 8.906 | 763.45 | 796.51 (770.43–898.40) | 4860 | 0 |
| donor | 8 | false | 502 | 503 | 773888 | 4.674 / 6.787 | 2588.44 | 2687.32 (2642.84–2956.64) | 4500 | 0 |
| donor | 1 | true | 2 | 3 | 731499 | 6.208 / 36.585 | 42.79 | 49.84 (46.83–50.41) | 4980 | 20 |
| donor | 8 | true | 11 | 11 | 735638 | 4.466 / 36.767 | 90.38 | 104.07 (100.99–106.36) | 4972 | 19 |
| candidate | 1 | false | 127 | 128 | 746273 | 4.899 / 8.595 | 761.05 | 794.06 (767.45–843.20) | 4860 | 0 |
| candidate | 8 | false | 502 | 503 | 773888 | 4.776 / 6.894 | 2666.28 | 2775.24 (2637.69–3062.49) | 4500 | 0 |
| candidate | 1 | true | 2 | 3 | 731499 | 6.064 / 35.582 | 42.40 | 52.11 (47.74–57.78) | 4980 | 20 |
| candidate | 8 | true | 2 | 3 | 731499 | 5.327 / 36.918 | 43.43 | 52.18 (47.86–54.76) | 4980 | 20 |

**Zero dropped semantic events in all 60 runs.** Every emitted event must bump
the authoritative transcript revision. Assertions check the complete ordered
Unicode text, all 20 tool identities/statuses/results, final turn completion,
all 1,000 history entry IDs, and the tree reconstructed from actual transmitted
add/move/delete/set/text operations. The model must match *and* the wire must
match: a fast no-op or an unflushed pending model fails.

Merged text snapshots are deliberately replaceable presentation updates, not
lost text. Hidden panes also merge transient tool `running` snapshots; the
running events are consumed by the model, and all final records/results reach
the resumed surface. Visible runs omit no tool-running snapshots. The candidate
omits one additional hidden running snapshot versus the donor at credits=8,
precisely because it does no hidden painting. No claim that every intermediate
state was displayed is made.

## Profile and cheap win

A separate baseline CPU profile (not included in the timing runs) identifies
SDK `Tree` construction/child-key checking, recursive diff/children/LIS and GC
as the limiter. Summary: [`results/profile.json`](results/profile.json). The
anonymous Tree child callback has 1,593 samples; children 775, diff 592, Tree
constructor 369, rising/LIS 219. Verification apply/place/walk stacks were
excluded; GC samples are not attributed to a specific phase.

Settled entry JSX already caches per revision/cwd/fold revision. Another App
entry cache would not remove SDK `View.from`'s whole-tree rebuilding and diffing,
so no redundant cache or SDK monkeypatch is shipped. The cheap win actually
tried is visibility gating: the donor still does eight hidden builds at
credits=8 and takes 104.07 ms; the candidate does zero and takes 52.18 ms.
At visible credits=8 the SDK is never blocked by this trace and there is no
work for pacing to avoid. This explains both the gain's ceiling and the
negative result instead of claiming a universal speedup.

## Behavioral gates

- `npm --prefix ui-tsp run typecheck` includes the benchmark TypeScript.
- `npm --prefix ui-tsp test`: 351 tests, 28 files passed.
- `npm --prefix ui-tsp run lint`: zero errors, 26 existing unrelated warnings.
- Counter gate proven red on baseline (`502 !== 127`) and green on candidate.
- New App tests exercise credits=1, hidden credits=1/8 and quitting hidden
  without a final ACK. Pump tests guard flushing once at close, stale queued
  callbacks and no change/no work. Feature fixtures now explicitly ACK their
  real SDK surfaces instead of silently relying on rebuilding while blocked.
- The donor by itself failed feature fixtures that never acknowledged their
  initial frames, and its fake splash surface lacked `acknowledge`; fixture
  terminals now implement painting. The candidate does not disable backpressure
  in production or in the separate credit-stall regression tests.
- The final-close flush is necessary: otherwise a quit while blocked would leave
  dirty authoritative state outside the SDK's kept-scrollback final flush.
- Native smoke receipts are reported on the draft PR separately. A synthetic
  terminal replay, tern-serve journey and ordinary signed-in native window are
  distinct evidence classes; this benchmark is only the first.

No merge, preview rewrite, live Tern interaction or SDK dependency edit is part
of this change.
