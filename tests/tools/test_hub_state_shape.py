"""One malformed record in a hub state file must not take every other record down with it."""
import json

from tools.skills_hub import HubLockFile, TapsManager


def test_lock_keeps_good_entries_beside_a_malformed_one(tmp_path):
    path = tmp_path / "lock.json"
    path.write_text(json.dumps({"version": 1, "installed": {
        "bad": "oops", "num": 3, "ok": {"install_path": "ok", "identifier": "a/b/ok"}}}))
    lock = HubLockFile(path)
    assert lock.list_installed() == [{"name": "ok", "install_path": "ok", "identifier": "a/b/ok"}]
    assert lock.get_installed("bad") is None
    assert set(lock.by_identifier()) == {"a/b/ok"}
    # A wrong-shaped file reads as empty instead of raising in every consumer.
    path.write_text('{"version": 1, "installed": []}')
    assert HubLockFile(path).list_installed() == []


def test_taps_skip_a_malformed_tap_and_still_accept_new_ones(tmp_path):
    path = tmp_path / "taps.json"
    path.write_text(json.dumps({"taps": [1, {"path": "x/"}, {"repo": "a/b", "path": "s/"}]}))
    taps = TapsManager(path)
    assert taps.load() == [{"repo": "a/b", "path": "s/"}]
    assert taps.add("c/d") is True
    assert [t["repo"] for t in taps.load()] == ["a/b", "c/d"]
    assert taps.remove("a/b") is True
    assert [t["repo"] for t in taps.load()] == ["c/d"]


def test_non_utf8_bytes_in_one_hub_row_keep_other_rows_visible(tmp_path):
    """Regression for #118686: one undecodable byte must not hide valid records."""
    lock_path = tmp_path / "lock.json"
    lock_path.write_bytes(
        b'{"version":1,"installed":{"good":{"identifier":"owner/good","install_path":"good"},'
        b'"bad":"\xff"}}'
    )
    lock = HubLockFile(lock_path)
    assert lock.list_installed() == [
        {"name": "good", "identifier": "owner/good", "install_path": "good"}
    ]
    assert list(lock.by_identifier()) == ["owner/good"]

    taps_path = tmp_path / "taps.json"
    taps_path.write_bytes(
        b'{"taps":[{"repo":"good/repo","path":"skills/"}, "\xff"]}'
    )
    taps = TapsManager(taps_path)
    assert taps.load() == [{"repo": "good/repo", "path": "skills/"}]
    assert taps.add("more/repo") is True
    assert [row["repo"] for row in taps.load()] == ["good/repo", "more/repo"]
