# PR #136165: supplemental forced-refresh evidence

Downstream-only evidence of a remaining recovery-contract gap. Production
implementation belongs to **liuhao1024**. **azhang** is the verified reporter of
[issue #136151](https://github.com/NousResearch/hermes-agent/issues/136151).
[Kevin's COMMENT review](https://github.com/NousResearch/hermes-agent/pull/136165#pullrequestreview-5479888832)
requests terminal-singleton plus forced-pool-refresh coverage; it is reviewer
evidence, not maintainer approval. No upstream publication or production fix.

| Revision | Qualified result | Terminal-singleton failure |
| --- | --- | --- |
| Head `71e74e11bc389c0ee4a02b09f88dd42421d46bbe` | **14 PASS / 1 FAIL** | Returns expired independent B; fresh-B assertion fails |
| Base `a62979dc3601c9eae455bff5b35ba8f9bed0df30` | **11 PASS / 1 FAIL** | Propagates A's parsed synthetic `invalid_grant` AuthError |

Both pool-only positive controls pass. Existing provider tests pass: 13 on head,
10 on base (the PR adds three tests). Both runner exits are 1, with retries
disabled. **This is not RED/GREEN or a regression from a passing base.** The
base already fails the recovery contract; the head changes the failure mode
without meeting forced pool rotation. Do not describe the gap as fixed.

## Reproduce

`fixture.py` is stored outside the ordinary test suite and never participates
in default CI discovery. Replay places it in a newly created disposable
detached worktree only. The script retains that worktree and reports its path.

Use the repository-supported Python 3.14 bootstrap and a fresh PM output:

```sh
HOME=<DISPOSABLE_HOME> HERMES_HOME=<DISPOSABLE_HERMES_HOME> CODEX_HOME=<DISPOSABLE_CODEX_HOME> \
  <SUPPORTED_PYTHON_3_14> -m pm.build_env --source . \
  --out <NEW_TEST_ENV> --python <SUPPORTED_PYTHON_3_14> --group dev --group test

evidence/hermes-136165-terminal-forced-refresh-20261011/replay.sh head <NEW_TEST_ENV>/bin/python
evidence/hermes-136165-terminal-forced-refresh-20261011/replay.sh base <NEW_TEST_ENV>/bin/python
```

The exact final canonical runner arguments appear in `receipt.json`. Replay
uses them with disposable HOME, HERMES_HOME and CODEX_HOME. Recorded interpreter:
CPython 3.14.7, pytest 9.1.1, httpx 0.28.1; complete installed versions are in
`versions.json`. The pinned revisions have identical dependency manifests.
Canonical runner syntax `--file-retries 0 -j 1` was verified. It needs writable
canonical scratch storage; in the managed environment, write permission was
scoped to its per-user pytest scratch directory.

## Boundary and qualifications

The real disposable auth store contains rejected singleton A, A's pool mirror,
and independently expired refreshable B. Distinct synthetic JWT `sub` and nested
`chatgpt_account_id` claims establish distinct recognized principals. The only
substituted function is `auth_codex._codex_http_client`, returning a real httpx
client with MockTransport: A receives synthetic HTTP 400, B synthetic HTTP 200
with rotated bytes. No real credentials or OAuth/provider network requests.
No real HOME token or network data entered this packet.

The resolver, OAuth serialization/parser, pool refresh methods, persistence and
locks remain real. The pool-only control exercises `try_refresh_matching`,
`_refresh_entry` and `_post_tokens_refresh` and verifies B's independently owned
persisted pair. Locks run **uncontended**; this does not certify cross-process or
borrowed-grant safety. Head's terminal branch bypasses that refresh. Its later
source/status/singleton/mirror-preservation assertions are **not reached** after
the first failure. No claim about failed B refresh or an end-to-end gateway
request. The HTTP factory's response-size hook and Happy Eyeballs setup are
outside this substitution's scope.

#133560 borrowed-grant locking and #123764 DEAD-row ownership remain with their
existing owners; neither is changed or certified by this evidence.

An independent xhigh critic inspected requirements, source, fixture, identical
hashes and final logs; **it did not independently rerun**. Its full qualification
is `critic.md`. Corrections were rerun on both revisions before qualification.

## Setup failures, excluded from results

Initial canonical attempts failed before collection because the sandbox could
not write runner scratch; **zero tests ran**. Scoped scratch access corrected
this. An intermediate fixture made HERMES_HOME equal synthetic HOME/.hermes,
triggering the auth-store safety guard. Moving HERMES_HOME to a distinct
disposable directory corrected it without changing the guard. The critic then
requested complete principal claims; those were added before the final,
byte-identical runs. Earlier attempts are not behavioral evidence.

`head.log.json` and `base.log.json` contain the exact final qualified output with only
absolute checkout/interpreter/temp paths replaced by explicit placeholders;
no lines or whitespace were omitted. JSON preserves the exact output string;
extract it with `jq -r .output head.log.json` (and likewise for base). Raw log
hashes and the published file hashes are recorded separately.
No private absolute paths, raw auth-store dumps or real credential data are
published. GitHub source reads and PM dependency acquisition are distinct from
the fully synthetic OAuth transport.

Before publication, PR head/owner and all 26 #447 comments were refreshed:
head unchanged, no new comments or matching supplemental evidence claim.
Relevant overlapping fork diffs were reviewed; the selected new branch was
absent remotely. No default-branch change, force push, upstream comment/PR,
credential setup, security-setting modification or denied-action workaround.
