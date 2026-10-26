# RFC143379 demote-gap characterization

Pinned upstream main: `e82bf01eec9bb58848209b07f0bc7d8895a39f9b`
(fetched 2026-10-26). This is **downstream study code only**, not a fix.

## Verdict scope: PARTIAL

The missing memory-specific reload marker is **CONFIRMED at the transcript
mechanism boundary** if `test_real_demote_and_proactive_prune` passes:
`skill_view` gets its exact reload instruction, while an injected historical
`memory(action="read", target="memory")` result does not. Tail demotion points
at `session_search`; proactive pruning keeps generic argument metadata instead.
These two stubs are deliberately not conflated.

An end-to-end `memory(action="read", doc=...)` claim cannot be confirmed on
this pin: main does not ship **either** read action **or** doc argument.
The dispatch test asserts the real rejection; the doc-read test explicitly
skips. The synthetic successful historical read is NOT represented as a
successful call to the currently shipped tool. A doc-shaped fixture is not
passed off as an actual doc read.

The executable receipt (`rfc-out/demote-gap.json`) records PARTIAL overall and
CONFIRMED for the injected-transcript mechanism. The hosted JUnit receipt is
the execution authority; see the draft PR for exact run and tested study SHA.

## Exact upstream evidence

All links/line numbers refer to the pin, not this study's older base:

- `agent/context_compressor_tail.py:11-12`: six protected rounds; 1,500-character floor.
- `agent/context_compressor_tail.py:46-52`: generic session-search recovery stub.
- `agent/context_compressor_tail.py:55-68`: only skill-view call names are indexed.
- `agent/context_compressor_tail.py:99-106`: skill-only reload append at demotion.
- `agent/context_compressor.py:861-866`: canonical skill reload marker.
- `agent/context_compressor.py:1718-1725`: proactive skill-view result summary.
- `agent/context_compressor.py:2018-2022`: generic fallback preserves up to two
  argument values; that is not a memory reload instruction.
- `agent/context_compressor_prune.py:28-75`: real proactive entry point and skill safety rule.
- `tools/memory_tool.py:222-224`: tool signature has no `doc` argument.
- `tools/memory_tool.py:282-283`: unsupported action rejection (see source pin
  and runtime dispatch assertion; the receipt does not rely on a source grep).

Read the source at
<https://github.com/NousResearch/hermes-agent/tree/e82bf01eec9bb58848209b07f0bc7d8895a39f9b>.

## Probe contract

The transcript carries both tool calls and >1,500-character result bodies,
followed by enough completed tool rounds to age them out. UTF-8 fixtures write
real bytes. Assertions cover both real paths, the 1,499/1,500 boundary, newest-six
round protection, canonical skill marker, memory marker absence, loss of the
original body, and non-mutation of the input. Network is blocked. Imports must
resolve to a checkout at the exact upstream SHA or the tests fail.

Sources/credit: xngg1021's
[17:58 comment](https://github.com/NousResearch/hermes-agent/issues/143379#issuecomment-6401144230)
and [18:16 comment](https://github.com/NousResearch/hermes-agent/issues/143379#issuecomment-6401350441).
No upstream posting, memory API change, or production compressor modification.
