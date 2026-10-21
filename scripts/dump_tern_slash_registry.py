#!/usr/bin/env python3
"""Export Tern's offline slash catalog from the canonical classic registry."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hermes_cli.commands import COMMAND_REGISTRY


def catalog():
    return [dict(name=c.name, aliases=list(c.aliases), description=c.description,
                 args_hint=c.args_hint, gateway_only=c.gateway_only)
            for c in COMMAND_REGISTRY]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    target = ROOT/'ui-tsp/src/classic-commands.generated.json'
    content = json.dumps(catalog(), ensure_ascii=False, indent=2)+'\n'
    if args.check:
        if target.read_text() != content:
            raise SystemExit('Classic slash catalog drift: run python scripts/dump_tern_slash_registry.py')
    else:
        target.write_text(content)


if __name__ == '__main__':
    main()
