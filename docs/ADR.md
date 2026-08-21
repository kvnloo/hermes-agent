# Architecture Decision Records

## 2026-08-21: Durable session notifications are not messages

Status: Accepted

Plugin-originated notification metadata lives in the versioned
`session_notifications` table in the canonical profile `state.db`. A
notification is not a `user`, `assistant`, or `system` message. Acceptance must
never append to `messages`, schedule a gateway turn, call a model, tool,
adapter, platform sender, or alter prompt assembly. This replaces rejected
candidate `c0baef9e7b44969df52b9c5036c472fe6f8f54be` while preserving lineage.

`PluginContext.append_notification_once` performs one globally keyed atomic
insert/lookup. Exact binding/digest replay returns `ALREADY_ACCEPTED`; mismatch
returns `CONFLICT`. Reads require exact profile/plugin/session ownership. Only
an explicit user/Captain action may acknowledge with exact generation and actor
identity. Pending rows never compact; acknowledged rows use bounded,
receipt-backed retention.

Metadata is allowlisted to `event`, `sender`, `device`, `sha256`, `bytes`,
`generation`, and `status_label`. Content, commands, paths, secrets, tokens,
and unknown fields are rejected. Legacy candidate rows remain as evidence and
are copied only as quarantined metadata; transcript content is never deleted.
A future user-driven prompt snapshot requires a separate review. No automatic
acknowledgment, delivery worker, or processing queue is authorized here.

Boundary proof drives synthetic Telegram `MessageEvent` values through
`GatewayRunner._handle_message`, before command resolution, slash access, and
busy-session policy. It guards the model loop, tool dispatcher, platform send,
pending queues, and all SessionDB message/metadata mutation surfaces while
asserting byte- and row-identical transcripts. Storage adversity uses SQLite's
real `max_page_count` limit, and crash adversity uses spawned processes that
terminate with `os._exit` immediately before or after migration, acceptance,
acknowledgment, and compaction commits; the parent reopens and retries the same
database to prove rollback-or-complete semantics.

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
