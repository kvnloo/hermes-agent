# Architecture Decision Records

## 2026-07-13: Scope plugin manager state by Hermes home/profile (keyed cache)

Status: Accepted

Context:
Hermes supports multiple profiles via different Hermes home directories.
Homes are switched two ways in a running process: the `HERMES_HOME`
environment variable (single-profile CLI/gateway processes), and the
context-local `set_hermes_home_override()` (`hermes_constants.py`), which
the multiplexed gateway worker (`gateway/run.py`'s `_profile_scope`) and
subagent/embedded callers use to serve several profiles from one
long-lived process. The override is a `ContextVar` and deliberately does
**not** mutate `os.environ`, since that would leak one profile's home
into every other concurrent task in the same process.

The plugin manager was a process-global single-slot singleton
(`_plugin_manager`). User-installed plugins are discovered from
`get_hermes_home() / "plugins"`, and context-engine plugins (e.g.
`hermes-lcm`) capture profile-scoped state — such as the LCM database
path — at registration time. A single-slot cache meant:

1. Switching homes via `set_hermes_home_override()` was invisible to a
   naive "did `HERMES_HOME` change" check, so the singleton silently kept
   serving the first profile's manager to every other profile in the
   process.
2. Even when a fresh `PluginManager` *was* created for a new home, plugin
   modules are imported into `sys.modules` as `hermes_plugins.<slug>` by
   `_load_directory_module`, and only that top-level module was ever
   replaced. A same-slug plugin's *relative* imports
   (`from . import state`) are cached separately under
   `hermes_plugins.<slug>.<submodule>`, and Python's import machinery
   resolves those from `sys.modules` first — so a profile switch could
   silently keep serving a previous profile's already-imported submodule
   code/state instead of re-executing the new profile's plugin.

Decision:
- Replace the single-slot singleton with a cache keyed on the *resolved*
  Hermes home path (`_plugin_managers_by_home: Dict[Path, PluginManager]`).
  `get_plugin_manager()` resolves the current home via `get_hermes_home()`
  (which itself already consults `get_hermes_home_override()` before
  `os.environ`), so both the env-var and context-local override paths are
  covered uniformly.
- `_plugin_manager` (the old single-slot name) is kept as a thin "last
  manager returned" pointer purely for backward compatibility with
  existing test code that does
  `monkeypatch.setattr(plugins_mod, "_plugin_manager", some_manager)`.
  When that name is monkeypatched to a manager the keyed cache doesn't
  know about, `get_plugin_manager()` treats it as an explicit injection
  and adopts it into the cache under the *current* resolved home, rather
  than discarding it.
- Both `PluginManager._load_directory_module` (initial/`force=True`
  reload within the same home) and the shared `_clear_plugin_submodules`
  helper (profile switch / test teardown) evict `sys.modules[module_name]`
  **and every name prefixed with `module_name + "."`** before a plugin
  slug is (re-)imported, so relative-import submodules can never survive
  a reload or a home switch.
- Test isolation (`tests/conftest.py`'s `_hermetic_environment` fixture)
  calls a new `_reset_plugin_managers_for_tests()` helper that drops the
  entire keyed cache and purges every plugin submodule from `sys.modules`
  between tests, instead of only resetting the single-slot pointer.

Consequences:
- Per-profile LCM instances (and any other context-engine plugin) use
  their own `{home}/lcm.db` regardless of whether the profile switch went
  through `HERMES_HOME` or `set_hermes_home_override()`.
- Plugin discovery remains cached within a profile for normal
  performance, and re-entering a previously-seen profile reuses its
  cached manager instead of rebuilding from scratch.
- Sequential *and* interleaved profile switching — in tests, the gateway
  multiplexer worker, or embedded callers using the context-local
  override — no longer leaks context-engine state, plugin module state,
  or stale relative-import submodules across profiles.
- Regression coverage exercises the real production path
  (`set_hermes_home_override()`) rather than only the env-var path, and
  includes a dedicated relative-import leak test.

## 2026-08-21: Defer durable plugin inject-once until the gateway owns a durable inbox

Status: Implemented as a local candidate; independent review required

Implementation status (2026-08-21):
- `gateway/inbox.py` now owns transactional acceptance, globally unique opaque
  keys, immutable binding/digest conflict checks, leases, durable turn IDs,
  bounded receipt-backed compaction, and an additive versioned migration in the
  canonical profile `state.db`.
- `GatewayRunner` authorizes and commits before returning `ACCEPTED`, drains on
  commit/startup, and carries inbox/key/turn identity in `MessageEvent.metadata`.
  `PluginContext.inject_message_once()` is a thin typed wrapper and never falls
  back to legacy injection; `inject_message()` remains unchanged.
- The candidate intentionally claims accepted-once conversation input, not
  exactly-once model/provider or outbound-platform side effects. Independent
  crash-boundary and clean-archive review remains required before release or
  bridge activation.

Context:
`PluginContext.inject_message()` currently hands a gateway request to a
process-local callable. `GatewayRunner._schedule_plugin_message_injection()`
reports success after creating an asyncio task, before session lookup,
authorization, adapter selection, or adapter dispatch. The task later builds a
`MessageEvent` and calls `BasePlatformAdapter.handle_message()`. That method is
also process-local: it either stores the event in the adapter's in-memory
`_pending_messages` slot or spawns background processing and returns. Transcript
rows are persisted only after the agent turn. Therefore none of the existing
success boundaries is a durable receiver enqueue boundary.

Adding an idempotency table in front of this path is unsafe. Committing the key
before `handle_message()` can lose an accepted message on crash; committing it
afterward can dispatch twice on retry. Marking an inbox row consumed before
calling the adapter has the same loss window, while marking it afterward has the
same duplicate window. SQLite cannot atomically commit with asyncio task
creation, an in-memory adapter queue, model/provider side effects, or platform
reply side effects. Consequently a truthful inject-once operation requires a
broader gateway receiver change, not a plugin-side ledger or a new wrapper over
the current scheduler.

Decision:
- Do not add `PluginContext.inject_message_once()` until the durable receiver
  described below exists. Capability detection must continue to return false;
  callers requiring idempotency must retain their source event and retry on a
  future Hermes version. They must not fall back to `inject_message()`.
- Keep legacy `inject_message()` behavior and its boolean, process-local
  acceptance semantics unchanged.
- The future contract returns a typed `InjectionOutcome` with `INJECTED`
  (durably committed for the first time), `ALREADY_ACCEPTED` (same scope and
  digest), `RETRYABLE_FAILURE` (no commit, including busy/I/O failure), and
  `REJECTED` (validation, authorization, conflict, or corruption). A conflict
  is `REJECTED`, never an already-accepted result.

Required receiver architecture (one atomic change set):
1. Add a `gateway_inbox` table to profile-local `state.db` through
   `hermes_state_common.SCHEMA_SQL` and the normal `SessionDB` schema
   reconciliation. Its immutable identity is
   the globally unique `idempotency_key`. Store `profile_home_digest`,
   `plugin_id`, `session_key`, `event_generation`, `payload_digest`, the durable
   payload, role, `accepted_at`, state, lease owner/expiry, `consumed_at`, and
   `retain_until`. A same-key insert with any different binding or payload is a
   conflict. The profile digest is derived
   from the exact resolved Hermes home bytes and is checked against the
   currently opened DB; it is not supplied by the plugin.
2. In one `BEGIN IMMEDIATE` transaction, validate the destination against the
   durable session-routing record, validate the current gateway authorization
   generation, insert the inbox row, and return `INJECTED`. On uniqueness,
   compare every immutable field and return `ALREADY_ACCEPTED` only for an
   exact match. Map SQLite busy and storage I/O failures before commit to
   `RETRYABLE_FAILURE`; map malformed/corrupt stores to `REJECTED` and do not
   recreate, truncate, vacuum, or bypass the store.
3. Replace direct plugin scheduling with a gateway inbox worker. On startup and
   after each commit notification, it leases pending rows using a transactional
   compare-and-swap. Leases make crash recovery at-least-once at the worker
   boundary; they do not by themselves justify exactly-once delivery.
4. Carry the immutable inbox identity on `MessageEvent` and through
   `_process_message_background`. Before any model call, atomically create a
   durable turn record keyed by the inbox identity and bind it to the session
   generation. Replays finding that turn record must resume its recorded state,
   not create another turn. Mark the inbox consumed in the same transaction
   that durably establishes the turn. This is the first safe handoff from inbox
   to conversation processing.
5. Provider and outbound platform side effects need durable operation IDs and
   replay-aware adapters. Without provider/platform idempotency, Hermes may
   guarantee one accepted conversation turn but cannot claim exactly-once
   external effects after a crash during an unacknowledged call. The public API
   documentation must say “accepted once” unless every downstream effect in the
   selected path supports that stronger contract.
6. Validate without normalization: role is one of the explicitly supported
   roles; plugin ID, session key, event generation, idempotency key, and UTF-8
   payload have fixed byte ceilings. Reject empty identifiers, control bytes,
   malformed UTF-8 inputs, and over-limit values. Logs contain plugin/session
   digests and a bounded key prefix only, never the message body.
7. Retain accepted identities for a configured horizon measured from
   `accepted_at` (and never shorter than the maximum source retry horizon).
   Compaction deletes only consumed, expired rows in bounded transactions.
   Pending/leased rows and accepted identities inside the horizon are never
   reused. Schema rollback leaves the additive table readable by older Hermes;
   old processes cannot consume it and therefore cannot falsely acknowledge it.

Required verification before changing this ADR to Accepted:
- Real `PluginContext` integration through a live `GatewayRunner` and test
  adapter; no synthetic receiver mock.
- Two processes and multiple threads racing the same key produce one inbox row
  and one durable turn; exact retry returns `ALREADY_ACCEPTED`; payload, plugin,
  profile, session, and generation conflicts fail closed.
- Deterministic crash injection before begin, before insert, before commit,
  after commit, after lease, before/after durable-turn creation, and before/after
  adapter handoff, followed by process restart and startup drain.
- SQLite busy, ENOSPC/fsync/I/O errors, read-only DB, malformed DB, and schema
  migration failures return the specified outcome without a false acceptance.
- Retention/lease expiry under a fake clock, old-process compatibility, legacy
  `inject_message()` behavior, bounded input validation, and a log/DB privacy
  scan.
- Relevant session-store, gateway, adapter, shutdown/restart, plugin discovery,
  and plugin injection suites pass from a clean archive.

Consequences:
This change deliberately provides no superficially convenient API. The blocked
Taildrop bridge remains pending rather than risking duplicate or lost injection.
The smallest honest implementation is the durable gateway inbox plus durable
turn handoff above; a standalone plugin ledger is explicitly rejected.
