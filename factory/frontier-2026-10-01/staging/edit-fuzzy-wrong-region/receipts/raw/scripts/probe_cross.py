"""Cross-apply the block_anchor carriers' own repros (#93717, #126502) and the
escape-drift diagnostic that #93717 preserves to every arm, by direct calls.
usage: probe_cross.py <arms dir> <arm,arm,...>"""
import importlib.util
import json
import sys
from pathlib import Path

ARMS_DIR = Path(sys.argv[1])
ARMS = sys.argv[2].split(",")

content_middle = "path_a = C:\\Users\\alice\npath_b = D:\\Temp\\cache\nmode = production"
old_middle = "first = C:\\\\Users\\\\alice\nsecond = D:\\\\Temp\\\\cache\nrequested = staging"
CASES = {
    "c93717_markdown_weak_middle": (
        "# Tasks\n\n- [ ] Publish report\n  - Source: [paper](https://example.com/source)\n"
        "  - Status: queued\n  - Owner: Alice\n  - Notes: preserve metadata\n  <!-- task-end -->\n",
        "- [ ] Publish report\n  - Source: [pdf](https://files.test/final.pdf)\n  - Status: complete\n"
        "  - Reviewer: Bob\n  - Notes: add download\n  <!-- task-end -->",
        "- [x] Publish report\n  <!-- task-end -->",
        "refuse",
    ),
    "c126502_markdown_lookalike": (
        "- [ ] Collect source URL for the atlas entry review queue\n"
        "- source: https://internal.example.com/atlas/boreal-survey\n"
        "- status: pending editor signoff, owner marina, due thursday\n"
        "- [ ] Collect source URL for the atlas entry review queue\n",
        "- [ ] Collect source URL for the atlas entry review queue\n"
        "- ref: atlas boreal survey (mirror id 7, cached snapshot)\n"
        "- note: quarterly budget reforecast approved, kpi dashboard v2\n"
        "- [ ] Collect source URL for the atlas entry review queue\n",
        "REPLACED",
        "refuse",
    ),
    "main_escape_drift_apostrophe": (
        "line\n    x = 1\nline", "line\n  x = \\'a\\'\nline", "line\n  x = \\'b\\'\nline", "drift-diag",
    ),
    "c93717_backslash_diag_weak_anchor": (
        f"settings:\n{content_middle}\nend settings",
        f"settings:\n{old_middle}\nend settings",
        f"settings:\n{old_middle}\nend settings".replace("staging", "complete"),
        "drift-diag",
    ),
}


def load(arm):
    spec = importlib.util.spec_from_file_location("fm_" + arm.replace("-", "_").replace("+", "_"),
                                                  ARMS_DIR / arm / "fuzzy_match.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


out = {}
for arm in ARMS:
    mod = load(arm)
    out[arm] = {}
    for name, (content, old, new, want) in CASES.items():
        new_content, count, strategy, err = mod.fuzzy_find_and_replace(content, old, new)
        if count:
            got = f"applied:{strategy}"
        elif err and err.startswith("Escape-drift"):
            got = "refused:drift-diag"
        else:
            got = "refused:no-match"
        ok = (want == "refuse" and not count) or (want == "drift-diag" and got == "refused:drift-diag")
        out[arm][name] = {"got": got, "want": want, "ok": ok}
print(json.dumps(out, indent=1))
