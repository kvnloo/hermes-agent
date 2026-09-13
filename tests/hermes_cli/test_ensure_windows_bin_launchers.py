"""``hermes`` must survive git operations on the checkout (launcher layout).

The Windows ``hermes`` command is a launcher derived from the venv console
script. Its canonical home is the managed binary dir ``HERMES_HOME\\bin`` —
OUTSIDE the git checkout — because the earlier in-checkout home
(``hermes-agent\\bin``) was swept by ``hermes update``'s autostash
(``git stash push --include-untracked``) and, with the desktop updater's
``--keep-stash``, never restored: ``hermes`` stopped resolving in every new
terminal (``venv\\Scripts`` itself must stay off PATH — it shadows the
user's ``python``, #83797).

``ensure_windows_bin_launchers`` re-stages missing launchers (canonical dir
always for the managed clone; legacy dir only while the user PATH still
points at it), choosing the form by venv kind: exe copy for normal venvs,
``.cmd`` delegator for relocatable venvs whose exe trampolines die when
copied out of ``venv\\Scripts``. ``migrate_windows_bin_path`` moves an
existing install's PATH to the canonical layout from the ``hermes update``
tail. Platform verdict, PATH values, and registry I/O are injected
parameters (same pattern as ``hermes_constants.venv_bin_dir``), so these
tests are host-independent input→output checks, not host fakes.

The ``.cmd`` delegator body must stay ASCII-pure for the default
``%LOCALAPPDATA%\\hermes\\hermes-agent`` layout even when the Windows
username carries non-ASCII characters (cmd.exe expands ``%LOCALAPPDATA%``
at run time); embedding the literal absolute path under
``write_text(..., encoding="ascii")`` raised ``UnicodeEncodeError`` (a
``ValueError``, not an ``OSError``) and escaped the per-file guard, so
no launcher was staged and a zero-byte ``.heal.<pid>`` file leaked.
"""

from pathlib import Path

import pytest

from hermes_cli._install_repair import (
    _WINDOWS_BIN_LAUNCHERS,
    _cmd_delegator_body,
    _normalize_windows_path,
    ensure_windows_bin_launchers,
    migrate_windows_bin_path,
)


def _make_managed(tmp_path, monkeypatch, *, relocatable: bool = False):
    """Fake managed layout: HERMES_HOME/hermes-agent/venv/Scripts + launchers."""
    home = tmp_path / "hermes"
    root = home / "hermes-agent"
    scripts = root / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    for name in _WINDOWS_BIN_LAUNCHERS:
        (scripts / f"{name}.exe").write_bytes(b"MZ console script: " + name.encode())
    cfg = "home = X\nversion_info = 3.11.15\n"
    if relocatable:
        cfg += "relocatable = true\n"
    (root / "venv" / "pyvenv.cfg").write_text(cfg, encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home, root


@pytest.fixture
def managed_install(tmp_path, monkeypatch):
    return _make_managed(tmp_path, monkeypatch)


def _make_relocatable_managed_under(home: Path, monkeypatch) -> tuple[Path, Path]:
    """Create a relocatable-venv managed install rooted at *home*.

    The venv, the managed clone, and the venv's console scripts are all
    materialized under *home*; HERMES_HOME is pointed at *home*. Used to
    reach the ``.cmd`` delegator writer from a layout whose path carries
    non-ASCII characters (international Windows usernames).
    """
    root = home / "hermes-agent"
    scripts = root / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    for name in _WINDOWS_BIN_LAUNCHERS:
        (scripts / f"{name}.exe").write_bytes(b"MZ console script: " + name.encode())
    (root / "venv" / "pyvenv.cfg").write_text(
        "home = X\nversion_info = 3.11.15\nrelocatable = true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home, root


def test_managed_clone_heals_canonical_home_bin(managed_install):
    home, root = managed_install

    restored = ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    assert len(restored) == len(_WINDOWS_BIN_LAUNCHERS)
    for name in _WINDOWS_BIN_LAUNCHERS:
        assert (home / "bin" / f"{name}.exe").read_bytes() == (
            root / "venv" / "Scripts" / f"{name}.exe"
        ).read_bytes()


def test_relocatable_venv_gets_cmd_delegators_not_exe_copies(tmp_path, monkeypatch):
    """A copied relocatable-venv trampoline dies ('uv trampoline failed to
    canonicalize script path') — the heal must emit .cmd delegators."""
    home, root = _make_managed(tmp_path, monkeypatch, relocatable=True)

    restored = ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    assert {Path(p).suffix for p in restored} == {".cmd"}
    for name in _WINDOWS_BIN_LAUNCHERS:
        # Read with UTF-8, not ASCII, so this test is not locked into the
        # ASCII-only body assumption — a non-ASCII username on a non-default
        # layout embeds the literal path and is written as UTF-8.
        body = (home / "bin" / f"{name}.cmd").read_text(encoding="utf-8")
        # Delegates to the in-venv exe by absolute path, forwarding args.
        assert str(root / "venv" / "Scripts" / f"{name}.exe") in body
        assert "%*" in body
        assert not (home / "bin" / f"{name}.exe").exists()


def test_cmd_delegator_body_uses_localappdata_expansion_for_default_layout():
    """Default %LOCALAPPDATA%\hermes\hermes-agent layout collapses to a pure
    ASCII body referencing %LOCALAPPDATA% (cmd.exe expands it at run time),
    even when the Source path itself carries non-ASCII."""
    default_root = Path("C:/Users/M\u00fcller/AppData/Local/hermes/hermes-agent")
    source = default_root / "venv" / "Scripts" / "hermes.exe"

    body, encoding = _cmd_delegator_body(source, default_root=default_root)

    assert encoding == "ascii"
    assert body.isascii()
    assert "%*" in body
    assert "@echo off\r\n" in body
    assert (
        '"%LOCALAPPDATA%\\hermes\\hermes-agent\\venv\\Scripts\\hermes.exe" %*'
        in body
    )
    # The literal non-ASCII username must NOT be embedded.
    assert "M\u00fcller" not in body


def test_cmd_delegator_body_supports_dotvenv_layout():
    """The default anchor delegates the relative tail, so a ``.venv`` layout
    also collapses to the %LOCALAPPDATA% form."""
    default_root = Path("C:/Users/M\u00fcller/AppData/Local/hermes/hermes-agent")
    source = default_root / ".venv" / "Scripts" / "hermes-acp.exe"

    body, encoding = _cmd_delegator_body(source, default_root=default_root)

    assert encoding == "ascii"
    assert body.isascii()
    assert (
        '"%LOCALAPPDATA%\\hermes\\hermes-agent\\.venv\\Scripts\\hermes-acp.exe" %*'
        in body
    )


def test_cmd_delegator_body_falls_back_to_literal_for_non_default_layout():
    """A HERMES_HOME override (or custom InstallDir) outside the default
    %LOCALAPPDATA% layout keeps the literal source path and writes UTF-8."""
    source = Path("/opt/hermes/hermes-agent/venv/Scripts/hermes.exe")

    body, encoding = _cmd_delegator_body(source, default_root=None)

    assert encoding == "utf-8"
    assert str(source) in body
    assert "%LOCALAPPDATA%" not in body
    assert "%*" in body


def test_cmd_delegator_body_falls_back_to_literal_when_source_outside_default_root():
    """default_root set but source not under it: literal path, UTF-8."""
    default_root = Path("/default/hermes/hermes-agent")
    source = Path("/opt/custom/hermes-agent/venv/Scripts/hermes.exe")

    body, encoding = _cmd_delegator_body(source, default_root=default_root)

    assert encoding == "utf-8"
    assert str(source) in body
    assert "%LOCALAPPDATA%" not in body


def test_relocatable_venv_cmd_delegator_for_non_ascii_default_layout_uses_localappdata(
    tmp_path, monkeypatch
):
    """Regression: an international Windows username (non-ASCII %LOCALAPPDATA%)
    plus a relocatable venv used to raise UnicodeEncodeError out of
    ensure_windows_bin_launchers, never staging the launcher and leaking a
    .heal.<pid> file. Post-fix the body inlines %LOCALAPPDATA% (ASCII-pure),
    the launcher stages, and the never-raise contract holds."""
    local_appdata = tmp_path / "M\u00fcller" / "AppData" / "Local"
    home = local_appdata / "hermes"
    home, root = _make_relocatable_managed_under(home, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    restored = ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    assert len(restored) == len(_WINDOWS_BIN_LAUNCHERS)
    assert {Path(p).suffix for p in restored} == {".cmd"}
    for name in _WINDOWS_BIN_LAUNCHERS:
        cmd = home / "bin" / f"{name}.cmd"
        assert cmd.is_file()
        body = cmd.read_text(encoding="utf-8")
        # The literal non-ASCII username must NOT appear in the file body;
        # the file references the exe via %LOCALAPPDATA% instead.
        assert "M\u00fcller" not in body
        assert body.isascii()
        assert (
            '"%LOCALAPPDATA%\\hermes\\hermes-agent\\venv\\Scripts\\'
            f"{name}.exe\" %*"
        ) in body
        assert not (home / "bin" / f"{name}.exe").exists()
    # Staging never leaked a .heal.<pid> file.
    assert [
        p.name for p in (home / "bin").iterdir() if ".heal." in p.name
    ] == []


def test_relocatable_venv_cmd_delegator_for_non_ascii_overridden_home_uses_utf8_fallback(
    tmp_path, monkeypatch
):
    """HERMES_HOME overridden to a non-ASCII path OUTSIDE the default
    %LOCALAPPDATA% layout does not collapse to the %LOCALAPPDATA% form, so
    the body embeds the literal path; writing as UTF-8 (not ASCII) keeps the
    never-raise contract and stages a launcher that round-trips on a UTF-8
    active code page (65001)."""
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    home = tmp_path / "M\u00fcller" / "hermes"
    home, root = _make_relocatable_managed_under(home, monkeypatch)

    restored = ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    assert len(restored) == len(_WINDOWS_BIN_LAUNCHERS)
    assert {Path(p).suffix for p in restored} == {".cmd"}
    for name in _WINDOWS_BIN_LAUNCHERS:
        cmd = home / "bin" / f"{name}.cmd"
        assert cmd.is_file()
        body = cmd.read_text(encoding="utf-8")
        # The literal non-ASCII path is embedded (no %LOCALAPPDATA% form),
        # and the file's bytes decode as UTF-8.
        assert str(root / "venv" / "Scripts" / f"{name}.exe") in body
        assert "M\u00fcller" in body
        assert "%LOCALAPPDATA%" not in body
        assert "%*" in body
        assert not (home / "bin" / f"{name}.exe").exists()
    assert [
        p.name for p in (home / "bin").iterdir() if ".heal." in p.name
    ] == []


def test_never_raises_and_cleans_staging_when_body_unencodable(tmp_path, monkeypatch):
    """Defense for the widened per-file guard: if the body somehow stays
    unencodable even under the UTF-8 fallback (e.g. a surrogate that UTF-8
    itself cannot encode), the function STILL never raises (its documented
    contract), does not stage, and leaves no .heal.<pid> file behind. This
    is the regression that the original `except OSError` guard missed —
    UnicodeEncodeError is a ValueError, not an OSError."""
    home = tmp_path / "hermes"
    home, root = _make_relocatable_managed_under(home, monkeypatch)
    from hermes_cli import _install_repair

    def _force_unencodable(source, *, default_root):
        # A lone surrogate encodes as neither ASCII nor UTF-8.
        return ('@echo off\r\n"\ud800" %*\r\n', "ascii")

    monkeypatch.setattr(_install_repair, "_cmd_delegator_body", _force_unencodable)

    restored = ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    assert restored == []
    for name in _WINDOWS_BIN_LAUNCHERS:
        assert not (home / "bin" / f"{name}.cmd").exists()
        assert not (home / "bin" / f"{name}.exe").exists()
    assert [
        p.name for p in (home / "bin").iterdir() if ".heal." in p.name
    ] == []


def test_no_staging_litter_for_non_ascii_default_layout(tmp_path, monkeypatch):
    """The staging cleanup path also runs cleanly when the body stays
    ASCII-pure on the non-ASCII default layout path."""
    local_appdata = tmp_path / "M\u00fcller" / "AppData" / "Local"
    home = local_appdata / "hermes"
    home, root = _make_relocatable_managed_under(home, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    leftovers = [p.name for p in (home / "bin").iterdir() if ".heal." in p.name]
    assert leftovers == []


def test_migrate_windows_bin_path_for_non_ascii_default_layout(tmp_path, monkeypatch):
    """End-to-end: hermes update's PATH migration also completes on the
    non-ASCII default layout (migrate_windows_bin_path calls
    ensure_windows_bin_launchers with no local try/except, relying on the
    never-raise contract)."""
    local_appdata = tmp_path / "M\u00fcller" / "AppData" / "Local"
    home = local_appdata / "hermes"
    home, root = _make_relocatable_managed_under(home, monkeypatch)
    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

    state, read, write = _fake_registry([str(root / "bin")])

    ok = migrate_windows_bin_path(
        root, windows=True, read_user_path=read, write_user_path=write
    )

    assert ok
    for name in _WINDOWS_BIN_LAUNCHERS:
        cmd = home / "bin" / f"{name}.cmd"
        assert cmd.is_file()
        assert cmd.read_text(encoding="utf-8").isascii()
    keys = [_normalize_windows_path(e) for e in state["entries"]]
    assert _normalize_windows_path(home / "bin") in keys
    assert _normalize_windows_path(root / "bin") not in keys


def test_existing_exe_counts_as_present_for_relocatable_venv(tmp_path, monkeypatch):
    """Exe copies staged before a venv rebuild embed the swapped-in-place
    venv's absolute path and keep working — never replaced with .cmd."""
    home, root = _make_managed(tmp_path, monkeypatch, relocatable=True)
    (home / "bin").mkdir()
    for name in _WINDOWS_BIN_LAUNCHERS:
        (home / "bin" / f"{name}.exe").write_bytes(b"pre-rebuild copy")

    assert ensure_windows_bin_launchers(root, windows=True, user_path_entries=[]) == []
    for name in _WINDOWS_BIN_LAUNCHERS:
        assert (home / "bin" / f"{name}.exe").read_bytes() == b"pre-rebuild copy"
        assert not (home / "bin" / f"{name}.cmd").exists()


def test_healthy_canonical_layout_is_a_noop(managed_install):
    home, root = managed_install
    (home / "bin").mkdir()
    for name in _WINDOWS_BIN_LAUNCHERS:
        (home / "bin" / f"{name}.exe").write_bytes(b"present")

    assert ensure_windows_bin_launchers(root, windows=True, user_path_entries=[]) == []


def test_legacy_bin_restaged_only_while_on_user_path(managed_install):
    home, root = managed_install
    legacy = root / "bin"

    restored = ensure_windows_bin_launchers(
        root, windows=True, user_path_entries=[str(legacy)]
    )

    stems = {Path(p).stem for p in restored}
    assert set(_WINDOWS_BIN_LAUNCHERS) <= stems
    for name in _WINDOWS_BIN_LAUNCHERS:
        assert (legacy / f"{name}.exe").is_file()        # legacy consent honored
        assert (home / "bin" / f"{name}.exe").is_file()  # canonical healed too


def test_legacy_bin_not_restaged_without_path_consent(managed_install):
    home, root = managed_install

    ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    assert not (root / "bin").exists()


def test_source_checkout_untouched(tmp_path, monkeypatch):
    """A checkout NOT under HERMES_HOME gains nothing anywhere."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    root = tmp_path / "src" / "hermes-agent"
    scripts = root / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    for name in _WINDOWS_BIN_LAUNCHERS:
        (scripts / f"{name}.exe").write_bytes(b"MZ")

    assert ensure_windows_bin_launchers(root, windows=True, user_path_entries=[]) == []
    assert not (home / "bin").exists()
    assert not (root / "bin").exists()


def test_noop_on_posix(managed_install):
    home, root = managed_install

    assert ensure_windows_bin_launchers(root, windows=False) == []
    assert not (home / "bin").exists()


def test_profile_session_still_heals_the_shared_bin(tmp_path, monkeypatch):
    """Under ``hermes -p <name>`` HERMES_HOME points inside profiles/<name>;
    the launcher dir is per-machine, so the heal must anchor on the default
    root and fire anyway — a habitual profile user gets the same repair."""
    home = tmp_path / "hermes"
    root = home / "hermes-agent"
    scripts = root / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    for name in _WINDOWS_BIN_LAUNCHERS:
        (scripts / f"{name}.exe").write_bytes(b"MZ")
    (root / "venv" / "pyvenv.cfg").write_text("home = X\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home / "profiles" / "work"))

    restored = ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    assert len(restored) == len(_WINDOWS_BIN_LAUNCHERS)
    for name in _WINDOWS_BIN_LAUNCHERS:
        assert (home / "bin" / f"{name}.exe").is_file()
    assert not (home / "profiles" / "work" / "bin").exists()


def test_noop_when_console_scripts_missing(tmp_path, monkeypatch):
    """A venv mid-repair has no console scripts — nothing to copy, no error."""
    home = tmp_path / "hermes"
    root = home / "hermes-agent"
    (root / "venv" / "Scripts").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))

    assert ensure_windows_bin_launchers(root, windows=True, user_path_entries=[]) == []


def test_no_staging_litter_left_behind(managed_install):
    home, root = managed_install

    ensure_windows_bin_launchers(root, windows=True, user_path_entries=[])

    leftovers = [p.name for p in (home / "bin").iterdir() if ".heal." in p.name]
    assert leftovers == []


# ---------------------------------------------------------------------------
# migrate_windows_bin_path — the `hermes update` tail migration
# ---------------------------------------------------------------------------


def _fake_registry(initial: list[str]):
    """In-memory user-PATH store standing in for the HKCU registry value."""
    state = {"entries": list(initial), "kind": 2, "writes": 0}

    def read():
        return list(state["entries"]), state["kind"]

    def write(entries, kind):
        state["entries"] = list(entries)
        state["kind"] = kind
        state["writes"] += 1

    return state, read, write


def test_migration_moves_path_to_home_bin_and_strips_legacy(managed_install):
    home, root = managed_install
    legacy_bin = str(root / "bin")
    legacy_scripts = str(root / "venv" / "Scripts")
    state, read, write = _fake_registry(
        [legacy_bin, legacy_scripts, r"C:\Windows\system32"]
    )
    (root / "bin").mkdir()
    (root / "bin" / "hermes.exe").write_bytes(b"legacy copy")

    ok = migrate_windows_bin_path(
        root, windows=True, read_user_path=read, write_user_path=write
    )

    assert ok
    keys = [_normalize_windows_path(e) for e in state["entries"]]
    assert _normalize_windows_path(home / "bin") in keys
    assert _normalize_windows_path(legacy_bin) not in keys
    assert _normalize_windows_path(legacy_scripts) not in keys
    assert _normalize_windows_path(r"C:\Windows\system32") in keys  # untouched
    for name in _WINDOWS_BIN_LAUNCHERS:
        assert (home / "bin" / f"{name}.exe").is_file()
    # Legacy FILES stay: editor/ACP configs holding absolute launcher paths
    # keep working. Only the PATH entry (the sweepable resolution route) goes.
    assert (root / "bin" / "hermes.exe").read_bytes() == b"legacy copy"


def test_migration_works_for_relocatable_venv(tmp_path, monkeypatch):
    home, root = _make_managed(tmp_path, monkeypatch, relocatable=True)
    state, read, write = _fake_registry([str(root / "bin")])

    ok = migrate_windows_bin_path(
        root, windows=True, read_user_path=read, write_user_path=write
    )

    assert ok
    for name in _WINDOWS_BIN_LAUNCHERS:
        assert (home / "bin" / f"{name}.cmd").is_file()
    keys = [_normalize_windows_path(e) for e in state["entries"]]
    assert _normalize_windows_path(home / "bin") in keys


def test_migration_is_idempotent(managed_install):
    home, root = managed_install
    state, read, write = _fake_registry([str(home / "bin"), r"C:\Windows\system32"])

    assert migrate_windows_bin_path(
        root, windows=True, read_user_path=read, write_user_path=write
    )
    first_entries = list(state["entries"])
    first_writes = state["writes"]

    assert migrate_windows_bin_path(
        root, windows=True, read_user_path=read, write_user_path=write
    )
    assert state["entries"] == first_entries
    assert state["writes"] == first_writes  # no redundant registry write


def test_migration_never_strips_path_when_staging_fails(tmp_path, monkeypatch):
    """No venv sources → launchers can't stage → PATH must stay untouched."""
    home = tmp_path / "hermes"
    root = home / "hermes-agent"
    (root / "venv" / "Scripts").mkdir(parents=True)  # no launcher exes inside
    monkeypatch.setenv("HERMES_HOME", str(home))
    legacy_bin = str(root / "bin")
    state, read, write = _fake_registry([legacy_bin])

    ok = migrate_windows_bin_path(
        root, windows=True, read_user_path=read, write_user_path=write
    )

    assert not ok
    assert state["entries"] == [legacy_bin]  # working entry preserved
    assert state["writes"] == 0


def test_migration_skips_source_checkouts(tmp_path, monkeypatch):
    home = tmp_path / "hermes-home"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    root = tmp_path / "src" / "hermes-agent"
    scripts = root / "venv" / "Scripts"
    scripts.mkdir(parents=True)
    for name in _WINDOWS_BIN_LAUNCHERS:
        (scripts / f"{name}.exe").write_bytes(b"MZ")
    state, read, write = _fake_registry([r"C:\Windows\system32"])

    assert not migrate_windows_bin_path(
        root, windows=True, read_user_path=read, write_user_path=write
    )
    assert state["writes"] == 0


def test_migration_noop_on_posix(managed_install):
    home, root = managed_install

    assert not migrate_windows_bin_path(root, windows=False)


def test_normalize_windows_path_equivalences():
    assert (
        _normalize_windows_path(r"C:\Users\Me\AppData\Local\hermes\bin")
        == _normalize_windows_path("c:/users/me/appdata/local/HERMES/BIN/")
    )


def test_repo_gitignores_the_legacy_bin_dir():
    """Transition safety: legacy in-checkout launchers must not be stash-swept.

    Until every install has migrated, pre-migration checkouts still carry
    launchers at ``<checkout>/bin``. ``hermes update`` autostashes with
    ``git stash push --include-untracked``; anything untracked and NOT
    ignored inside the checkout gets swept off disk. Exercises git's real
    ignore machinery rather than reading .gitignore text.
    """
    import subprocess

    repo_root = Path(__file__).resolve().parents[2]
    if not (repo_root / ".git").exists():
        pytest.skip("not running from a git checkout")

    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "bin/hermes.exe"],
        capture_output=True,
    )
    assert result.returncode == 0, (
        "bin/hermes.exe is not gitignored — hermes update's autostash "
        "(--include-untracked) would sweep pre-migration launchers off disk"
    )
