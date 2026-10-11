# Supplemental Weixin public cross-loop held-text evidence

LOCAL_ONLY scoped test evidence for NousResearch/hermes-agent PR 135922.
This downstream publication contains a supplemental test, not a competing fix.

## Provenance and ownership

- Implementation owner and original issue reporter: LAIguapi. Owner head: `41d079bd6998b19e31c0503043c4394b6fd6f898`; base: `3eb7ed08d19da393196722d0b219b2ba1ec22810`.
- Requirement: [issue 135921](https://github.com/NousResearch/hermes-agent/issues/135921) reports cron `Deliver: weixin` loss. PRATHAMESH75 identified disposable-adapter loss in [review comment 6092916208](https://github.com/NousResearch/hermes-agent/pull/135922#issuecomment-6092916208); LAIguapi agreed and promised public-send/live-owner coverage in [comment 6093540270](https://github.com/NousResearch/hermes-agent/pull/135922#issuecomment-6093540270).
- LtetMoi separately owns complementary durable final-response recovery, described in [issue comment 6094482487](https://github.com/NousResearch/hermes-agent/issues/135921#issuecomment-6094482487). This test neither implements nor qualifies that work.
- Read current repository and owner-head instructions, test/gateway/PM instructions, CONTRIBUTING.md, and kvnloo/oss-factory AGENTS.md/control-plane/HITL/projects registry.
- Before editing: refreshed issue/PR timelines, reviews, fork issue 447 claims, competing PR 74826/68557/68574/35237/77378 metadata/comments/diffs, recent 100 fork issues, bounded Weixin searches, and all 1144 fork heads. No equivalent public held-text regression found in those surfaces. This is not an exhaustive audit of all historical branches/search results.
- Before this single authorized downstream publication: head/base/owner and all PR-comment IDs/timestamps remained unchanged; all 26 fork issue 447 claim IDs/timestamps remained unchanged. New local and remote branch `test/hermes-135922-cross-loop-hold-20261011` verified absent before creation/push.

## Runtime and exact commands

Linux x86_64; official PM Python 3.14.7; aiohttp 3.14.3;
cryptography 50.0.1; pytest 9.1.1; pytest-asyncio 1.3.0.
Fresh locked project build using dev/test groups and messaging extra.
Disposable HOME, HERMES_HOME and runtime store; no raw pip/uv mutation.

From the owner checkout, provision PM Python then build a fresh output:
```sh
HOME=/workspace/scratch/weixin-supplement/home HERMES_HOME=/workspace/scratch/weixin-supplement/hermes-home HERMES_RUNTIME_DIR=/workspace/scratch/weixin-supplement/runtime python3 -c "import pm; pm.ensure('python', explicit=True)"
HOME=/workspace/scratch/weixin-supplement/home HERMES_HOME=/workspace/scratch/weixin-supplement/hermes-home HERMES_RUNTIME_DIR=/workspace/scratch/weixin-supplement/runtime /workspace/scratch/weixin-supplement/runtime/python-3.14.7+20260901-linux-x64/bin/python3 -m pm.build_env --source . --out /workspace/scratch/weixin-supplement/test-messaging-env --group dev --group test --extra messaging
```

The canonical command below was executed from each isolated worktree:
`/workspace/weixin-cross-loop-hold` at owner head, and
`/workspace/weixin-cross-loop-base` detached at base, with identical final
fixture bytes copied into the base worktree.
```sh
HOME=/workspace/scratch/weixin-supplement/home HERMES_HOME=/workspace/scratch/weixin-supplement/hermes-home HERMES_PYTHON=/workspace/scratch/weixin-supplement/test-messaging-env/bin/python scripts/run_tests.sh tests/gateway/test_weixin_cross_loop_hold.py tests/gateway/test_weixin.py --file-retries 0 -j 1
```
Loopback 127.0.0.1 bind/listen was confirmed. Canonical runner requires its
`/var/tmp/hermes-pytest-1000` scratch directory; the parent run obtained a scoped
writable grant, with no runner modification or conftest exclusion.

Head checks, also repeated against the final publication contents:
```sh
HOME=/workspace/scratch/weixin-supplement/home HERMES_HOME=/workspace/scratch/weixin-supplement/hermes-home HERMES_RUNTIME_DIR=/workspace/scratch/weixin-supplement/runtime /workspace/scratch/weixin-supplement/test-messaging-env/bin/python scripts/check --base 41d079bd6998b19e31c0503043c4394b6fd6f898
git diff --check
git diff --cached --check
```

## Final behavioral results and log extracts

| Revision | New supplemental | Existing test_weixin.py | Combined result |
|---|---|---|---|
| Owner head | 1 passed | 50 passed | 51 passed / 0 failed, exit 0 |
| Base | 1 failed | 33 passed | 33 passed / 1 failed, exit 1 |

The existing suite counts differ because the owner PR added tests. These are
separate revision runs, never an independent 84-test gate.

Head canonical log:
```text
[ 97.8% |    45/~46 | ✓50 | ✗ 0] ✓ tests/gateway/test_weixin.py (50✓, 1.3s)
[100.0% |    46/~46 | ✓51 | ✗ 0] ✓ tests/gateway/test_weixin_cross_loop_hold.py (1✓, 0.6s)
=== Summary: 2 files, 51 tests passed, 0 failed (100% complete) in 1.9s (1 workers) ===
```
Base canonical log:
```text
[ 96.9% |    31/~32 | ✓33 | ✗ 0] ✓ tests/gateway/test_weixin.py (33✓, 2.0s)
[100.0% |    32/~32 | ✓33 | ✗ 1] ✗ tests/gateway/test_weixin_cross_loop_hold.py (1✗, 2.1s)
> assert result.get("success") is True, result
E AssertionError: {'error': 'Weixin send failed: iLink sendmessage session not ready: ret=-2 errcode=None errmsg=prepare failed — the user must send the bot a message first (or re-pair)'}
WARNING gateway.platforms.weixin: session expired for syntheti; retrying without context_token
ERROR gateway.platforms.weixin: send failed to=syntheti: iLink sendmessage session not ready: ret=-2 errcode=None errmsg=prepare failed — the user must send the bot a message first (or re-pair)
```
Base fails on the public behavior after actual HTTP refusal/tokenless retry,
before assuming a hold method exists. This is not an import/setup failure.
Final fixture checks: eleven checks passed; new Python file measured with zero
blocking/advisory findings; diff whitespace checks passed.

## Real versus substituted boundaries

Real adapter connect/disconnect and registration, public selector, actual
aiohttp sessions, HTTP serialization/refusal parsing, persisted context store,
queue, call_soon_threadsafe, allowlist intake, actual _process_message,
context refresh and flush, base batching/handle_message, and session/task
cleanup. Delegating observers call the original _new_session and live
_hold_outbound_text; they record identity without replacing behavior.

External iLink is substituted by a loopback HTTP server. getupdates remains
open; getconfig/typing return synthetic success; sendmessage switches from
ret=-2/prepare failed to success. The registered inbound handler records
invocation and does not run a model. Inbound is explicitly fed to actual
_process_message, not delivered through polling ingress.

Assertions/records:
- Worker B uses a different loop object and thread ID from owner A; real hold
  executes on A's exact loop/thread.
- Three actual sessions exist: live poll/send on A and temporary send on B.
  Temporary session is closed, B's loop is closed, live send session remains
  open, and the live queue still contains exactly the held text.
- HTTP attempts contain old context then tokenless refusal; no successful
  delivery occurs while closed.
- Successful held HTTP delivery echoes fresh inbound context. Dispatch snapshot
  sees exactly that delivery; order is held-send then inbound-dispatch; queue
  is empty.
- Second distinct authorized inbound causes no further send: three total
  attempts, one successful held delivery. Actual inbound tasks finish before
  disconnect and all recorded sessions close.

## Independent critique, setup failures and limits

Independent xhigh critic reviewed repository instructions, production source,
fixture and head/base logs. Its independent rerun stopped before collection
on read-only scratch; that rerun was not retried by another route and is not
a pass. The parent receipts are the runtime evidence. Critic identified a P3
missing typing endpoint/cleanup concern; parent corrected the fixture, reran
both revisions and checks, and critic approved the revised source with no
remaining findings. Critic made no edits or publication.

Separate setup failures: nonexistent --extra weixin; core-only environment
lacked aiohttp; initial canonical attempt collected zero tests on read-only
scratch; one initial base process could not start because the worktree path
was not created. None is counted as a test pass.

No live iLink or polling-ingress certification; exactly-once is only the
controlled loopback trace. No durable-final, media, TTL-policy, whole-send
bridge, full-project, macOS or Windows claim. No real credentials, peer data,
live messaging, external provider/model requests, security changes or user
installation. Only synthetic credentials/data were used. No external messages
or upstream posts. This lease authorizes only a normal new downstream branch
push; no main/default-branch, force, merge, destructive action or fake DCO.

Full sanitized packet retained in ChatGPT Library as
Hermes-135922-cross-loop-hold-regression-packet.md,
identity libfile_3ac109b7d5988191874d6cec619ef2ca, version 0.

## SHA-256 evidence digests

```json
{
  "final test": "ca203911617b5f7e957aa44f43c38a5a14471b618846f6de7fca004b7963881d",
  "owner uv.lock": "2bc4db483e9cba927cd7147f9ccbb09635f85bb3f1f36d6e9d51d06b65d1c67e",
  "owner PM lock": "49b79259220160f147255078a19af541a5f328d3871c8041cc1eb909d19eb549",
  "full head log": "32d70398ea1fe2141ffa149c7300ed1d614545d997a1f53d2338e7bc5c5a9d9e",
  "full base log": "7189162cc62e003dfa22c6d4fe1cd7dee8ab605883ac06fd7f8220266abeaf70",
  "fixture checks log": "4ca29f67023209342015e2040892e18efcc1290ccf7bc8c01da2c6544f0fdff5",
  "installed distribution inventory": "5698748e40566c0c2c24e3f0e716bac35c22d68f4a2ce30321db38a3df0c9240",
  "Library packet bytes": "5e7b68b57af208827c599d0a93459e23a38905f381aae072fba4a6dd28e8e261"
}
```
