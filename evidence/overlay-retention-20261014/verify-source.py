"""Verify a prepared partial execution tree against immutable Git blob identities."""
import hashlib
import json
import pathlib
import sys

packet = pathlib.Path(__file__).resolve().parent
manifest = json.loads((packet / "provenance.json").read_text())
variant = sys.argv[1]
assert variant in {"head", "parent"}
source = pathlib.Path(sys.argv[2])
for item in manifest["source_manifest"]:
    path = item["path"]
    expected = item["sha"]
    if variant == "parent" and path == "ui-tui/src/lib/agentsOverlayClock.ts":
        expected = manifest["parent_clock_blob"]
    data = (source / path).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert actual == expected, (path, actual, expected)
test = source / "ui-tui/src/__tests__/agentsOverlayRetention.test.tsx"
assert hashlib.sha256(test.read_bytes()).hexdigest() == manifest["test_sha256"]
ink = source / "ui-tui/packages/hermes-ink/dist/entry-exports.js"
assert hashlib.sha256(ink.read_bytes()).hexdigest() == manifest["ink_bundle_sha256"]
print(f"{variant}: {len(manifest['source_manifest'])} original files, test, and Ink bundle verified")
