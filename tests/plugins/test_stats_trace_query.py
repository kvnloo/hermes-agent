"""Tests for ``trace_query`` / ``trace_resolve`` in the stats-dashboard plugin.

The omp-stats API is replaced by an in-memory opener serving a synthetic trace with the shapes
``omp stats`` returns (``/api/session/trace``, ``/api/session/entry``, ``/api/stats/*``), so the tool,
the resolver, the render hook and the ``@trace`` reference provider run end to end without a server.
"""

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[2] / "plugins" / "stats-dashboard"

if "hermes_plugins" not in sys.modules:
    sys.modules["hermes_plugins"] = types.ModuleType("hermes_plugins")
    sys.modules["hermes_plugins"].__path__ = []


def _load(name):
    spec = importlib.util.spec_from_file_location(f"hermes_plugins.stats_dashboard.{name}", PLUGIN_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


tq = _load("trace_query")

T0 = 1_793_700_000_000
TEMPLATE = ('<!doctype html><html><head><style>.x{}</style></head><body><div id="cards"></div>'
            '<script id="eui-slice" type="application/json">__EUI_SLICE__</script><script>boot()</script></body></html>')


def _span(id_, kind, start, end, label, **extra):
    return {"id": id_, "kind": kind, "start": T0 + start, "end": T0 + end, "label": label, **extra}


def make_trace(file, n_tools=6, title="Fix the flaky build"):
    main = [
        _span("main:e0", "turn", 0, 400_000, "why is CI red?", entryId="e0"),
        _span("main:e1", "model", 0, 5_000, "claude-opus", entryId="e1", model="claude-opus", tokens=1200, cost=0.02),
    ]
    t = 5_000
    for i in range(n_tools):
        dur = 1_000 * (i + 1)
        main.append(_span(f"main:e1:call{i}", "tool", t, t + dur, "terminal" if i % 2 == 0 else "read_file",
                          entryId=f"e{10 + i}", detail='{"command":"pytest -x tests/</script>"}',
                          **({"isError": True, "errorKind": "exit 1"} if i == 3 else {})))
        t += dur
    main.append(_span("main:e30", "model", t + 120_000, t + 150_000, "claude-opus", entryId="e30",
                      model="claude-opus", tokens=9000, cost=0.3))
    main.append(_span("main:e31", "subagent", t + 150_000, t + 200_000, "scout", childTrackId="sub1"))
    sub = [_span("sub1:e1", "model", t + 150_000, t + 170_000, "gpt-x", entryId="e1", model="gpt-x", tokens=500,
                 cost=0.01),
           _span("sub1:e1:c", "tool", t + 170_000, t + 199_000, "search_files", entryId="e2")]
    tracks = [{"id": "main", "parentId": None, "label": "Main", "agent": "main", "model": "claude-opus",
               "file": file, "spans": main, "markers": []},
              {"id": "sub1", "parentId": "main", "label": "subagent scout", "agent": "subagent", "model": "gpt-x",
               "file": file.replace(".jsonl", "/sub.jsonl"), "spans": sub, "markers": []}]
    tools = [s for tr in tracks for s in tr["spans"] if s["kind"] == "tool"]
    return {"file": file, "title": title, "cwd": "/private/path", "startedAt": T0, "endedAt": T0 + 400_000,
            "mtimeMs": 1, "etag": "x", "tracks": tracks,
            "summary": {"wallMs": 400_000, "modelMs": 55_000, "toolMs": sum(s["end"] - s["start"] for s in tools),
                        "idleMs": 200_000, "turns": 1, "requests": 3, "toolCalls": len(tools), "subagents": 1,
                        "totalTokens": 10_700, "costTotal": 0.33, "unpricedRequests": 0, "toolStats": []}}


class FakeServer:
    """In-memory omp-stats: answers the paths trace_query calls and records them."""

    def __init__(self, traces):
        self.traces = {t["file"]: t for t in traces}
        self.calls = []

    def __call__(self, url, timeout):
        u = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        self.calls.append(u.path + ("?" + u.query if u.query else ""))
        if u.path == "/api/session/trace":
            trace = self.traces.get(q["file"])
            if trace is None:
                raise tq.urllib.error.HTTPError(url, 404, "nope", None, None)
            return json.dumps(trace).encode()
        if u.path == "/api/session/entry":
            return json.dumps({"entry": {"type": "message", "id": q["id"], "message": {
                "role": "assistant", "model": "claude-opus", "provider": "anthropic", "stopReason": "toolUse",
                "usage": {"input": 10, "output": 5, "totalTokens": 15},
                "content": [{"type": "text", "text": "Running the tests " + "x" * 3000},
                            {"type": "toolCall", "name": "terminal", "arguments": {"command": "pytest -x"}}]}}}).encode()
        if u.path == "/api/stats/tools":
            return json.dumps({"byTool": [{"tool": "terminal", "calls": 40, "errors": 4, "costShare": 1.5},
                                          {"tool": "read_file", "calls": 90, "errors": 1, "costShare": 0.5}],
                               "byToolModel": [{"tool": "terminal", "model": "m"}] * 50, "series": []}).encode()
        if u.path == "/api/stats":
            return json.dumps({"overall": {"totalRequests": 9, "totalCost": 1.25, "cacheRate": 0.9},
                               "byModel": [{"model": "claude-opus", "provider": "anthropic", "totalRequests": 9,
                                            "totalCost": 1.25}],
                               "byAgentType": [], "byFolder": [{"folder": "/private"}], "timeSeries": [],
                               "costSeries": [], "modelSeries": [], "modelPerformanceSeries": []}).encode()
        if u.path in ("/api/stats/providers", "/api/stats/frustration"):
            return b"{}"
        if u.path == "/api/stats/errors":
            return b"[]"
        raise AssertionError(f"unexpected path {url}")


@pytest.fixture
def world(tmp_path):
    sessions = tmp_path / "omp-stats" / "agent" / "sessions"
    rel = {"s-old": "--proj--/2026-11-01T10-00-00-000Z_s-old.jsonl",
           "s-new": "--proj--/2026-11-02T10-00-00-000Z_s-new.jsonl",
           "s-empty": "--proj--/2026-11-03T09-00-00-000Z_s-empty.jsonl",
           "s-cur": "--proj--/2026-11-03T10-00-00-000Z_s-cur.jsonl",
           "s-child": "--proj--/2026-11-02T10-00-00-000Z_s-new/2026-11-02T10-01-00-000Z_s-child.jsonl"}
    state = sessions.parent / "hermes-export-state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"version": 1, "sessions": {k: {"fp": "x", "path": v} for k, v in rel.items()}}))
    files = {k: str(sessions / v) for k, v in rel.items()}
    empty = make_trace(files["s-empty"], n_tools=0)
    empty["summary"]["turns"] = 0
    for track in empty["tracks"]:
        track["spans"] = []
    server = FakeServer([make_trace(files["s-old"], title="Older"), make_trace(files["s-new"], n_tools=8),
                         empty, make_trace(files["s-cur"], title="Current")])
    index = tq.SessionIndex.load(sessions, state)
    template = tmp_path / "stats-inline.html"
    template.write_text(TEMPLATE)
    return types.SimpleNamespace(api=tq.StatsApi("127.0.0.1", 1, opener=server), server=server, index=index,
                                 files=files, renders=tmp_path / "renders", template=template)


# ---------------------------------------------------------------- planning


@pytest.mark.parametrize("question,intent", [
    ("why was this session so slow?", "explain_slowness"),
    ("what was going on in this window, and why did it take so long?", "explain_slowness"),
    ("is the gap the same kind of wait as the subagent polling window?", "explain_slowness"),
    ("which tools failed most this week?", "tool_failures"),
    ("compare my last two sessions", "compare_sessions"),
    ("what did the subagents cost?", "subagent_cost"),
    ("where did the money go?", "cost_breakdown"),
    ("hello", "session_overview"),
])
def test_questions_map_to_the_kits_intents(question, intent):
    assert tq.classify(question)[0] == intent


def test_query_args_accept_a_trace_query_plan_and_a_ref():
    q = tq.Query.from_args({"plan": {"v": 0, "q": "compare", "intent": "compare_sessions",
                                     "scope": {"session": "latest", "range": "30d", "count": 2},
                                     "layers": ["cost", "bogus"]}})
    assert (q.intent, q.session, q.range, q.layers) == ("compare_sessions", "last 2", "30d", ["cost"])
    q = tq.Query.from_args({"question": "why slow", "ref": "@trace:v0;s=s-new;k=span;ids=main:e30;r=5-9;l=tokens"})
    assert (q.session, q.focus, q.focus_range, q.layers) == ("s-new", ["main:e30"], [5, 9], ["tokens"])
    with pytest.raises(tq.TraceQueryError):
        tq.Query.from_args({"intent": "nope"})


def test_latest_skips_the_current_session_and_subagent_files(world):
    picked = tq.pick_sessions(world.index, "latest", "s-cur", extra=5)
    assert [p.stem.rsplit("_", 1)[1] for p in picked] == ["s-empty", "s-new", "s-old"]
    assert tq.pick_sessions(world.index, "current", "s-cur") == [Path(world.files["s-cur"])]
    with pytest.raises(tq.TraceQueryError):
        tq.pick_sessions(world.index, "nope", "s-cur")
    with pytest.raises(tq.TraceQueryError):
        tq.pick_sessions(world.index, "/etc/passwd.jsonl", "s-cur")


# ---------------------------------------------------------------- analysis


def test_analysis_names_ids_tools_failures_and_idle(world):
    trace = make_trace(world.files["s-new"], n_tools=8)
    a = tq.analyze_trace(trace, "s-new", "explain_slowness")
    assert a["summary"]["requests"] == 3 and a["share"]["idleMs"] == 0.5
    terminal = next(r for r in a["tools"] if r["tool"] == "terminal")
    assert terminal["calls"] == 4 and terminal["errors"] == 0 and terminal["p95Ms"] >= terminal["p50Ms"]
    assert a["failures"]["count"] == 1 and a["failures"]["spans"][0]["id"] == "main:e1:call3"
    assert a["longest"][0]["id"] == "main:e31"  # the 50 s subagent span
    assert a["idle"][0]["ms"] == 120_000 and a["idle"][0]["before"] == "main:e30"
    assert {t["id"] for t in a["tracks"]} == {"main", "sub1"}


def test_analysis_stays_bounded_on_a_huge_trace(world):
    trace = make_trace(world.files["s-new"], n_tools=6000)
    for track in trace["tracks"]:
        for span in track["spans"]:
            if span["kind"] == "tool":
                span["label"] = f"tool_{span['id'][-4:]}"
                span["isError"] = True
    payload = tq.fit({"analysis": tq.analyze_trace(trace, "s-new", "errors", top=20)})
    assert len(json.dumps(payload, separators=(",", ":"))) <= tq.ANALYSIS_BUDGET
    assert payload["truncation"] and payload["analysis"]["failures"]["count"] == 6001  # + the subagent tool span


def test_trimmed_board_trace_keeps_failures_and_fits(world):
    trace = make_trace(world.files["s-new"], n_tools=3000)
    trimmed, notes = tq.trim_trace(trace, 60_000)
    assert len(json.dumps(trimmed, separators=(",", ":"))) <= 60_000
    kept = {s["id"] for tr in trimmed["tracks"] for s in tr["spans"]}
    assert "main:e1:call3" in kept and "main:e30" in kept and "cwd" not in trimmed
    assert any("left out" in n for n in notes)
    assert len(json.dumps(trace)) > 60_000  # the original is untouched


# ---------------------------------------------------------------- references


def test_refs_round_trip_and_reject_unsafe_values():
    ref = tq.make_ref("s-new", "selection", ["main:e30", "tool:terminal", ""], (10, 20), ["cost", "x"])
    assert ref == "@trace:v0;s=s-new;k=selection;ids=main:e30,tool:terminal;r=10-20;l=cost"
    parsed = tq.parse_ref(f"look at this {ref} please")
    assert parsed == {"s": "s-new", "k": "selection", "ids": ["main:e30", "tool:terminal"], "r": [10, 20],
                      "l": ["cost"]}
    assert tq.parse_ref('trace-ref:v0 {"session": "s-new", "ids": ["main:e1"], "range": [3, 1]}')["r"] is None
    assert tq.parse_ref("@trace:v0;s=s;ids=ok,../../x,<b> y")["ids"] == ["ok"]
    for bad in ("@trace:v1;s=x", "@trace:v0;k=span", "@trace:v0;s=<script>"):
        with pytest.raises(tq.TraceQueryError):
            tq.parse_ref(bad)


def test_resolve_expands_spans_tools_and_a_window(world):
    ref = tq.parse_ref(f"@trace:v0;s=s-new;k=selection;ids=main:e30,tool:terminal,main:nope;"
                       f"r={T0 + 5_000}-{T0 + 20_000}")
    out = tq.resolve(world.api, world.index, ref)
    span, tool, missing = out["items"]
    assert span["id"] == "main:e30" and span["entry"]["toolCalls"][0]["name"] == "terminal"
    assert len(span["entry"]["text"]) <= 1_200
    assert tool["tool"]["calls"] == 4 and tool["spans"]
    assert missing == {"id": "main:nope", "missing": True}
    assert out["range"]["tools"][0]["tool"] in ("terminal", "read_file") and out["range"]["spans"] >= 4
    assert len(json.dumps(out)) <= tq.ANALYSIS_BUDGET + 2_000
    assert "@trace selection" in tq.describe(out) or "trace selection" in tq.describe(out)


# ---------------------------------------------------------------- the tool end to end


def test_run_query_returns_bounded_analysis_and_a_render_handle(world):
    q = tq.Query.from_args({"question": "why was my latest session slow?", "session": "latest"})
    res = tq.run_query(q, world.api, world.index, "s-cur", world.renders, world.template)
    assert res["intent"] == "explain_slowness" and res["analysis"]["session"]["id"] == "s-new"
    assert any("no turns" in n for n in res["truncation"])  # s-empty was skipped
    assert len(json.dumps({k: v for k, v in res.items() if k != "render"}, separators=(",", ":"))) <= tq.ANALYSIS_BUDGET + 600
    render = res["render"]
    assert render["handle"].startswith("trace-render:") and render["cards"] == ["trace-summary", "trace", "trace-tools"]
    html = Path(render["path"]).read_text()
    assert "__EUI_SLICE__" not in html and "tests/</script>" not in html and "tests/\\u003c/script>" in html
    payload = json.loads(html.split('type="application/json">', 1)[1].split("</script>", 1)[0])
    assert 'tests/</script>' in json.dumps(payload)  # escaped on the wire, intact once parsed
    assert payload["inputs"]["trace0"] == world.files["s-new"] and payload["session"] == "s-new"
    assert world.files["s-new"] in payload["slice"]["traces"] and payload["slice"]["entries"]
    assert "/api/stats/errors?range=30d" in payload["slice"]["api"]
    assert tq.read_render(world.renders, render["handle"]) == html


def test_range_intents_trim_payloads_and_compare_orders_older_first(world):
    q = tq.Query.from_args({"question": "which tools failed most this week?", "session": "s-new"})
    res = tq.run_query(q, world.api, world.index, "s-cur", world.renders, world.template)
    assert res["rangeAnalysis"]["tools"]["errors"] == 5 and res["range"] == "7d"
    html = Path(res["render"]["path"]).read_text()
    assert '"byToolModel":[]' in html
    q = tq.Query.from_args({"question": "compare my last two sessions"})
    res = tq.run_query(q, world.api, world.index, "s-cur", world.renders, world.template)
    assert res["analysis"]["session"]["id"] == "s-new" and res["older"]["session"]["id"] == "s-old"
    assert res["render"]["cards"] == ["trace-compare", "trace-summary", "trace-summary"]
    q = tq.Query.from_args({"question": "where did the money go this month?"})
    res = tq.run_query(q, world.api, world.index, "s-cur", world.renders, world.template)
    assert "analysis" not in res and res["rangeAnalysis"]["usage"]["overall"]["totalCost"] == 1.25
    assert "byFolder" not in Path(res["render"]["path"]).read_text()


def test_focus_ids_come_back_resolved_with_the_board(world):
    q = tq.Query.from_args({"question": "what happened here?", "session": "s-new", "focus": ["main:e1:call3"]})
    res = tq.run_query(q, world.api, world.index, "s-cur", world.renders, world.template)
    assert res["focus"]["items"][0]["error"] == "exit 1"
    assert '"focus":{"ids":["main:e1:call3"]' in Path(res["render"]["path"]).read_text()


def test_board_passes_the_hosts_viewport_height_scan():
    payload = {"slice": {"detail": '<div style="height:50vh">', "x": "</script><!-- STYLE=12vh"}}
    html = tq.fill_template(TEMPLATE, payload)
    assert tq.viewport_height_unit(html) is None
    assert json.loads(html.split('type="application/json">', 1)[1].split("</script>", 1)[0]) == payload
    assert tq.viewport_height_unit('<p style="min-height:12vh">') == "12vh"
    assert tq.viewport_height_unit("<style>.a{height:3.5dvh}</style>") == "3.5dvh"
    assert tq.viewport_height_unit("<style>.a{background:url(data:x/1vh)}</style>") is None


def test_missing_template_or_oversized_board_is_reported_not_raised(world, tmp_path):
    q = tq.Query.from_args({"question": "why slow", "session": "s-new"})
    res = tq.run_query(q, world.api, world.index, "s-cur", world.renders, tmp_path / "missing.html")
    assert "stats-inline.mjs --template" in res["render"]["error"] and res["analysis"]
    big = tmp_path / "big.html"
    big.write_text(TEMPLATE.replace(".x{}", "." + "x" * 600_000))
    res = tq.run_query(q, world.api, world.index, "s-cur", world.renders, big)
    assert "html_render limit" in res["render"]["error"]
    vh = tmp_path / "vh.html"
    vh.write_text(TEMPLATE.replace(".x{}", ".x{height:100vh}"))
    assert "viewport height unit (100vh)" in tq.run_query(q, world.api, world.index, "s-cur", world.renders,
                                                           vh)["render"]["error"]


# ---------------------------------------------------------------- plugin wiring


class _Ctx:
    def __init__(self):
        self.tools, self.hooks, self.references, self.skills, self.commands = {}, {}, [], {}, {}

    def get_config(self, key, default=None):
        return default

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = handler

    def register_tool(self, name, toolset, schema, handler, **kwargs):
        self.tools[name] = (schema, handler)

    def register_hook(self, name, callback, **kwargs):
        self.hooks[name] = callback

    def register_context_reference(self, provider):
        self.references.append(provider)

    def register_skill(self, name, path, description=""):
        self.skills[name] = Path(path)


@pytest.fixture
def plugin(tmp_path, monkeypatch, world):
    spec = importlib.util.spec_from_file_location(
        "hermes_plugins.stats_dashboard", PLUGIN_DIR / "__init__.py", submodule_search_locations=[str(PLUGIN_DIR)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    home = tmp_path / "hermes"
    monkeypatch.setattr(mod, "_hermes_home", lambda: home)
    monkeypatch.setattr(mod, "_prepare", lambda settings, session_id, need_history: (world.api, world.index))
    (home / "omp-stats").mkdir(parents=True)
    (home / "omp-stats" / "stats-inline.html").write_text(TEMPLATE)
    ctx = _Ctx()
    mod.register(ctx)
    return mod, ctx, home


def test_register_wires_tools_hook_skill_and_references(plugin):
    _mod, ctx, _home = plugin
    assert set(ctx.tools) == {"trace_query", "trace_resolve"} and "pre_tool_call" in ctx.hooks
    assert ctx.tools["trace_query"][0]["parameters"]["properties"]["intent"]["enum"][-1] == "session_overview"
    assert ctx.skills["trace-query"].read_text().startswith("---\nname: trace-query")
    if ctx.references:  # core with plugin context references
        assert ctx.references[0].prefix == "trace"


def test_tool_handlers_return_json_and_errors(plugin):
    _mod, ctx, home = plugin
    out = json.loads(ctx.tools["trace_query"][1]({"question": "why slow?", "session": "s-new"}, session_id="s-cur"))
    assert out["render"]["handle"].startswith("trace-render:")
    assert (home / "omp-stats" / "renders").is_dir()
    assert "error" in json.loads(ctx.tools["trace_query"][1]({"session": "nope"}, session_id="s-cur"))
    got = json.loads(ctx.tools["trace_resolve"][1]({"ref": "@trace:v0;s=s-new;k=span;ids=main:e30"}))
    assert got["items"][0]["entry"]["model"] == "claude-opus"
    got = json.loads(ctx.tools["trace_resolve"][1]({"session": "s-new", "ids": ["tool:read_file"]}))
    assert got["items"][0]["tool"]["calls"] == 4
    assert "error" in json.loads(ctx.tools["trace_resolve"][1]({"ref": "nonsense"}))


def test_render_hook_swaps_only_its_own_handles_into_html_tools(plugin):
    _mod, ctx, _home = plugin
    hook = ctx.hooks["pre_tool_call"]
    handle = json.loads(ctx.tools["trace_query"][1]({"session": "s-new"}, session_id="s-cur"))["render"]["handle"]
    got = hook(tool_name="mcp__editor_t3_code_1f7cde1a__html_render", args={"html": handle, "title": "t", "height": 900})
    assert got["action"] == "modify" and got["args"]["html"].startswith("<!doctype html>")
    assert hook(tool_name="mcp_editor_t3_code_x_html_preview", args={"html": f"  {handle}\n"})["action"] == "modify"
    assert hook(tool_name="write_file", args={"html": handle}) is None
    assert hook(tool_name="mcp__x__html_render", args={"html": "<p>hi</p>"}) is None
    assert hook(tool_name="mcp__x__html_render", args={"html": "trace-render:0000000000000000"})["action"] == "block"
    assert hook(tool_name="mcp__x__html_render", args={"html": "trace-render:../../etc/passwd"})["action"] == "block"
    assert hook(tool_name="mcp__x__html_render", args=None) is None
    assert hook(tool_name="mcp__x__html_render", args={"html": 42}) is None


def test_trace_reference_expands_in_the_prompt(plugin):
    _mod, ctx, _home = plugin
    if not ctx.references:
        pytest.skip("core without plugin context references")
    provider = ctx.references[0]
    text = asyncio.run(provider.expand("v0;s=s-new;k=span;ids=main:e1:call3"))
    assert "main:e1:call3" in text and "exit 1" in text
    assert "not expanded" in asyncio.run(provider.expand("v0;k=span"))
