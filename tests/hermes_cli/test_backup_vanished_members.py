"""Regression: full backups must preserve the last good archive when all sources vanish.

A bounded number of missing members is harmless only when other files made it
into the archive. Exercises the real full-zip publisher and ZIP member writer.
"""

import zipfile
from pathlib import Path

from hermes_cli import backup as backup_mod


def test_full_zip_accepts_one_vanished_member_but_never_an_empty_archive(
    tmp_path, monkeypatch,
) -> None:
    names = ("alpha.txt", "beta.txt", "rotated.log")
    real_write = zipfile.ZipFile.write

    # Both cases are required: the original implementation rejects the first;
    # the proposed allowance incorrectly publishes a clean archive in the second.
    for gone in ({"rotated.log"}, set(names)):
        home = tmp_path / f"home-{len(gone)}"
        home.mkdir()
        for name in names:
            (home / name).write_text(name, encoding="utf-8")

        archive = tmp_path / f"automatic-{len(gone)}.zip"
        with zipfile.ZipFile(archive, "w") as existing:
            existing.writestr("previous.txt", "last good backup")
        previous_bytes = archive.read_bytes()

        def write_or_vanish(zf, filename, arcname=None, compress_type=None, compresslevel=None):
            path = Path(filename)
            if path.name in gone:
                path.unlink()
                raise FileNotFoundError(2, "No such file or directory", str(path))
            return real_write(
                zf, filename, arcname=arcname, compress_type=compress_type,
                compresslevel=compresslevel,
            )

        with monkeypatch.context() as patch:
            # Isolate the scan/read race without mocking backup publication.
            patch.setattr(
                backup_mod, "_iter_backup_files",
                lambda root, _out: ((root / name, Path(name)) for name in names),
            )
            patch.setattr(zipfile.ZipFile, "write", write_or_vanish)
            published = backup_mod._write_full_zip_backup(archive, home)

        if len(gone) == 1:
            assert published == archive
            with zipfile.ZipFile(archive) as zf:
                assert set(zf.namelist()) == {"alpha.txt", "beta.txt"}
        else:
            assert published is None
            assert archive.read_bytes() == previous_bytes
            assert not archive.with_name(archive.stem + ".incomplete.zip").exists()
