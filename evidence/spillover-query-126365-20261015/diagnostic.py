#!/usr/bin/env python3
"""Standalone stdlib semantics diagnostic. Never imports or runs Hermes code.

Reads pinned repository snapshots as data; parses their AST to extract literals.
Only database is sqlite3.connect(":memory:"). No archive creation/deletion,
repository mutation, external calls, native Windows or full-Hermes execution.
"""
import ast
import hashlib
import json
import pathlib
import platform
import re
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PIN = "77dcd5879a51815e3c05382fb38f65ea583f0245"
REPO = "NousResearch/hermes-agent"
FILES = {
    "storage": "tools/tool_result_storage.py",
    "messages": "hermes_state_messages.py",
    "maintenance": "hermes_state_maintenance.py",
    "state": "hermes_state.py",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


sources = {}
trees = {}
provenance = {}
for key, path in FILES.items():
    response = json.loads((ROOT / (key + "_response.json")).read_text())
    data = (ROOT / path).read_bytes()
    assert data == response["content"].encode("utf-8")
    git_sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert git_sha == response["sha"], (path, git_sha, response["sha"])
    sources[key] = data.decode("utf-8")
    trees[key] = ast.parse(sources[key], filename=path)
    provenance[key] = {
        "path": path, "url": response["display_url"], "bytes": len(data),
        "git_blob_sha1": git_sha, "sha256": digest(data),
    }

pr = json.loads((ROOT / "pr_snapshot.json").read_text())["pull_request"]
assert pr["head_sha"] == PIN
comments = json.loads((ROOT / "comments_snapshot.json").read_text())["comments"]


def function(key, name):
    return next(n for n in ast.walk(trees[key])
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


def assigned_literal(key, name):
    n = next(n for n in ast.walk(trees[key]) if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    value_node = n.value.args[0] if isinstance(n.value, ast.Call) else n.value
    value = ast.literal_eval(value_node)
    return value, {"path": FILES[key], "line_start": n.lineno, "line_end": n.end_lineno,
                   "source": ast.get_source_segment(sources[key], n),
                   "literal_source": ast.get_source_segment(sources[key], value_node),
                   "value": value, "value_utf8_sha256": digest(value.encode("utf-8"))}


pattern, regex_provenance = assigned_literal("storage", "_SPILLOVER_NAME_RE")
content_prefix, prefix_provenance = assigned_literal("state", "_CONTENT_JSON_PREFIX")
storage_fn = function("storage", "referenced_spillover_names")
query_node = next(n for n in ast.walk(storage_fn)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)
                  and n.value.startswith("SELECT content, api_content FROM messages "))
query = ast.literal_eval(query_node)
maintenance_fn = function("maintenance", "_spillover_refs")
maintenance_condition_node = next(
    n for n in ast.walk(maintenance_fn) if isinstance(n, ast.Constant)
    and isinstance(n.value, str) and " AND (content LIKE " in n.value
)
maintenance_condition = maintenance_condition_node.value
# The AST merges a trailing f-string segment ")" with the adjacent plain literal.
# Preserve the exact predicate characters after that closing session-IN delimiter.
maintenance_condition = maintenance_condition[maintenance_condition.index(" AND ("):]
maintenance_query = (
    "SELECT content, api_content FROM messages WHERE session_id IN (?)"
    + maintenance_condition
)
helper_fn = function("storage", "spillover_names_in_text")
gate_node = next(n for n in ast.walk(helper_fn) if isinstance(n, ast.Constant)
                 and n.value == "spillover/")
gate = ast.literal_eval(gate_node)
literals = {
    "regex": regex_provenance,
    "substring_gate": {
        "path": FILES["storage"], "line": gate_node.lineno,
        "literal_source": ast.get_source_segment(sources["storage"], gate_node),
        "value": gate,
    },
    "reference_query": {
        "path": FILES["storage"], "line_start": query_node.lineno,
        "line_end": query_node.end_lineno,
        "source": ast.get_source_segment(sources["storage"], query_node),
        "value": query, "value_utf8_sha256": digest(query.encode()),
    },
    "capture_condition": {
        "path": FILES["maintenance"], "line_start": maintenance_condition_node.lineno,
        "line_end": maintenance_condition_node.end_lineno,
        "exact_predicate": maintenance_condition,
        "predicate_utf8_sha256": digest(maintenance_condition.encode()),
        "diagnostic_select": maintenance_query,
        "note": "Diagnostic replaces only session-ID placeholder construction with one bound parameter.",
    },
    "content_json_prefix": prefix_provenance,
}
regex = re.compile(pattern)


def notice(path):
    # Synthetic minimal notice. The source builder inserts file_path unchanged at
    # tools/tool_result_storage.py:358; no builder/module is executed here.
    return "<persisted-output>\nFull output saved to: " + path + "\n</persisted-output>"


def names_from_literal_semantics(*texts):
    # Independent stdlib operations using extracted string/regex data, not Hermes.
    return sorted({name for text in texts if isinstance(text, str) and gate in text
                   for name in regex.findall(text)})


families = [
    ("posix_forward", "/synthetic/home/cache/spillover/{name}", "forward"),
    ("windows_forward", "C:/synthetic/home/cache/spillover/{name}", "forward"),
    ("windows_backslash", "C:\\synthetic\\home\\cache\\spillover\\{name}", "backslash"),
    ("windows_unc_backslash", "\\\\server\\synthetic\\cache\\spillover\\{name}", "backslash"),
    ("negative_other_directory", "/synthetic/home/cache/not_spill/{name}", "negative"),
    ("negative_no_path", "No archived output is referenced.", "negative"),
]
fixtures = []
for family, path_template, group in families:
    for encoding in ("raw", "json_string"):
        for column in ("content", "api_content"):
            case_id = family + "__" + encoding + "__" + column
            basename = case_id + ".txt"
            raw = notice(path_template.format(name=basename))
            stored = raw if encoding == "raw" else json.dumps(raw)
            row = {
                "case_id": case_id, "group": group, "encoding": encoding,
                "target_column": column,
                "target_basename": basename if group != "negative" else None,
                "content": stored if column == "content" else None,
                "api_content": stored if column == "api_content" else None,
            }
            fixtures.append(row)

# Canonical structured-content representation shown by _encode_content at
# hermes_state_messages.py:155: NUL-prefixed JSON. Only content has this encoder.
for family, path_template, group in families[:4]:
    case_id = family + "__sentinel_json_parts__content"
    basename = case_id + ".txt"
    stored = content_prefix + json.dumps([
        {"type": "text", "text": notice(path_template.format(name=basename))}
    ])
    fixtures.append({
        "case_id": case_id, "group": "structured_" + group,
        "encoding": "sentinel_json_parts", "target_column": "content",
        "target_basename": basename, "content": stored, "api_content": None,
    })

# OR-gate positive controls: a forward-slash reference in the other column
# admits the row but still does not make the backslash basename extractable.
for column in ("content", "api_content"):
    case_id = "mixed_columns__backslash_in__" + column
    back_name = case_id + "__back.txt"
    forward_name = case_id + "__forward.txt"
    back = notice("C:\\synthetic\\cache\\spillover\\" + back_name)
    forward = notice("/synthetic/cache/spillover/" + forward_name)
    fixtures.append({
        "case_id": case_id, "group": "mixed", "encoding": "raw",
        "target_column": column, "target_basename": back_name,
        "forward_control_basename": forward_name,
        "content": back if column == "content" else forward,
        "api_content": back if column == "api_content" else forward,
    })

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE messages (session_id TEXT, content TEXT, api_content TEXT)")
results = []
for f in fixtures:
    conn.execute("INSERT INTO messages VALUES (?, ?, ?)",
                 (f["case_id"], f["content"], f["api_content"]))
    selected = conn.execute(maintenance_query, (f["case_id"],)).fetchall()
    direct_names = names_from_literal_semantics(f["content"], f["api_content"])
    sql_names = sorted({name for row in selected for name in names_from_literal_semantics(*row)})
    results.append({
        **f, "capture_selected_rows": len(selected), "direct_regex_names": direct_names,
        "capture_extracted_names": sql_names,
        "target_found_direct": f["target_basename"] in direct_names if f["target_basename"] else False,
        "target_found_after_sql": f["target_basename"] in sql_names if f["target_basename"] else False,
    })
reference_rows = conn.execute(query).fetchall()
reference_names = sorted({name for row in reference_rows for name in names_from_literal_semantics(*row)})
# Count per-row reference selection using the exact original query on a fresh
# in-memory table containing only that fixture. No SQL predicate is rewritten.
single = sqlite3.connect(":memory:")
single.execute("CREATE TABLE messages (content TEXT, api_content TEXT)")
for result in results:
    single.execute("DELETE FROM messages")  # In-memory synthetic rows only.
    single.execute("INSERT INTO messages VALUES (?, ?)",
                   (result["content"], result["api_content"]))
    result["reference_selected_rows"] = len(single.execute(query).fetchall())
    assert result["reference_selected_rows"] == result["capture_selected_rows"]
single.close()
conn.close()

groups = {}
for group in sorted({r["group"] for r in results}):
    rows = [r for r in results if r["group"] == group]
    groups[group] = {
        "cases": len(rows),
        "reference_sql_selected_rows": sum(r["reference_selected_rows"] for r in rows),
        "capture_sql_selected_rows": sum(r["capture_selected_rows"] for r in rows),
        "rows_with_direct_regex_names": sum(bool(r["direct_regex_names"]) for r in rows),
        "target_found_after_sql": sum(r["target_found_after_sql"] for r in rows),
    }
assert groups["forward"]["target_found_after_sql"] == 8
assert groups["backslash"]["reference_sql_selected_rows"] == 0
assert groups["backslash"]["rows_with_direct_regex_names"] == 0
assert groups["negative"]["reference_sql_selected_rows"] == 0
assert groups["structured_forward"]["reference_sql_selected_rows"] == 0
assert groups["structured_forward"]["rows_with_direct_regex_names"] == 2
assert groups["structured_backslash"]["reference_sql_selected_rows"] == 0
assert groups["mixed"]["reference_sql_selected_rows"] == 2
assert groups["mixed"]["target_found_after_sql"] == 0
assert len(results) == 30 and len(reference_rows) == 10 and len(reference_names) == 10

output = {
    "scope": "Standalone Python/sqlite3/re literal-semantics diagnostic, not a Hermes/native-Windows test or implementation claim.",
    "pin": PIN, "pr_url": pr["url"],
    "platform": platform.platform(), "python": sys.version,
    "sqlite": sqlite3.sqlite_version,
    "source_provenance": provenance, "literals": literals,
    "comments_refreshed_count": len(comments),
    "latest_comment": {
        k: comments[-1].get(k) for k in ("url", "created_at", "updated_at")
    },
    "summary": {
        "cases": len(results), "reference_query_selected_rows": len(reference_rows),
        "reference_query_extracted_unique_names": len(reference_names),
        "groups": groups,
    },
    "reference_query_names": reference_names, "results": results,
}
(ROOT / "diagnostic_results.json").write_text(json.dumps(output, indent=2) + "\n")
(ROOT / "literal_provenance.json").write_text(json.dumps({
    "pin": PIN, "files": provenance, "literals": literals,
}, indent=2) + "\n")
print("SCOPE:", output["scope"])
print("HEAD:", PIN)
print("PLATFORM:", platform.platform())
print("PYTHON:", platform.python_version(), "SQLITE:", sqlite3.sqlite_version)
print("CASES:", len(results), "REFERENCE_SELECTED:", len(reference_rows),
      "REFERENCE_UNIQUE_NAMES:", len(reference_names))
for group, counts in groups.items():
    print("GROUP", group, json.dumps(counts, sort_keys=True))
for row in results:
    print("CASE", row["case_id"], "reference_sql=" + str(row["reference_selected_rows"]),
          "capture_sql=" + str(row["capture_selected_rows"]),
          "regex=" + json.dumps(row["direct_regex_names"]),
          "target_after_sql=" + str(row["target_found_after_sql"]))
print("ASSERTIONS: PASS")

