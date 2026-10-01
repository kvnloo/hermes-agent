"""Catalog-loader probe for the plugin-catalog-entries staging branch.

Run from a hermes-agent worktree root with the repo on sys.path. Uses only the runtime loader
(hermes_cli.plugin_catalog) on the in-tree plugin-catalog/ directory: no network, no CLI.
Prints one JSON line: file count, loaded-entry count, and the named entry as the loader sees it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from hermes_cli import plugin_catalog as pc  # noqa: E402

name = sys.argv[1] if len(sys.argv) > 1 else "paw-pii"
root = pc.get_catalog_dir()
files = sorted(p.name for p in root.glob("*.yaml") if p.name != "removed.yaml")
entries = pc.load_catalog()
hit = next((e for e in entries if e.name == name), None)
repo = sys.argv[2] if len(sys.argv) > 2 else "https://github.com/kvnloo/pii"
removed = pc.find_removed(name) or pc.find_removed(repo)
out = {
    "catalog_dir": str(root),
    "files": len(files),
    "loaded": len(entries),
    "all_loaded": len(files) == len(entries),
    "entry_present": hit is not None,
    "entry": hit.to_dict() if hit is not None and hasattr(hit, "to_dict") else None,
    "install_identifier": getattr(hit, "install_identifier", None),
    "capability_summary": pc.entry_capability_summary(hit) if hit is not None and hasattr(pc, "entry_capability_summary") else None,
    "removed_match": None if removed is None else str(removed),
    "name_collisions": [f for f in files if f.rsplit(".", 1)[0] == name],
}
print(json.dumps(out, sort_keys=True))
