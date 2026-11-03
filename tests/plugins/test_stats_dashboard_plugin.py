"""Tests for the stats-dashboard plugin (``plugins/stats-dashboard/``).

* exporter: Hermes ``state.db`` rows -> omp session JSONL (tool spans, subagents, usage, compaction),
  incremental watermarks, read-only source;
* dashboard: the omp child env never points at ``~/.omp``;
* ``/stats`` handler: missing omp, status and help replies.
"""

import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "stats-dashboard"


if "hermes_plugins" not in sys.modules:  # the PluginManager's namespace package, for relative imports
    sys.modules["hermes_plugins"] = types.ModuleType("hermes_plugins")
    sys.modules["hermes_plugins"].__path__ = []


def _load(name):
    spec = importlib.util.spec_from_file_location(f"hermes_plugins.stats_dashboard.{name}", PLUGIN_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


exporter = _load("exporter")
dashboard = _load("dashboard")


def _load_plugin():
    spec = importlib.util.spec_from_file_location(
        "hermes_plugins.stats_dashboard", PLUGIN_DIR / "__init__.py", submodule_search_locations=[str(PLUGIN_DIR)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


SCHEMA = """
CREATE TABLE sessions (id TEXT PRIMARY KEY, source TEXT NOT NULL, model TEXT, model_config TEXT,
  parent_session_id TEXT, started_at REAL NOT NULL, ended_at REAL, end_reason TEXT, cwd TEXT, title TEXT,
  billing_provider TEXT, message_count INTEGER DEFAULT 0, transcript_revision INTEGER DEFAULT 0);
CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
  content TEXT, tool_call_id TEXT, tool_calls TEXT, tool_name TEXT, timestamp REAL NOT NULL, finish_reason TEXT,
  active INTEGER NOT NULL DEFAULT 1, compacted INTEGER NOT NULL DEFAULT 0,
  _compressed_summary INTEGER NOT NULL DEFAULT 0);
CREATE TABLE session_model_usage (session_id TEXT NOT NULL, model TEXT NOT NULL,
  billing_provider TEXT NOT NULL DEFAULT '', billing_base_url TEXT NOT NULL DEFAULT '',
  billing_mode TEXT NOT NULL DEFAULT '', task TEXT NOT NULL DEFAULT '', api_call_count INTEGER NOT NULL DEFAULT 0,
  input_tokens INTEGER NOT NULL DEFAULT 0, output_tokens INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens INTEGER NOT NULL DEFAULT 0, cache_write_tokens INTEGER NOT NULL DEFAULT 0,
  reasoning_tokens INTEGER NOT NULL DEFAULT 0, estimated_cost_usd REAL NOT NULL DEFAULT 0,
  actual_cost_usd REAL NOT NULL DEFAULT 0, cost_status TEXT, cost_source TEXT, first_seen REAL, last_seen REAL);
"""

T0 = 1_793_667_769.0


def _tool_call(call_id, name, args):
    return {"id": call_id, "call_id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


@pytest.fixture
def state_db(tmp_path):
    path = tmp_path / "state.db"
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.execute("INSERT INTO sessions VALUES ('parent','cli','claude-opus-5-5',NULL,NULL,?,?, 'cli_close',"
               "'/work/repo','Fix the build','anthropic',6,0)", (T0, T0 + 60))
    db.execute("INSERT INTO sessions VALUES ('child','subagent','gpt-6.1-sol',?, 'parent',?,?,NULL,'/work/repo',"
               "NULL,'openai-codex',3,0)", (json.dumps({"_delegate_from": "parent"}), T0 + 10, T0 + 40))
    db.execute("INSERT INTO sessions VALUES ('branch','cli','claude-opus-5-5',NULL,'parent',?,NULL,NULL,'/work/repo',"
               "'Branch',NULL,0,0)", (T0 + 100,))
    rows = [
        ("parent", "user", "please build", None, None, None, T0 + 1.0, None, 1, 0, 0),
        ("parent", "assistant", "running it", None, json.dumps([_tool_call("call_1", "terminal", {"command": "make"})]),
         None, T0 + 3.0, "tool_calls", 1, 0, 0),
        ("parent", "tool", json.dumps({"output": "ok", "exit_code": 0}), "call_1", None, "terminal", T0 + 7.5, None, 1, 0, 0),
        ("parent", "assistant", "", None, json.dumps([_tool_call("call_2", "delegate_task", {"goal": "review"})]),
         None, T0 + 9.0, "tool_calls", 1, 0, 0),
        ("parent", "tool", json.dumps({"error": "boom"}), "call_2", None, "delegate_task", T0 + 41.0, None, 1, 0, 0),
        ("parent", "assistant", "rewound reply", None, None, None, T0 + 42.0, "stop", 0, 0, 0),
        ("parent", "user", "summary of earlier turns", None, None, None, T0 + 43.0, None, 1, 0, 1),
        ("parent", "assistant", "done", None, None, None, T0 + 45.0, "stop", 1, 0, 0),
        ("child", "user", "review the diff", None, None, None, T0 + 10.5, None, 1, 0, 0),
        ("child", "assistant", "", None, json.dumps([_tool_call("c_1", "read_file", {"path": "a.py"})]),
         None, T0 + 12.0, "tool_calls", 1, 0, 0),
        ("child", "tool", "contents", "c_1", None, "read_file", T0 + 12.2, None, 1, 0, 0),
    ]
    db.executemany("INSERT INTO messages (session_id, role, content, tool_call_id, tool_calls, tool_name, timestamp,"
                   " finish_reason, active, compacted, _compressed_summary) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.execute("INSERT INTO session_model_usage (session_id, model, billing_provider, api_call_count, input_tokens,"
               " output_tokens, cache_read_tokens, cache_write_tokens, estimated_cost_usd, cost_status, first_seen,"
               " last_seen) VALUES ('parent','claude-opus-5-5','anthropic',3,100,50,1000,10,0.25,'estimated',?,?)",
               (T0 + 2, T0 + 45))
    db.execute("INSERT INTO session_model_usage (session_id, model, billing_provider, billing_mode, api_call_count,"
               " input_tokens, output_tokens, cost_status, last_seen) VALUES"
               " ('child','gpt-6.1-sol','openai-codex','subscription_included',2,20,5,'included',?)", (T0 + 12,))
    db.commit()
    db.close()
    return path


def _export(state_db, tmp_path, **kwargs):
    source = exporter.HermesStateSource(state_db, "test")
    try:
        return exporter.export([source], tmp_path / "omp" / "agent" / "sessions", **kwargs)
    finally:
        source.close()


def _entries(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_layout_nests_subagents_and_keeps_other_children_top_level(state_db, tmp_path):
    report = _export(state_db, tmp_path)
    assert report.written == 3
    rel = {k: p.relative_to(report.sessions_dir) for k, p in report.paths.items()}
    assert rel["parent"].parts[0] == "--work-repo--"
    assert len(rel["parent"].parts) == 2
    # Subagent: <project>/<parent stem>/<child stem>.jsonl, which omp classifies as `subagent`.
    assert rel["child"].parent == rel["parent"].with_suffix("")
    # A branch child is its own conversation, not a subagent.
    assert len(rel["branch"].parts) == 2
    assert all(p.exists() for p in report.paths.values())


def test_messages_tool_spans_and_usage_map_to_omp_entries(state_db, tmp_path):
    report = _export(state_db, tmp_path)
    entries = _entries(report.paths["parent"])
    header = entries[0]
    assert header == {"type": "session", "version": 3, "id": "parent", "timestamp": "2026-11-03T01:02:49.000Z",
                      "cwd": "/work/repo", "title": "Fix the build"}
    # One linear parentId chain, so omp's active-branch walk keeps every entry.
    ids = [e["id"] for e in entries[1:]]
    assert [e["parentId"] for e in entries[1:]] == [None] + ids[:-1]

    messages = [e["message"] for e in entries if e["type"] == "message"]
    call_turn = next(m for m in messages if m["role"] == "assistant" and m["content"][-1].get("id") == "call_1")
    assert call_turn["content"][-1] == {"type": "toolCall", "id": "call_1", "name": "terminal",
                                        "arguments": {"command": "make"}}
    # Model span = previous row (the user message) -> this row; no api/usage, so stats never double count.
    assert call_turn["timestamp"] == int((T0 + 1.0) * 1000)
    assert call_turn["completedAt"] == int((T0 + 3.0) * 1000)
    assert "api" not in call_turn
    result = next(m for m in messages if m["role"] == "toolResult" and m["toolCallId"] == "call_1")
    assert result["timestamp"] == int((T0 + 7.5) * 1000) and result["isError"] is False
    failed = next(m for m in messages if m["role"] == "toolResult" and m["toolCallId"] == "call_2")
    assert failed["isError"] is True and failed["toolName"] == "delegate_task"

    # Rewound rows (active=0, compacted=0) are not part of the transcript; summaries are compactions.
    texts = [b.get("text") for m in messages for b in m.get("content", []) if isinstance(b, dict)]
    assert "rewound reply" not in texts
    compaction = next(e for e in entries if e["type"] == "compaction")
    assert compaction["summary"] == "summary of earlier turns" and "tokensBefore" not in compaction

    usage = next(e for e in entries if e["type"] == "model_usage")
    assert usage["model"] == "claude-opus-5-5" and usage["provider"] == "anthropic"
    assert usage["api"] == "anthropic-messages"
    assert usage["usage"] == {"input": 100, "output": 50, "cacheRead": 1000, "cacheWrite": 10, "totalTokens": 1160,
                              "cost": {"total": 0.25}}
    exit_marker = entries[-1]
    assert exit_marker["type"] == "custom" and exit_marker["customType"] == "session_exit"
    assert exit_marker["data"]["kind"] == "cli_close"


def test_subagent_file_has_init_and_its_own_usage(state_db, tmp_path):
    report = _export(state_db, tmp_path)
    entries = _entries(report.paths["child"])
    init = entries[1]
    assert init["type"] == "session_init" and init["agent"] == "subagent" and init["resolvedModel"] == "gpt-6.1-sol"
    usage = next(e for e in entries if e["type"] == "model_usage")
    # A priced subscription row keeps Hermes's recorded zero.
    assert usage["usage"]["cost"] == {"total": 0.0} and usage["provider"] == "openai-codex"


def test_unpriced_usage_omits_cost_instead_of_inventing_one(state_db, tmp_path):
    db = sqlite3.connect(state_db)
    db.execute("UPDATE session_model_usage SET cost_status = NULL, estimated_cost_usd = 0 WHERE session_id='parent'")
    db.commit()
    db.close()
    usage = next(e for e in _entries(_export(state_db, tmp_path).paths["parent"]) if e["type"] == "model_usage")
    assert "cost" not in usage["usage"]


def test_export_is_incremental_and_prunes_deleted_sessions(state_db, tmp_path):
    first = _export(state_db, tmp_path)
    child_mtime = first.paths["child"].stat().st_mtime_ns
    again = _export(state_db, tmp_path)
    assert (again.written, again.unchanged) == (0, 3)

    db = sqlite3.connect(state_db)
    db.execute("INSERT INTO messages (session_id, role, content, timestamp) VALUES ('parent','user','more',?)",
               (T0 + 50,))
    db.execute("DELETE FROM sessions WHERE id='branch'")
    db.commit()
    db.close()
    third = _export(state_db, tmp_path)
    assert (third.written, third.unchanged, third.removed) == (1, 1, 1)
    assert first.paths["child"].stat().st_mtime_ns == child_mtime
    assert not first.paths["branch"].exists()
    assert "more" in first.paths["parent"].read_text(encoding="utf-8")


def test_only_keys_exports_the_current_session_tree(state_db, tmp_path):
    source = exporter.HermesStateSource(state_db, "test")
    keys = exporter.session_tree_keys(source.scan(), "child")
    source.close()
    assert keys == {"parent", "child"}
    report = _export(state_db, tmp_path, only_keys=keys)
    assert report.written == 2 and not report.paths["branch"].exists()


def test_source_is_read_only(state_db, tmp_path):
    before = state_db.read_bytes()
    source = exporter.HermesStateSource(state_db, "test")
    with pytest.raises(sqlite3.OperationalError):
        source._db().execute("DELETE FROM messages")
    source.close()
    _export(state_db, tmp_path)
    assert state_db.read_bytes() == before


def test_omp_env_pins_every_omp_path_to_the_export_root(tmp_path):
    root = tmp_path / "home" / ".hermes" / "omp-stats"
    base = {"HOME": str(tmp_path / "home"), "XDG_DATA_HOME": "/x", "XDG_STATE_HOME": "/y",
            "XDG_CACHE_HOME": "/z", "OMP_PROFILE": "work", "PI_CODING_AGENT_DIR": "/elsewhere", "PATH": "/bin"}
    env = dashboard.omp_env(root, base)
    assert env["PI_CONFIG_DIR"] == ".hermes/omp-stats"
    assert env["PI_CODING_AGENT_DIR"] == str(root / "agent")
    assert env["PI_NATIVES_DIR"] == str(root / "natives")
    assert not {"XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME", "OMP_PROFILE"} & set(env)
    assert env["PATH"] == "/bin"


def test_trace_url_deep_links_the_session_file():
    url = dashboard.trace_url("127.0.0.1", 3858, Path("/h/omp-stats/agent/sessions/--p--/a b.jsonl"))
    assert url == "http://127.0.0.1:3858/#/traces?range=all&s=%2Fh%2Fomp-stats%2Fagent%2Fsessions%2F--p--%2Fa%20b.jsonl"


class _Ctx:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.commands = {}

    def get_config(self, key, default=None):
        return self.settings.get(key, default)

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = handler


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    mod = _load_plugin()
    monkeypatch.setattr(mod, "_hermes_home", lambda: tmp_path / "hermes")
    ctx = _Ctx()
    mod.register(ctx)
    return mod, ctx.commands["stats"]


def test_stats_without_omp_returns_the_install_hint(plugin, monkeypatch):
    mod, handler = plugin
    monkeypatch.setattr(mod.dashboard, "find_omp", lambda configured=None: None)
    assert handler("", session_id="s1", platform="acp") == mod.dashboard.INSTALL_HINT


def test_stats_status_help_and_stop_without_a_server(plugin):
    _mod, handler = plugin
    assert "not running" in handler("status")
    assert "/stats stop" in handler("help")
    assert handler("stop") == "No trace dashboard was running."
    assert handler("bogus").startswith("Unknown /stats subcommand: bogus")


def test_browser_only_opens_on_desktop_surfaces(plugin, monkeypatch):
    mod, _handler = plugin
    opened = []
    monkeypatch.setattr(mod.webbrowser, "open", lambda url, new=0: opened.append(url) or True)
    monkeypatch.setenv("DISPLAY", ":0")
    assert mod._open_browser("http://x", "acp") is False
    assert mod._open_browser("http://x", "telegram") is False
    assert mod._open_browser("http://x", "cli") is True and opened == ["http://x"]


def test_stats_exports_this_session_first_then_reuses_the_watermark(plugin, state_db, tmp_path, monkeypatch):
    mod, handler = plugin
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "state.db").write_bytes(state_db.read_bytes())
    monkeypatch.setattr(mod.dashboard, "find_omp", lambda configured=None: "/bin/omp")
    monkeypatch.setattr(mod.dashboard, "ensure_server",
                        lambda root, omp, host, port: (mod.dashboard.ServerState(4242, port, host, str(root)), True))
    monkeypatch.setattr(mod.dashboard, "request_sync", lambda host, port: True)
    first = handler("", session_id="child", platform="acp")
    assert "#/traces?range=all&s=" in first and "child.jsonl" in first
    assert "exporting the other" in first
    mod._backlog.join()
    second = handler("", session_id="child", platform="acp")
    assert "0 written, 3 unchanged" in second and "pid 4242" in second
