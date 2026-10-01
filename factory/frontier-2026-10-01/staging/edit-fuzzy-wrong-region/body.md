# edit-fuzzy-wrong-region: posting texts (owner posts; nothing here has been posted)

Owner notes, not for posting: only the quoted blocks (lines starting with `>`) are posted, each as one comment. To post a block, remove the leading `> ` from each of its lines (a line that is only `>` becomes an empty line) and change nothing else. Each block is complete as it stands: there is nothing to paste in or fill in, and the §3 block already contains its diff. Everything outside the quoted blocks, including the section headings, these notes and the tone-gate list at the end, stays here. Each piece stands alone, and each is easy to decline. Every count and SHA in the blocks was measured on main `44a1ce97` (44a1ce9724), with the staged commit rebased onto it as `fdaaf5b729` (F01/r20261001-04; the battery in §4 was re-run there too). Main was 44a1ce9724 (by `git ls-remote`) when the commit was rebased at 16:37Z. By 16:56Z it had moved 4 commits to `aaa863f7` (aaa863f7ff), none of them on the edit path or the 13 neighbouring test files; the commit still merges cleanly there, and one RED run (8 of 10 cases fail) and one GREEN run (10 of 10 cases pass) gave the same results (F01/r20261001-04 `freshness_after_proof`). For that reason the blocks name the SHA and do not call it current main. Before posting, re-check (STAGING.md, Next steps 3); if you re-measure on a newer main, change `44a1ce97` in the blocks to that SHA. Every quoted block ends with a line saying the poster checked the results. Post a block only after you have checked them.

## 1. Wave row (delta comment on the salvage wave)

Owner note: the 2026-10-01 board, kvnloo/hermes-agent#402, is closed. Its 9 rows were posted upstream as NousResearch/hermes-agent#130139, and this row is not among them. You pick the venue: post the block below as a comment on NousResearch/hermes-agent#130139, or hold the row for the next wave. That issue's body has no AI disclosure, so the comment carries its own. It is not a row for the staged-PR queue kvnloo/hermes-agent#404, because there is no PR to promote.

> One more row for this wave. It uses the same method and columns as the rows above: each open fix is applied to main (`44a1ce97`) and run against one behaviour-contract regression test, and a fix that conflicts is marked as not run.
>
> | issue | carrier (author) | A/B | fold in (author: what) | close after carrier merges | evidence |
> |---|---|---|---|---|---|
> | #54572 (also #93698, and the single-line part of #111116) | #54575 (MaxFreedomPollard) for the block case, plus #125376's fix commit `5f3f5896` (Finn763) for the single-line case | main `44a1ce97`: FAIL, 8 of 10 cases fail (`block_anchor` and `context_aware` each replace text the edit never named, count=1, no error, in both replace and V4A mode); #54575: FAIL, 6 of 10 cases fail after a mechanical test-file rebase (its 2 block cases pass; the 6 single-line cases still land); #125376's fix commit alone: FAIL, 4 of 10 cases fail (the 2 block cases and the 2 trailing-newline cases still land); #126502: FAIL, 6 of 10 cases fail (block cases pass, single-line cases still land), and 2 existing escape-drift tests fail; #93717: CONFLICTING, not run; #54575 + `5f3f5896`: FAIL, 2 of 10 cases fail (both are the trailing-newline case); #54575 + `5f3f5896` + fold-in: PASS, 10 of 10 cases pass, in 3 of 3 runs | Enough1122 (review comment on #125376, 2026-09-29): one line in #125376's guard. It tests `len(pattern.strip().split('\n')) == 1` instead of `n == 1`, so an `old_string` with a trailing newline (or CRLF, or a leading blank line) can no longer reach the single-line similarity path. `Co-authored-by: Enough1122 <10966420+Enough1122@users.noreply.github.com>`. kvnloo: verified that line in this A/B and wrote the regression test `tests/tools/test_fuzzy_match_wrong_region.py`, run on the real `patch_replace` and V4A paths. Four wrong-region cases must return an error and leave the file byte-identical. Two near misses must still apply, and the matcher must name a non-exact strategy for them. The test's cases come from the #54572 repro (MaxFreedomPollard), #54575's live near-miss test (likivik), #125376's single-line fixture (Finn763), two traps from the #111127 battery (KoNit-K) and the review's trailing-newline case (Enough1122); the test commit carries a `Co-authored-by` trailer for each of them. `Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>` | #126502, #93717. Both fix the same block_anchor defect, and #54575 also refuses both PRs' Markdown repros. | Reverting any one of the three fix pieces alone makes the test fail again. #54575's floor covers the block cases; it also runs on the single-line matches but lets them through (`trim()` vs `strip()` is 0.923, above its 0.90 floor). #125376's guard covers all the single-line cases. The fold-in line covers only the trailing-newline cases, and both carriers' own tests still pass without it. The sibling tests (13 files: fuzzy_match, file_operations*, patch_parser, patch_*, file_tools*, acp edit_approval, the shared-metrics harness) give 284 passed and 8 skipped on main, on #54575, on #125376's fix, and on the combination. Behaviour change: the `hermes.file_edit.count` label sets do not change, but wrong-region edits move from `applied/context_aware` or `applied/block_anchor` to `no_match`, so the patch returns an error instead of editing. #125376 also carries an unrelated bot_relay commit, which conflicts with main. |
>
> (I used an AI assistant to run the A/B, draft the regression test and write this row, and I checked the results myself.)

## 2. Comment on #125376 (one comment)

> I ran this against main at `44a1ce97` together with #54575, using a regression test that drives the real `patch_replace` and V4A paths. Your guard closes the single-line case on both paths.
>
> The trailing-newline case from the earlier review is still open: `"    return value.trim()\n"` splits into two lines and still reaches the similarity fallback (applied via `context_aware`). The fix that review proposed, checking the stripped pattern, closes it, and the CRLF and leading-blank-line variants with it. I confirmed it here:
>
> ```diff
> -    if n == 1:
> +    if len(pattern.strip().split('\n')) == 1:
> ```
>
> With that line, #54575, and your commit, all 10 cases of the test below pass. On main 8 of 10 cases fail, and without the one-line change 2 of 10 fail (both are the trailing-newline case). Your existing tests and #54575's pass either way. Reverting only that line breaks only the trailing-newline cases. Take the line, the test, or neither, whichever is easiest. The line is the reviewer's, so if you take it, `Co-authored-by: Enough1122 <10966420+Enough1122@users.noreply.github.com>` would credit them.
>
> Separately: the branch's bot_relay commit conflicts with main in `tui_gateway/methods_bot_relay.py`. The fix commit `5f3f5896` cherry-picks cleanly on its own.
>
> (I used an AI assistant to run the comparison, draft the test and write this comment, and I checked the results myself.)
>
> <details><summary>tests/tools/test_fuzzy_match_wrong_region.py</summary>
>
> ```python
> """Wrong-region fuzzy edits must fail loud on the live patch path.
>
> When old_string is not in the file, the similarity fallbacks must not overwrite
> a region whose text differs from it: the patch reports an error and the file
> stays byte-identical, so the model re-reads instead of corrupting code. Near
> misses on the same text still apply, and the matcher names the non-exact
> strategy that matched them.
> Refs #54572, #111116.
> """
>
> import pytest
>
> from tools.environments.local import LocalEnvironment
> from tools.file_operations import ShellFileOperations
> from tools.fuzzy_match import STRATEGIES, fuzzy_find_and_replace
>
> # case -> (file content, old_string, new_string)
> WRONG_REGION = {
>     # #54572: first and last lines line up; the middle names a different statement.
>     "block_anchor_middle": (
>         "def handler(request):\n    audit_log(request.user_id)\n    return process(request)\n",
>         "def handler(request):\n    validate(request.token)\n    return process(request)",
>         "def handler(request):\n    rate_limit(request)\n    return process(request)",
>     ),
>     # #125376: one line that differs only in the method name (similarity 0.92).
>     "single_line_wrong_token": (
>         "def f(v):\n    return value.strip()\n",
>         "    return value.trim()",
>         "    return value.fixed()",
>     ),
>     # #111127 battery, missing_anchor trap: the same without indentation. (The
>     # battery's new_string is a substring of the file, so it takes the
>     # already-applied path instead; any other replacement shows the defect.)
>     "single_line_missing_anchor": (
>         "def normalize(value):\n    return value.strip()\n",
>         "return value.trim()",
>         "return value.casefold()",
>     ),
>     # Review on #125376: one logical line plus its line terminator.
>     "single_line_trailing_newline": (
>         "def f(v):\n    return value.strip()\n",
>         "    return value.trim()\n",
>         "    return value.fixed()\n",
>     ),
> }
>
> # case -> (file content, old_string, new_string, text that must land)
> NEAR_MISS = {
>     # #54575: same block, indentation drifted and one remembered value off.
>     "block_drift": (
>         "def foo():\n    x = 1\n    y = 2\n    return x + y\n",
>         "def foo():\n  x = 1\n  y = 9\n  return x + y",
>         "def foo():\n    return 0\n",
>         "return 0",
>     ),
>     # #111127 battery, indentation_drift trap: two spaces sent, four in the file.
>     "indentation_drift": (
>         "def retry_delay():\n    return 250\n",
>         "\n  return 250\n",
>         "\n  return 500\n",
>         "return 500",
>     ),
> }
>
>
> @pytest.fixture
> def ops(tmp_path):
>     return ShellFileOperations(LocalEnvironment(cwd=str(tmp_path), timeout=15), cwd=str(tmp_path))
>
>
> def _v4a(path, old, new):
>     hunk = [f"-{line}" for line in old.split("\n")] + [f"+{line}" for line in new.split("\n")]
>     return "\n".join(["*** Begin Patch", f"*** Update File: {path}", "@@", *hunk, "*** End Patch"])
>
>
> @pytest.mark.parametrize("mode", ["replace", "v4a"])
> @pytest.mark.parametrize("case", list(WRONG_REGION))
> def test_wrong_region_edit_fails_loud_and_leaves_file_untouched(ops, tmp_path, case, mode):
>     content, old, new = WRONG_REGION[case]
>     target = tmp_path / "target.py"
>     target.write_text(content, encoding="utf-8")
>     _, count, strategy, err = fuzzy_find_and_replace(content, old, new)
>
>     if mode == "replace":
>         result = ops.patch_replace(str(target), old, new)
>     else:
>         result = ops.patch_v4a(_v4a(str(target), old, new))
>
>     on_disk = target.read_text(encoding="utf-8")
>     assert result.error is not None and not result.success and on_disk == content, (
>         f"wrong region replaced via {strategy}: count={count}, error={err!r}\n{on_disk}")
>
>
> @pytest.mark.parametrize("case", list(NEAR_MISS))
> def test_near_miss_edit_still_applies_via_a_non_exact_strategy(ops, tmp_path, case):
>     content, old, new, landed = NEAR_MISS[case]
>     target = tmp_path / "target.py"
>     target.write_text(content, encoding="utf-8")
>
>     _, count, strategy, err = fuzzy_find_and_replace(content, old, new)
>     assert (count, err) == (1, None)
>     assert strategy in {name for name, _fn in STRATEGIES} - {"exact"}
>
>     result = ops.patch_replace(str(target), old, new)
>     assert result.success and result.error is None, result.error
>     assert landed in target.read_text(encoding="utf-8")
> ```
>
> </details>

## 3. Comment on #54575 (one comment)

Owner note: the diff inside this block's `<details>` is `c54575-rebased-on-main.diff` byte for byte (sha256 `e8da4410…`, 188 lines, 8.6 KB); `git apply --check` passes on main 44a1ce9724 and on aaa863f7ff. Its blank context lines are a single space; `git apply` still accepts the diff if an editor strips that space.

> I compared this with the other open fixes for the same block_anchor case (#126502, #93717) on main at `44a1ce97`. Your guard refuses the #54572 repro, and it also refuses both of those PRs' Markdown repros. It runs after the escape-drift check, so it keeps the two existing escape-drift messages, which a flat 0.70 threshold turns into a plain "Could not find a match". The 13 neighbouring test files pass unchanged (284 passed, 8 skipped, same as main).
>
> The branch now conflicts with main in tests only. Main deleted `TestStrategyNameSurfaced` and `TestTerminalOutputCleanliness` next to your additions. Keeping main's deletion plus your new classes is enough, and the diff below applies cleanly to main.
>
> Your floor runs on the single-line case from #125376 too, but lets it through: `trim()` vs `strip()` is 0.923 after normalization, above the 0.90 floor, so that edit still applies via `context_aware`. #125376 refuses single-line patterns inside `context_aware` itself. The two fixes cover different cases and compose without conflict.
>
> (I used an AI assistant to run the comparison, prepare the rebase diff and write this comment, and I checked the results myself.)
>
> <details><summary>rebase of this branch onto main: additions only, <code>tools/fuzzy_match.py</code> +30, tests +127, 0 lines removed</summary>
>
> ```diff
> --- a/tools/fuzzy_match.py
> +++ b/tools/fuzzy_match.py
> @@ -301,6 +301,22 @@
>  # unique replacement, never safe under replace_all.
>  SIMILARITY_STRATEGIES = frozenset({"block_anchor", "context_aware"})
>  
> +# These same two strategies are also the only ones that can accept a region whose
> +# *content* differs from old_string by more than formatting. They are reached only after
> +# every formatting-tolerant strategy has already failed, so when they fire, old_string is
> +# not present except as an approximate shape. A match that is the same block with a line
> +# or two drifted is a useful rescue; a match that merely shares its first/last line (or
> +# half its lines) with an unrelated block means we would overwrite text the caller never
> +# named. Require the matched region to be substantially the same text as old_string.
> +_FUZZY_CONTENT_FLOOR = 0.90
> +
> +
> +def _normalized_similarity(region: str, pattern: str) -> float:
> +    """Similarity of two strings ignoring unicode form and whitespace runs."""
> +    def _norm(s: str) -> str:
> +        return re.sub(r"\s+", " ", _unicode_normalize(s)).strip()
> +    return SequenceMatcher(None, _norm(region), _norm(pattern)).ratio()
> +
>  
>  # ── Orchestrator ─────────────────────────────────────────────────────────
>  
> @@ -388,6 +404,20 @@
>              if drift_err:
>                  return content, 0, None, drift_err
>  
> +        # Content-divergence guard. Drop any similarity-strategy match that is not
> +        # substantially the same text as old_string, comparing with unicode form and
> +        # whitespace runs normalized away so legitimate reflow, indentation and
> +        # smart-quote drift still pass. If nothing survives, fall through to the next
> +        # strategy and ultimately the no-match path, which prompts a re-read instead of
> +        # editing the wrong place.
> +        if strategy_name in SIMILARITY_STRATEGIES:
> +            matches = [
> +                (start, end) for (start, end) in matches
> +                if _normalized_similarity(content[start:end], old_string) >= _FUZZY_CONTENT_FLOOR
> +            ]
> +            if not matches:
> +                continue
> +
>          effective_new = _maybe_unescape_new_string(new_string, content, matches)
>          if strategy_name == "unicode_normalized":
>              effective_new = _preserve_unicode_in_replacement(content, matches, old_string, effective_new)
> --- a/tests/tools/test_fuzzy_match.py
> +++ b/tests/tools/test_fuzzy_match.py
> @@ -320,6 +320,64 @@
>          )
>  
>  
> +class TestContentDivergenceGuard:
> +    """A fuzzy match must not overwrite a region whose content differs from
> +    old_string in more than formatting, even when a first/last-line anchor or a
> +    partial line overlap lines up. Otherwise the edit lands on the wrong text
> +    and the tool still reports success."""
> +
> +    def test_block_anchor_partial_middle_does_not_overwrite(self):
> +        # The file's middle line is a real audit_log call. old_string names a
> +        # different statement that never existed in the file, but shares the
> +        # first and last lines. This must not replace the audit_log line.
> +        content = (
> +            "def handler(request):\n"
> +            "    audit_log(request.user_id)\n"
> +            "    return process(request)\n"
> +        )
> +        old_string = (
> +            "def handler(request):\n"
> +            "    validate(request.token)\n"
> +            "    return process(request)"
> +        )
> +        new_string = (
> +            "def handler(request):\n"
> +            "    rate_limit(request)\n"
> +            "    return process(request)"
> +        )
> +        new, count, strategy, err = fuzzy_find_and_replace(content, old_string, new_string)
> +        assert count == 0, f"overwrote a non-matching region via {strategy}"
> +        assert new == content
> +        assert "audit_log(request.user_id)" in new
> +
> +    def test_context_aware_half_matching_block_does_not_overwrite(self):
> +        # Only the first and last of four lines match the file. The two middle
> +        # lines (the real balance check and ledger debit) never appear in
> +        # old_string and must survive.
> +        content = (
> +            "def transfer(amount, dst):\n"
> +            "    check_balance(amount)\n"
> +            "    ledger.debit(amount, dst)\n"
> +            "    return receipt(dst)\n"
> +        )
> +        old_string = (
> +            "def transfer(amount, dst):\n"
> +            "    # TODO add logging here\n"
> +            "    pass\n"
> +            "    return receipt(dst)"
> +        )
> +        new, count, strategy, err = fuzzy_find_and_replace(content, old_string, "x = 1")
> +        assert count == 0, f"overwrote a half-matching region via {strategy}"
> +        assert "check_balance(amount)" in new
> +        assert "ledger.debit(amount, dst)" in new
> +
> +    def test_genuine_single_line_drift_still_matches(self):
> +        # The same block with one line lightly drifted is a legitimate rescue
> +        # and must still apply, so the guard does not regress real edits.
> +        content = "def foo():\n    x = 1\n    y = 2\n    return x + y\n"
> +        old_string = "def foo():\n    x = 1\n    y = 9\n    return x + y"
> +        new, count, strategy, err = fuzzy_find_and_replace(content, old_string, "def foo():\n    return 0\n")
> +        assert count == 1
>  
>  
>  class TestEscapeDriftGuard:
> --- a/tests/tools/test_file_tools_live.py
> +++ b/tests/tools/test_file_tools_live.py
> @@ -195,3 +195,72 @@
>              assert "~" not in result
>  
>  # ── Terminal output cleanliness ──────────────────────────────────────────
> +
> +
> +# ── patch_replace wrong-region regression (PR #54572 / #54575) ──────────
> +
> +WRONG_REGION_CONTENT = (
> +    "def handler(request):\n"
> +    "    audit_log(request.user_id)\n"
> +    "    return process(request)\n"
> +)
> +
> +
> +WRONG_REGION_OLD = (
> +    "def handler(request):\n"
> +    "    validate(request.token)\n"
> +    "    return process(request)"
> +)
> +
> +
> +WRONG_REGION_NEW = (
> +    "def handler(request):\n"
> +    "    rate_limit(request)\n"
> +    "    return process(request)"
> +)
> +
> +
> +class TestPatchReplaceWrongRegionRejected:
> +    """Live regression for the bug where a fuzzy strategy (block_anchor /
> +    context_aware) would happily overwrite a region whose real content
> +    differed from old_string, so the patch 'succeeded' while editing the
> +    wrong place. After PR #54575 the guard must reject the match, surface
> +    an error via PatchResult, and leave the on-disk file byte-identical."""
> +
> +    def test_block_anchor_wrong_region_is_rejected(self, ops, tmp_path):
> +        # File contents deliberately do not contain any substring that looks
> +        # like validate(request.token). The first/last lines do match the
> +        # model's pattern, which is precisely what used to trick strategy 8.
> +        target = tmp_path / "service.py"
> +        target.write_text(WRONG_REGION_CONTENT)
> +
> +        result = ops.patch_replace(
> +            str(target), WRONG_REGION_OLD, WRONG_REGION_NEW
> +        )
> +
> +        assert result.error is not None, (
> +            "patch_replace returned success for a wrong-region match — "
> +            "this is the bug PR #54572 / #54575 fixes."
> +        )
> +        # File on disk must be untouched. The audit_log line is the canary:
> +        # if the guard regressed, this line gets clobbered with
> +        # validate(request.token) or rate_limit(request).
> +        assert target.read_text() == WRONG_REGION_CONTENT
> +        assert "audit_log(request.user_id)" in target.read_text()
> +        assert "validate(request.token)" not in target.read_text()
> +        assert "rate_limit(request)" not in target.read_text()
> +
> +    def test_legitimate_rescue_still_applies(self, ops, tmp_path):
> +        """Sanity check: the guard must not regress real edits. A pattern
> +        that differs from the file only in indentation / whitespace still
> +        has to apply."""
> +        target = tmp_path / "math.py"
> +        target.write_text("def foo():\n    x = 1\n    y = 2\n    return x + y\n")
> +        result = ops.patch_replace(
> +            str(target),
> +            "def foo():\n  x = 1\n  y = 9\n  return x + y",  # drifted indent + value
> +            "def foo():\n    return 0\n",
> +        )
> +        assert result.error is None, f"legitimate edit rejected: {result.error}"
> +        assert "return 0" in target.read_text()
> +        assert "audit_log" not in target.read_text()  # not this file's content
> ```
>
> </details>

## 4. Comment on #111127 (one comment)

> I ran the battery at `5444b1a2` on main at `44a1ce97`. For str_replace 6 of 6 tasks pass; for hermes_patch 5 of 6 pass, and the one that fails is missing_anchor, applied via `context_aware`. That is the same result as the earlier run on `602e5963`.
>
> One thing I noticed while running it against the open fixes (#125376, #54575): hermes_patch stays at 5 of 6 passing even with the fix in. The trap's new_string `return value` is a substring of `return value.strip()`. After the refusal, the already-applied check reports `no_change` instead of `rejected`. With a new_string that isn't already in the file (for example `return value.casefold()`), the trap outcome moves with the fix: `applied` on main, `rejected` with #125376. I checked this by calling the matcher directly; I did not re-run the battery with the changed task.
>
> (I used an AI assistant to run the battery and the direct calls and to write this comment, and I checked the results myself.)

## Tone gate (self-check, author worker, re-run in round 4; the independent read is still pending)

- peer: yes. Each comment reports a result and offers one piece of work.
- no_labor: yes. The fold-in line, the rebase diff and the test are supplied in full; nothing is asked of the author beyond accepting or declining.
- no_internal_leak: yes. No lane, envelope, experiment IDs or board jargon in the comments.
- smallest_ask: yes. One line plus an optional test, one rebase diff, and one trap tweak. The test stays optional because each carrier already brings its own tests, and upstream's salvage bar is 2 tests or fewer.
- self_service: yes. The fold-in diff, the test (§2) and the rebase diff (§3) are inline, so no comment points at a file the reader cannot see; the rebase diff applies cleanly to main at `44a1ce97`. Until round 4, §3 held a paste instruction instead of the diff, so this line was not true then.
- local_voice: yes. Plain first person.
- easy_decline: yes. "Take the line, the test, or neither."
- credit: the stripped-pattern line and the trailing-newline case are credited to the reviewer who proposed them (Enough1122, review comment on #125376, 2026-09-29), in the wave row and in the #125376 comment. The wave row also names the authors of every reused test case (MaxFreedomPollard, likivik, Finn763, KoNit-K, Enough1122). Our part is stated as verification plus the regression test.
- No @mentions. Each of the four quoted blocks ends with an AI-assistance line that names what the assistant did, including writing that comment or row. The §1 line was added in the round-3 fix; NousResearch/hermes-agent#130139's own body has none, so the delta comment cannot rely on it.
- counts: every A/B result says "N of 10 cases fail" or "N of 10 cases pass", and the battery results say "N of 6 tasks pass".
- no owner notes in the posted text: the four quoted blocks contain no HTML comments, no placeholders and no instructions to the poster. Owner notes sit outside the quotes only.
- main: every block names `44a1ce97`, where all its counts were measured, and none calls it current main.
