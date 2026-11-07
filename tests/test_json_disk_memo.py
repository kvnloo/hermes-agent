"""Differential JSON decode contract and fail-fast guarded caller mutations."""

from __future__ import annotations

import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import json_disk_memo as memo


@pytest.fixture(autouse=True)
def _fresh_memo():
    memo.clear_json_disk_memo()
    yield
    memo.clear_json_disk_memo()


def _old_disk_reader(path: Path):
    """Original per-call JSON parser (before the in-process memo)."""
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def _generated_payloads():
    windows_path = r"C:\Users\模型\folder_%\file_name.json"
    # JSON allows duplicate object keys; both readers must retain the last value.
    yield "{}"
    yield "[]"
    yield (
        '{"duplicate":1,"duplicate":2,"path":'
        + json.dumps(windows_path, ensure_ascii=True)
        + ',"like":'
        + json.dumps("%_\\", ensure_ascii=True)
        + "}"
    )
    special = ("", "%", "_", r"part\child", "λ", "東京", windows_path, "a%b_c")
    rng = random.Random(1107)
    for count in (1, 17, 257):
        rows = [
            {
                "id": i % 7,  # duplicate values
                "name": special[i % len(special)],
                "path": windows_path + f"\\item_{i}%",
                "nested": {"children": [special[rng.randrange(len(special))], i]},
            }
            for i in range(count)
        ]
        yield json.dumps({"rows": rows, "unicode": "模型 🌐", "empty": []}, ensure_ascii=True)


@pytest.mark.parametrize("payload", list(_generated_payloads()))
def test_same_generated_json_as_old_parser(tmp_path, payload):
    path = tmp_path / "catalog.json"
    path.write_text(payload, encoding="utf-8")
    expected = _old_disk_reader(path)

    first = memo.read_json_disk_memo(path)
    second = memo.read_json_disk_memo(path)

    assert first == expected
    assert second == expected
    assert first is second
    assert memo.json_disk_memo_parse_count() == 1


def test_utf8_bom_is_identical_to_old_reader(tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"paths": [r"C:\folder\_x%", "κ"]}).encode("utf-8"))
    assert memo.read_json_disk_memo(path) == _old_disk_reader(path)


def test_shared_identity_and_guard_detects_nested_mutation(tmp_path):
    path = tmp_path / "catalog.json"
    original = {"xai": {"models": [{"id": "a"}, {"id": "a"}]}, "removed": ["_%", "\\"]}
    path.write_text(json.dumps(original), encoding="utf-8")

    first = memo.read_json_disk_memo(path)
    second = memo.read_json_disk_memo(path)
    assert first is second
    assert memo.json_disk_memo_parse_count() == 1

    with memo.guard_json_disk_memo_mutations():
        guarded = memo.read_json_disk_memo(path)
        assert guarded == original
        with pytest.raises(TypeError, match="read-only"):
            guarded["xai"]["models"][0]["id"] = "changed"
        with pytest.raises(TypeError, match="read-only"):
            guarded["xai"]["models"].append({"id": "extra"})
        with pytest.raises(TypeError, match="read-only"):
            guarded["removed"].clear()
        assert memo.read_json_disk_memo(path) is guarded
        assert memo.json_disk_memo_parse_count() == 1

    assert memo.read_json_disk_memo(path) == original


def test_rewrite_invalidates_file_version(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"version":1,"rows":[1]}', encoding="utf-8")
    assert memo.read_json_disk_memo(path)["version"] == 1
    before = path.stat()

    path.write_text('{"version":2,"rows":[1,2]}', encoding="utf-8")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    assert memo.read_json_disk_memo(path)["version"] == 2
    assert memo.json_disk_memo_parse_count() == 2


def test_failed_parse_is_not_negative_cached(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text('{"broken":', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        memo.read_json_disk_memo(path)
    path.write_text('{"repaired":true}', encoding="utf-8")
    assert memo.read_json_disk_memo(path) == {"repaired": True}


def test_concurrent_readers_parse_single_version_once(tmp_path):
    path = tmp_path / "catalog.json"
    original = {"rows": [{"id": i} for i in range(100)]}
    path.write_text(json.dumps(original), encoding="utf-8")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: memo.read_json_disk_memo(path), range(12)))
    assert all(result == original and result is results[0] for result in results)
    assert memo.json_disk_memo_parse_count() == 1
