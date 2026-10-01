This slice no longer applies to main. The media code has grown since August (tool-image retirement inside the protected tail, the send-path `evict_stale_outbound_tool_images`, the `_multimodal` envelope). `merge-tree` now conflicts in `agent/context_compressor.py`, and AGENTS.md now rules out re-export seams for internal moves.

I rebuilt just the media slice on current main without the seam. It keeps this PR's module name and topic cut, and callers and tests import from `agent/context_compressor_media.py`. No behaviour change: tests/agent and tests/tools give the same pass/fail set before and after, and every moved statement is byte- and AST-identical. Patch attached.

One knock-on to flag: the same media commit (5aa1746a28) also sits, unchanged, in #80645, #80644, #81074 and #81181, which stack on this PR. If a rebuilt media slice lands, that commit is obsolete in all five, and each would need to drop it when rebased, because it adds the same new file.

Since this PR was opened, the file has also been split from the maintainer side: micro-compaction moved to `agent/micro_compaction.py` (4a64d42f9b, in #102117) and summary dispatch to `agent/context_compressor_summary.py` (77086b1439, in #104920). If the media helpers are already planned that way, please ignore this.

If not: is an outside split of the media helpers wanted now, given how often this file changes? On 2026-10-01, 411 open PRs touched it. Not counting this stack and 16 stale-base diffs of 600+ files, seven of them would need a small follow-up if this lands: five change the moved code (#90910, #106867, #107589, #110103, #130634), and #85481 and #104914 add facade calls to moved helpers that the facade would no longer import. An eighth, #120403, only adds an old-path import of `_rewritten`, which keeps working because the facade still imports that name. If yes, happy for it to be folded into this PR, or to go in as a salvage with Andrex as co-author, whichever the maintainers prefer.

AI assistance: prepared with Claude Code (Claude Opus 5.5). It made the move with a small AST-based script, ran the checks and drafted this comment.
