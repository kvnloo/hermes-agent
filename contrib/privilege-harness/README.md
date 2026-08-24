# Hermes Privilege Harness — typed requester prototype

> Experimental. Do not install this helper as root on a production host.

This branch preserves Corton Kwok's original contribution history while
replacing the original arbitrary-command design with a split-authority,
single-execution prototype.

## Repository placement

Hermes policy does not accept a third-party product plugin or privileged helper
inside the core repository. The helper under `contrib/privilege-harness` is
therefore reviewable prototype code only. A mergeable follow-up must publish it
as a separately maintained Linux package/plugin repository. Hermes core remains
unchanged; only the unprivileged requester integration can be considered after
that external package has a stable protocol.

No installer in this branch should be run. In particular, this design does not
create users, edit sudoers, start a root service, or install anything during a
Hermes update.

## Authority split

- The Hermes plugin is an unprivileged requester. Its tool accepts only
  `operation_id`, typed scalar `slots`, `reason`, `profile`, and `session`.
  It cannot submit a shell, argv, cwd, environment, stdin, or an approval.
- The Linux helper owns a root-controlled immutable catalog. It resolves typed
  slots to an absolute executable and direct argv. Shells, interpreters,
  scripts, PATH lookup, caller environment, caller cwd, stdin, and inherited
  descriptors are rejected or unavailable.
- A distinct operator account uses a separate `operator.sock` and credential.
  Requester and operator UID sets must be disjoint. Both sockets bind the peer
  to Linux `SO_PEERCRED` plus `/proc/<pid>/stat` process start time.
- Hermes native `pre_tool_call` approval is retained only as UX and
  defense-in-depth. It is not sent to or trusted by the helper.

## Single-execution lifecycle

The helper canonicalizes the plan and records its catalog and executable
digests. It records `request -> decision -> reserve -> start -> result` to an
fsynced ledger. The random grant remains broker-internal, expires against a
monotonic clock, is claimed before spawn, and is never returned to requester or
operator. Restart revokes all in-memory grants. A reserved or started operation
without a terminal result is ambiguous and is never spawned again.

Execution uses direct argv, a fixed minimal environment and cwd, null stdin,
closed inherited descriptors, a new process group, a bounded timeout, and one
combined stdout/stderr budget. Limit or timeout termination targets the process
group.

## Operator transport

`operator.sock` is intentionally separate from `request.sock`. The operator
API exposes only inert, escaped and bounded request views plus exact `list` and
`decide` messages. Telegram/Discord delivery belongs to a separately installed
operator frontend running under the operator account; it must keep operator
credentials unavailable to Hermes and render all request fields as inert text.
No messaging connector in this prototype is an authorization authority.

## Verification

The disposable unprivileged tests cover typed plan construction, distinct
credentials and UIDs, requester inability to approve, role-separated Unix
endpoints, one-use concurrent reservation, replay/expiry/restart ambiguity,
catalog and executable mutation, inert approval views, direct execution,
combined output limiting, and interpreter rejection:

    python -m pytest tests/contrib/test_privilege_broker.py \
      tests/plugins/test_privilege_harness_requester.py -q

The tests do not install or invoke sudo and use only inert temporary files and
unprivileged Unix sockets.

## License and attribution

MIT. Original concept and prior commits by Corton Kwok. This security-boundary
revision is a collaborative follow-up and intentionally preserves that history.
