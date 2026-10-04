"""An unreadable included subtree must not publish/prune as a complete backup."""
from argparse import Namespace
from pathlib import Path
import os
import zipfile

import pytest

from hermes_cli import backup


@pytest.mark.parametrize('automatic', [False, True], ids=['manual', 'pre-update'])
def test_scan_failure_preserves_complete_backup_until_readable(
        tmp_path, monkeypatch, capsys, caplog, automatic):
    home = tmp_path / 'home'
    home.mkdir()
    (home / 'visible.txt').write_text('visible recovery content')
    subtree = home / 'notes'
    subtree.mkdir()
    (subtree / 'retained.txt').write_text('must not silently omit this content')
    monkeypatch.setenv('HERMES_HOME', str(home))
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    output_dir = home / 'backups' if automatic else tmp_path / 'archives'
    output_dir.mkdir()
    prefix = 'pre-update-' if automatic else 'hermes-backup-'
    previous = output_dir / f'{prefix}2000-01-01-000000.zip'
    with zipfile.ZipFile(previous, 'w') as archive:
        archive.writestr('previous.txt', 'last complete recovery content')
    previous_bytes = previous.read_bytes()
    os.utime(previous, (1, 1))
    output = output_dir / f'{prefix}2099-01-01-000000.zip'

    def run():
        return (backup.create_pre_update_backup(hermes_home=home, keep=1) if automatic
                else backup.run_backup(Namespace(output=str(output), keep=1)))

    real_scandir = os.scandir
    denied = []
    def fail_owned_subtree(path):
        if Path(path) == subtree:
            denied.append(str(path))
            raise OSError(5, 'fixture subtree read failed', str(path))
        return real_scandir(path)

    with monkeypatch.context() as fault:
        fault.setattr(os, 'scandir', fail_owned_subtree)
        result = run()
    assert denied == [str(subtree)]
    assert result is (None if automatic else False), 'incomplete scan reported backup success'
    assert previous.read_bytes() == previous_bytes
    assert sorted(output_dir.glob('*.zip')) == [previous]
    assert not list(output_dir.glob('*.partial'))
    diagnostic = capsys.readouterr().out + caplog.text
    assert 'fixture subtree read failed' in diagnostic
    assert str(subtree) in diagnostic

    # The same real scanner/writer succeeds once the owned fixture becomes readable.
    healthy = run()
    assert healthy if automatic else healthy is True
    published = healthy if automatic else output
    with zipfile.ZipFile(published) as archive:
        assert archive.read('visible.txt') == b'visible recovery content'
        assert archive.read('notes/retained.txt') == b'must not silently omit this content'
        assert archive.testzip() is None
    assert not previous.exists(), 'a later complete backup should still honor keep=1'
