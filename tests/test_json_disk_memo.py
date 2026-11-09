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


def _atomic_replace_same_metadata(path: Path, payload: str) -> None:
    """Use a distinct inode while keeping the old mtime and byte count."""
    before = path.stat()
    candidate = path.with_name(path.name + ".incoming")
    candidate.write_text(payload, encoding="utf-8")
    assert candidate.stat().st_size == before.st_size
    os.utime(candidate, ns=(before.st_atime_ns, before.st_mtime_ns))
    os.replace(candidate, path)
    assert path.stat().st_ino != before.st_ino


def test_production_nested_objects_are_read_only(tmp_path):
    original = {"nested": {"rows": [{"tags": ["%", "_", "λ", "\\"]}]}}
    path = tmp_path / "readonly.json"
    path.write_text(json.dumps(original), encoding="utf-8")
    cached = memo.read_json_disk_memo(path)
    assert isinstance(cached, dict)
    assert isinstance(cached["nested"]["rows"], list)
    with pytest.raises(TypeError, match="read-only"):
        cached["nested"]["rows"][0]["tags"][0] = "bad"
    with pytest.raises(TypeError, match="read-only"):
        cached["nested"]["rows"][0]["tags"].append("bad")
    with pytest.raises(TypeError, match="read-only"):
        cached["nested"].update({"rows": []})
    with pytest.raises(TypeError, match="read-only"):
        cached["nested"]["rows"].sort()
    assert memo.read_json_disk_memo(path) is cached
    assert cached == _old_disk_reader(path) == original


def test_equal_mtime_equal_size_atomic_replace_does_not_reuse_inode(tmp_path):
    path = tmp_path / "replace.json"
    path.write_text('{"v":1}', encoding="utf-8")
    original = memo.read_json_disk_memo(path)
    _atomic_replace_same_metadata(path, '{"v":2}')
    updated = memo.read_json_disk_memo(path)
    assert original["v"] == 1
    assert updated["v"] == 2
    assert updated is not original
    assert memo.json_disk_memo_parse_count() == 2


def test_external_delete_recreate_cannot_resurrect_cached_generation(tmp_path):
    path = tmp_path / "recreated.json"
    path.write_text('{"v":1}', encoding="utf-8")
    signature = path.stat()
    assert memo.read_json_disk_memo(path)["v"] == 1
    path.unlink()
    with pytest.raises(FileNotFoundError):
        memo.read_json_disk_memo(path)
    path.write_text('{"v":2}', encoding="utf-8")
    os.utime(path, ns=(signature.st_atime_ns, signature.st_mtime_ns))
    assert memo.read_json_disk_memo(path)["v"] == 2


def test_external_process_atomic_writer_does_not_need_local_clear(tmp_path):
    import subprocess
    import sys

    path = tmp_path / "external.json"
    path.write_text('{"v":1}', encoding="utf-8")
    before = path.stat()
    assert memo.read_json_disk_memo(path)["v"] == 1
    writer = (
        "import os,sys; from pathlib import Path; "
        "p=Path(sys.argv[1]); q=p.with_suffix('.writer'); "
        "q.write_text(sys.argv[2],encoding='utf-8'); "
        "os.utime(q,ns=(int(sys.argv[3]),int(sys.argv[4]))); "
        "os.replace(q,p)"
    )
    subprocess.run(
        [sys.executable, "-c", writer, str(path), '{"v":2}',
         str(before.st_atime_ns), str(before.st_mtime_ns)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    assert path.stat().st_size == before.st_size
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert memo.read_json_disk_memo(path)["v"] == 2


def test_external_replace_between_stat_and_open_with_local_clear(tmp_path, monkeypatch):
    from threading import Event, current_thread

    path = tmp_path / "raced.json"
    path.write_text('{"v":1}', encoding="utf-8")
    entered, proceed = Event(), Event()
    original_open = Path.open
    paused = False

    def delayed_open(self, *args, **kwargs):
        nonlocal paused
        if self == path and current_thread().name.startswith("memo-race") and not paused:
            paused = True
            entered.set()
            assert proceed.wait(15)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", delayed_open)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="memo-race") as pool:
        # executor name memo-race_0: pause on the first open in the reader.
        reader = pool.submit(memo.read_json_disk_memo, path)
        assert entered.wait(15)
        _atomic_replace_same_metadata(path, '{"v":2}')
        clearing = pool.submit(memo.clear_json_disk_memo)
        proceed.set()
        assert reader.result(timeout=20)["v"] == 2
        clearing.result(timeout=20)
    assert memo.read_json_disk_memo(path)["v"] == 2


def test_in_place_change_after_open_retries_when_fstat_changes(tmp_path, monkeypatch):
    from threading import Event, current_thread

    path = tmp_path / "raced-in-place.json"
    path.write_text('{"v":1}', encoding="utf-8")
    old = path.stat()
    entered, proceed = Event(), Event()
    original_open = Path.open
    pause_once = False

    class DelayedRead:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def fileno(self):
            return self.stream.fileno()

        def read(self, *args):
            entered.set()
            assert proceed.wait(15)
            return self.stream.read(*args)

    def delayed_open(self, *args, **kwargs):
        nonlocal pause_once
        stream = original_open(self, *args, **kwargs)
        if self == path and current_thread().name.startswith("memo-inplace") and not pause_once:
            pause_once = True
            return DelayedRead(stream)
        return stream

    monkeypatch.setattr(Path, "open", delayed_open)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="memo-inplace") as pool:
        reader = pool.submit(memo.read_json_disk_memo, path)
        assert entered.wait(15)
        path.write_text('{"v":2}', encoding="utf-8")
        os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns + 1_000_000_000))
        proceed.set()
        assert reader.result(timeout=20)["v"] == 2
    assert memo.read_json_disk_memo(path)["v"] == 2
