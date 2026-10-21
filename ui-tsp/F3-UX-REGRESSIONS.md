# F3 keyboard and plan regressions

Tab accepts an open completion. Otherwise it opens a native Keyboard actions
picker for enabled rendered card and composer buttons. F6 opens this picker
inside a sheet too. Tab/Shift+Tab and arrows select, Enter activates, and Escape
returns without changing the draft or caret. Composer Shift+Tab still cycles
effort. This uses native picker selection because TSP focus addresses editors,
not arbitrary button focus. All keys live in `src/actions.ts`.

Help sends scroll keys to its sheet body. Settings category names include their
change counts in the label, rather than a badge which replaces the accessible
name. Plan revision uses a bounded multiline editor. Refinement, annotation and
revision have separate drafts. Deny-and-steer splits the live transcript at the
user correction so settlement cannot put the resulting answer before it.
Multi-file drops parse quoted or escaped image paths without shell evaluation.
The singleton treemap root discards its child flex basis so CSS height applies.

## Rendered receipts

Run from the repository root, with an owned TMPDIR. On a shared host, put each
command under the shared lock and nice. These fixtures make no model calls.

```sh
python ui-tsp/e2e/f3_geometry.py "$PWD" --baseline --receipts "$TMPDIR/f3-before"
python ui-tsp/e2e/f3_geometry.py "$PWD" --receipts "$TMPDIR/f3-after"
python ui-tsp/e2e/openui_geometry.py "$PWD" --baseline --receipts "$TMPDIR/map-before"
python ui-tsp/e2e/openui_geometry.py "$PWD" --receipts "$TMPDIR/map-after"
```

The F3 runner saves PNGs, native text trees, accessibility names and 21 checks at
measured 80x28, 100x30 and 160x44. Baseline uses affected modules verbatim from
724b2aaec5 and reports expected-red. The OpenUI runner uses the real Luau plugin,
checks dense root containment, then drills into a singleton at the same measured
sizes and asserts positive leaf geometry. Its baseline intentionally exits 1 on
the zero-height leaf. Captures are isolated `tern serve` evidence, not signed-in
native-window or OS screen-reader certification.
