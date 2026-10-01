"""Emulate #111127 arms._hermes_replace on the missing_anchor trap with its own new_string
and with a new_string not already in the file. Direct calls, each arm's fuzzy_match by path."""
import importlib.util, json, sys
from pathlib import Path
ARMS_DIR = Path(sys.argv[1]); ARMS = sys.argv[2].split(",")
content = "def normalize(value):\n    return value.strip()\n"
def outcome(mod, old, new):
    new_content, count, strategy, error = mod.fuzzy_find_and_replace(content, old, new, replace_all=False)
    if error:
        if mod.is_already_applied(content, old, new):
            return "no_change"
        return "no_change" if error == mod.IDENTICAL_STRINGS_ERROR else "rejected"
    if count == 0:
        return "no_change" if new in content else "rejected"
    return f"applied:{strategy}"
out = {}
for arm in ARMS:
    spec = importlib.util.spec_from_file_location("m" + str(abs(hash(arm))), ARMS_DIR / arm / "fuzzy_match.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    out[arm] = {"trap_as_written(new='return value')": outcome(mod, "return value.trim()", "return value"),
                "variant(new='return value.casefold()')": outcome(mod, "return value.trim()", "return value.casefold()")}
print(json.dumps(out, indent=1))
