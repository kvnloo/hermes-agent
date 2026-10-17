"""Select complete frontend products and stage the runnable native agent."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.bundles.payload import resolve_revision, snapshot
from scripts.bundles.native import stage_native


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--cache", type=Path, help="persistent uv build cache")
    parser.add_argument("--tui", type=Path)
    parser.add_argument("--tsp", type=Path)
    parser.add_argument("--web", type=Path)
    args = parser.parse_args(argv)
    supplied = (args.tui, args.tsp, args.web)
    if any(path is not None for path in supplied) and not all(path is not None for path in supplied):
        parser.error("supply --tui, --tsp, and --web products together, or none to build them")
    node = shutil.which("node")
    if node is None:
        raise FileNotFoundError("Node is required to validate or build frontend products")
    revision = resolve_revision(ROOT, args.ref)
    args.ref = revision
    if args.tui is not None:
        args.frontends = {
            "tui": args.tui.resolve(), "tsp": args.tsp.resolve(), "web": args.web.resolve(),
        }
        return stage_native(args)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="hermes-products-") as temp:
        products = Path(temp)
        source = products / "source"
        snapshot(ROOT, revision, source)
        # The staging interpreter need not be a Hermes runtime; render icons on one.
        from scripts.build.icon_environment import prepare_icon_environment
        icon_python = prepare_icon_environment(source, products / "icon-environment", args.cache)
        env = {**os.environ, "HERMES_PYTHON": str(icon_python)}
        commands = [
            ["scripts/build/node-deps.mjs", "--source", str(source),
             "--workspace", "ui-tui", "--workspace", "ui-tsp", "--workspace", "web"],
            ["scripts/generate-icons.mjs", "--source", str(source), "--out", str(products / "icons")],
            ["scripts/build/tui.mjs", "--source", str(source), "--out", str(products / "tui")],
            ["scripts/build/tsp.mjs", "--source", str(source), "--out", str(products / "tsp")],
            ["scripts/build/web.mjs", "--source", str(source), "--icons", str(products / "icons"), "--out", str(products / "web")],
        ]
        for command in commands:
            subprocess.run([node, *command], cwd=ROOT, env=env, check=True)
        args.frontends = {"tui": products / "tui", "tsp": products / "tsp", "web": products / "web"}
        return stage_native(args)


if __name__ == "__main__":
    raise SystemExit(main())
