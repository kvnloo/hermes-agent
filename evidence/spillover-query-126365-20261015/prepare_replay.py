#!/usr/bin/env python3
"""Reconstruct the exact diagnostic's minimal inputs from pinned public source.

This packaging helper was prepared after the recorded runs; it is not a test
result. It makes no network requests and executes no Hermes code. The output
directory must not exist. Full GitHub snapshots are intentionally not copied.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path, help="Files from the exact pinned Hermes tree")
    parser.add_argument("output_dir", type=Path, help="New scratch directory; must not exist")
    args = parser.parse_args()
    packet = Path(__file__).resolve().parent
    provenance = json.loads((packet / "literal_provenance.json").read_text(encoding="utf-8"))
    recorded = json.loads((packet / "diagnostic_results.json").read_text(encoding="utf-8"))
    inputs = []
    for key, source in provenance["files"].items():
        data = (args.source_dir / source["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError("Pinned source SHA-256 mismatch: " + source["path"])
        git_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if git_blob != source["git_blob_sha1"]:
            raise ValueError("Pinned Git blob mismatch: " + source["path"])
        inputs.append((key, source, data))
    args.output_dir.mkdir(parents=False, exist_ok=False)
    for key, source, data in inputs:
        target = args.output_dir / source["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        response = {"content": data.decode("utf-8"), "sha": source["git_blob_sha1"],
                    "display_url": source["url"]}
        (args.output_dir / (key + "_response.json")).write_text(
            json.dumps(response) + "\n", encoding="utf-8")
    # Only these fields are consumed by the preserved diagnostic. Empty entries
    # retain the recorded count; they are not claimed to be full comment copies.
    comments = [{} for _ in range(recorded["comments_refreshed_count"] - 1)]
    comments.append(recorded["latest_comment"])
    (args.output_dir / "comments_snapshot.json").write_text(
        json.dumps({"comments": comments}) + "\n", encoding="utf-8")
    (args.output_dir / "pr_snapshot.json").write_text(json.dumps({
        "pull_request": {"head_sha": provenance["pin"], "url": recorded["pr_url"]}
    }) + "\n", encoding="utf-8")
    shutil.copyfile(packet / "diagnostic.py", args.output_dir / "diagnostic.py")
    print("Prepared pinned inputs only; diagnostic has not been executed.")


if __name__ == "__main__":
    main()
