from pathlib import Path
from tempfile import TemporaryDirectory


def probe(call, delimiter, two):
    first = "FIRST-fb2-46f2".ljust(64, "x")
    second = "SECOND-fb2-93da".ljust(64, "y")
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "MEMORY.md").write_text("@doc:alpha", encoding="utf-8")
        path = root / "docs" / "alpha.md"
        adds = [call(root, "add", body) for body in
                ([first, second] if two else [first])]
        read = call(root, "read", None)
        raw = path.read_bytes() if path.exists() else b""
        entries = read.get("entries")
        if "Unknown action 'read'" in read.get("error", ""):
            entries = raw.decode("utf-8").split(delimiter)
        survived = first.encode() in [x.encode() for x in entries or []]
        print("adds:", adds, "\nread:", read, "\nfile:", repr(raw))
        print(f"FIRST_SURVIVED_SECOND_ADD = {survived}; file bytes = {len(raw)}")
        return all(a.get("success") and not a.get("staged") for a in adds)
