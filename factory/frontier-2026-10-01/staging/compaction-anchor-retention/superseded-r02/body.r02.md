This PR touches the same table as something I was about to propose, so I'd rather offer it here than open a second PR that conflicts with yours.

The 2026-09-19 Jev scorecard (`evals/compaction/results/SCORECARD-2026-09-19-jev.md`) says the summary's misses were "delegation ids, root causes, config keys, exact error strings" in assistant text, and calls that "a summariser-retention target (anchor index / identifier capture)". Three of those classes have no row in `_ANCHOR_PATTERNS`, either here or on main:

| row | captures | stays out |
|---|---|---|
| `task ids` | `sa-2-7318d0ba` (delegate_tool), `t_4f9c2a1e` (kanban) | hex fragments inside longer words |
| `dotted keys` | `plugins.stream_reasoning_deltas`, `compression.tail_mode` | `config.yaml`, `api.openai.com`, `e.g` (the last segment must be snake_case) |
| `error messages` | `GraphQL: … (mergePullRequest)`, ``Blocked: `git checkout` …``, `fatal: …`, `error: …`, `error TS2741: …` | annotations like `error: Exception)` and `"error: %s"` log formats (`fatal:`/`error:` only count where a line starts, after a quote or backtick, or after an escaped `\n` in JSON tool output) |

If you want them, the patch below adds the three rows in this PR's cheap-first order (`task ids` after `todo ids`, `dotted keys` before `files`, `error messages` last) plus one test file. It applies to `2c19948e15` with `git apply`. With it applied on top of current main, both test files pass (your 5 and these 2), and so do the six neighbouring compressor test files (372 passed across the 8 files). Your per-section truncation matters here too: on main, rows appended at the end only get the budget the earlier sections leave over.

What I checked, and what I didn't:
- I chose the rows from the 08-15 scorecard's committed gold answers. 24 of its 49 identifier golds match a current row, and 31 match with these rows. I wrote the rows after reading those golds, so that is an in-sample count. The 5 error-line golds behind it are only 2 distinct strings: the `Blocked:` git-guard refusal and one gh merge-conflict error.
- The 09-19 scorecard asks for a coverage check on its prreview/sysprompt/sigsegv banks. Those banks aren't committed, so I couldn't run it.
- I haven't run the recall exam; it needs the aux model.
- On Python source, `dotted keys` mostly picks up attribute access (`self.base_url`, `agent.session_id`). In a region full of `read_file` output it can crowd out real config keys.

<details><summary>Patch (rows + tests/agent/test_context_compressor_anchor_index.py)</summary>

```diff
diff --git a/agent/context_compressor.py b/agent/context_compressor.py
index 9ad6509eb8..c74862db51 100644
--- a/agent/context_compressor.py
+++ b/agent/context_compressor.py
@@ -955,16 +955,23 @@ _ANCHOR_PATTERNS: "list[tuple[str, re.Pattern[str], int]]" = [
     ("PRs/issues", re.compile(r"#\d{3,6}\b"), 120),
     ("session ids", re.compile(r"\b\d{8}_\d{6}_[0-9a-f]{8}\b"), 40),
     ("todo ids", re.compile(r"\[\d{6}\]"), 40),
+    ("task ids", re.compile(r"\b(?:sa-\d+-[0-9a-f]{8}|t_[0-9a-f]{8})\b"), 40),  # delegate_tool / kanban_db ids
     ("commits", re.compile(r"\b[0-9a-f]{9,40}\b"), 40),
     ("branches", re.compile(r"\b(?:fix|feat|docs|refactor|chore|salvage|ent)/[A-Za-z0-9._/-]{3,60}"), 40),
     ("handles", re.compile(r"@[A-Za-z0-9-]{3,30}\b"), 40),
     ("urls", re.compile(r"https?://[^\s)\"']{10,110}"), 30),
+    ("dotted keys", re.compile(r"\b[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.[a-z][a-z0-9]*_[a-z0-9_]*[a-z0-9](?!\.?\w)"), 40),
     # Filename segment: path characters incl. CJK names, but never quoting/CJK list punctuation —
     # unpunctuated prose runs ("`a.py`：`b.py`、`c.py`") otherwise collapse into one unusable value;
     # the 120-char cap bounds any run that still slips through. Directory part stays \w so
     # non-ASCII directory names keep working.
     ("files", re.compile(r"\b[\w./-]+/[^\s/`'\"\u3001\uff0c\u3002\uff1a\uff1b\uff01\uff1f\uff08\uff09\u3010\u3011\{\}\[\]<>*|]{1,120}\.(?:py|ts|tsx|js|jsx|rs|go|java|rb|php|sql|md|rst|csv|tsv|xlsx|xls|ipynb|html|css|scss|vue|yaml|yml|json|jsonl|toml|ini|cfg|sh|db|sqlite|log)\b"), 80),
     ("errors", re.compile(r"\b(?:[A-Z][a-zA-Z]*Error|Exception|ENOSPC|EACCES|SIGKILL|Traceback)\b[^\n]{0,90}"), 40),
+    # CLI error lines (git fatal:/error:, tsc error TS####:, gh GraphQL:) and Hermes tool refusals (Blocked:).
+    # fatal:/error: only at a line start (or after a quote, backtick, JSON-escaped \n); not annotations or %s/{}.
+    ("error messages", re.compile(
+        r"(?:(?:^|(?<=[`\"])|(?<=\\n))(?:fatal|[Ee]rror)|\berror TS\d{4,5}|\bGraphQL|\bBlocked): "
+        r"(?![%{])(?:(?!\\n)[^\n]){8,110}", re.M), 20),
 ]
 _ANCHOR_NOISE = frozenset({
     "@teknium", "@teknium1",  # session owner, in every transcript
diff --git a/tests/agent/test_context_compressor_anchor_index.py b/tests/agent/test_context_compressor_anchor_index.py
new file mode 100644
index 0000000000..eadbec4ac6
--- /dev/null
+++ b/tests/agent/test_context_compressor_anchor_index.py
@@ -0,0 +1,89 @@
+"""Anchor index: identifier classes the compaction recall exam lost from assistant text.
+
+SCORECARD-2026-09-19-jev.md: the facts the summary dropped (delegation ids, config keys,
+exact error strings) sat in assistant text. ``_build_anchor_index`` keeps only what a row
+in ``_ANCHOR_PATTERNS`` matches, so each class needs a row that captures it verbatim,
+stays inside its cap and the shared budget, and does not soak up neighbouring classes.
+"""
+import json
+
+import agent.context_compressor as cc
+
+
+def _line(index: str, label: str) -> str:
+    return next((ln for ln in index.splitlines() if ln.startswith(f"{label}: ")), "")
+
+
+def _cap(label: str) -> int:
+    return next(cap for name, _pattern, cap in cc._ANCHOR_PATTERNS if name == label)
+
+
+def test_anchor_index_keeps_task_ids_config_keys_and_error_messages_verbatim():
+    turns = [
+        {"role": "user", "content": "Land the desktop batch and turn on reasoning deltas."},
+        {
+            "role": "assistant",
+            "content": (
+                "Delegated the inflight-journal cluster to sa-2-7318d0ba; kanban card t_4f9c2a1e tracks it.\n"
+                "Set plugins.stream_reasoning_deltas: true in config.yaml.\n"
+                "Merging #86589 failed:\n"
+                "GraphQL: Pull Request has merge conflicts (mergePullRequest)\n"
+                "The worktree checkout was refused:\n"
+                "Blocked: `git checkout` would rewrite Hermes's live source checkout\n"
+                "The pull stopped at `fatal: refusing to merge unrelated histories`\n"
+            ),
+        },
+        {
+            "role": "tool",
+            "content": json.dumps({
+                "output": "Updating 1a2b3c4..5d6e7f8\nerror: Your local changes to the following files would be overwritten by merge\n",
+                "exit_code": 1,
+            }),
+        },
+    ]
+
+    index = cc._build_anchor_index(turns)
+
+    for needle in (
+        "sa-2-7318d0ba",
+        "t_4f9c2a1e",
+        "plugins.stream_reasoning_deltas",
+        "GraphQL: Pull Request has merge conflicts (mergePullRequest)",
+        "Blocked: `git checkout` would rewrite Hermes's live source checkout",
+        "fatal: refusing to merge unrelated histories",
+        "error: Your local changes to the following files would be overwritten by merge",
+    ):
+        assert needle in index, f"{needle!r} missing from anchor index:\n{index}"
+    assert "exit_code" not in _line(index, "error messages")  # stops at the escaped newline
+
+
+def test_new_anchor_classes_stay_exact_and_bounded():
+    prose = (
+        "See agent/context_compressor.py and config.yaml (e.g. api.openai.com); "
+        "compression.tail_mode stays lean and the task_7 retry passed.\n"
+    )
+    ids = " ".join(f"sa-{i}-{i:08x}" for i in range(60))
+    errors = "\n".join(f"fatal: unable to reach remote mirror {i} over https" for i in range(60))
+    source = (  # code is not an error line: annotations and log format strings stay out
+        "    def _on_failure(self, error: Exception) -> Dict[str, Any]:\n"
+        '        logger.warning("error: %s", exc)\n'
+        "    error: Optional[Exception] = None\n"
+    ) * 2
+    turns = [
+        {"role": "assistant", "content": prose + ids + "\n" + errors},
+        {"role": "tool", "content": source},
+    ]
+
+    index = cc._build_anchor_index(turns)
+
+    dotted = _line(index, "dotted keys")
+    assert "compression.tail_mode" in dotted
+    for not_a_key in ("context_compressor.py", "config.yaml", "api.openai.com", "e.g", "task_7"):
+        assert not_a_key not in dotted, f"{not_a_key!r} leaked into dotted keys: {dotted!r}"
+    assert _line(index, "task ids").count("sa-") == _cap("task ids")
+    messages = _line(index, "error messages")
+    for not_an_error in ("Exception)", "%s", "Optional["):
+        assert not_an_error not in messages, f"{not_an_error!r} leaked into error messages: {messages!r}"
+    assert messages.count("fatal: ") == _cap("error messages")
+    sections = index.split("\n")[3:-1]  # between the heading and the trailing note
+    assert sum(len(s) for s in sections) <= cc._LEAN_ANCHOR_BUDGET_CHARS
```

</details>

If you'd rather keep this PR's scope as it is, no problem. I can open it separately after this lands, or drop it. If you do fold it in, a `Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>` trailer would be appreciated.

Written with AI assistance (Claude Code). I reviewed the patch and ran the tests above.
