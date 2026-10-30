"""Builds the study's sanitized-echo candidate on upstream main 0107da5d2a (study only, not an upstream PR).

Every response field that hands live entry text back to the model (current_entries,
closest_entries, ambiguous `matches`) passes through the same strict threat scan the
load-time snapshot uses. Clean entries are returned unchanged, so main's live-entries
contract (07af2357ec) is preserved.
"""
import sys
from pathlib import Path

p = Path(sys.argv[1]) / "tools/memory_tool_store.py"
s = p.read_text(encoding="utf-8")

helper = '''

def _echo_safe(entries):
    """Entries echoed to the model in an error response, with threat hits replaced by the
    same kind of [BLOCKED] marker the prompt snapshot uses (RFC #143379 study candidate)."""
    from tools.threat_patterns import scan_for_threats
    out = []
    for entry in entries:
        findings = scan_for_threats(entry, scope="strict") if entry and not entry.startswith("[BLOCKED:") else None
        out.append(entry if not findings else
                   f"[BLOCKED: entry contained threat pattern(s): {', '.join(findings)}. Text withheld.]")
    return out
'''
anchor = "def _no_match_error("
assert s.count(anchor) == 1
s = s.replace(anchor, helper.lstrip("\n") + "\n\n" + anchor, 1)

edits = [
    ('closest = [entries[i] for score, i in scored[:3] if score >= 0.3]',
     'closest = _echo_safe([entries[i] for score, i in scored[:3] if score >= 0.3])'),
    ('_error(message, "over_budget", current_entries=self._entries_for(target), usage=self._usage(target))',
     '_error(message, "over_budget", current_entries=_echo_safe(self._entries_for(target)), usage=self._usage(target))'),
    ('_no_match_error(entries, old_text, verb, current_entries=entries)',
     '_no_match_error(entries, old_text, verb, current_entries=_echo_safe(entries))'),
    ('matches=[entries[i][:80] + ("..." if len(entries[i]) > 80 else "")\n                                   for i in _substring_matches(entries, old_text)])',
     'matches=[e[:80] + ("..." if len(e) > 80 else "")\n                                   for e in _echo_safe([entries[i] for i in _substring_matches(entries, old_text)])])'),
]
for old, new in edits:
    assert s.count(old) == 1, old
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("candidate applied")
