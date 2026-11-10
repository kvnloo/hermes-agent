"""Full-zip backup churn must never replace a good backup with an empty archive."""

import zipfile
from pathlib import Path

from hermes_cli import backup


def test_one_vanished_entry_is_tolerated_but_all_vanished_entries_are_discarded(
        tmp_path, monkeypatch) -> None:
    """One rotated file is harmless; a wholly vanished scan has nothing to back up."""
    real_write = zipfile.ZipFile.write

    for disappeared in (1, 5):
        case_dir = tmp_path / f"case-{disappeared}"
        home = case_dir / ".hermes"
        home.mkdir(parents=True)
        files = [home / f"rotating-{i}.txt" for i in range(5)]
        for path in files:
            path.write_text("content", encoding="utf-8")

        archive = case_dir / "automatic.zip"
        archive.write_bytes(b"previous-good-archive")
        to_rotate = set(files[:disappeared])

        def rotate_before_write(zf, filename, arcname=None, compress_type=None, compresslevel=None):
            path = Path(filename)
            if path in to_rotate:
                path.unlink()
                to_rotate.remove(path)
            return real_write(
                zf, filename, arcname=arcname,
                compress_type=compress_type, compresslevel=compresslevel,
            )

        with monkeypatch.context() as patch:
            patch.setattr(zipfile.ZipFile, "write", rotate_before_write)
            result = backup._write_full_zip_backup(archive, home)

        assert not to_rotate
        if disappeared == 1:
            assert result == archive
            with zipfile.ZipFile(archive) as zf:
                assert len(zf.namelist()) == 4
        else:
            assert result is None
            assert archive.read_bytes() == b"previous-good-archive"
            assert not (case_dir / "automatic.incomplete.zip").exists()
