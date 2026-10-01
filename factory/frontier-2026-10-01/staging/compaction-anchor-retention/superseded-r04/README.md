# Superseded round-4 material

STAGING.md, body.md and PR_BODY.md as they stood after round 4 (head 30a746f792 on main 040b6df2c4), plus
the round-3 fold-in patch (`foldin-on-117462.patch`, sha256 3713e44b..., rows in #117462's cheap-first
order: `task ids` after `todo ids`, `dotted keys` before `files`, `error messages` last), the five
r20261001-03 receipts that measured that fold-in arm (E03p, E03s, F02s, T01, AB117462) and its test
outputs (`raw/`).

Superseded on 2026-10-01 by round 5, which answered the round-3 re-verifier: that order took budget
from #117462's own `files` and `errors` lines, and body.md did not say so. Round 5 appends the rows
after `errors` instead (no #117462 line changes) and re-measured the fold-in arm (r20261001-05). The
head, the standalone patch and the RG01, N01 and N02 receipts did not change, so they are not copied
here. `harness/build_receipts.py` (round 3) read the old patch and raw files from the staging root;
they now sit here. Kept for history only; nothing here is cited.
