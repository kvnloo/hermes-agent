"""A selected provider-state scan failure must not authorize complete-backup pruning."""
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
import os
import zipfile

from hermes_cli import backup


def test_declared_external_scan_failure_preserves_backup_until_readable(
        tmp_path, monkeypatch, capsys):
    import plugins.memory as memory_plugins

    home = tmp_path / '.hermes'
    home.mkdir()
    (home / 'visible.txt').write_text('Hermes recovery content')
    provider_root = tmp_path / 'provider-state'
    subtree = provider_root / 'notes'
    subtree.mkdir(parents=True)
    (provider_root / 'metadata.txt').write_text('provider metadata')
    (subtree / 'retained.txt').write_text('provider durable content')
    monkeypatch.setenv('HERMES_HOME', str(home))
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    declarations = []
    def backup_paths():
        declarations.append(provider_root)
        return [provider_root]
    # Inert provider boundary; actual declaration collection, home-relative
    # archive naming, external scanner and full backup/retention remain real.
    monkeypatch.setattr(memory_plugins, '_get_active_memory_provider', lambda: 'fixture')
    monkeypatch.setattr(memory_plugins, 'load_memory_provider', lambda name: SimpleNamespace(backup_paths=backup_paths))
    output_dir = tmp_path / 'archives'
    output_dir.mkdir()
    previous = output_dir / 'hermes-backup-2000-01-01-000000.zip'
    with zipfile.ZipFile(previous, 'w') as archive:
        archive.writestr('previous.txt', 'last complete recovery content')
    previous_bytes = previous.read_bytes()
    os.utime(previous, (1, 1))
    output = output_dir / 'hermes-backup-2099-01-01-000000.zip'
    args = Namespace(output=str(output), keep=1)
    real_scandir = os.scandir
    denied = []
    def fail_selected_subtree(path):
        if Path(path) == subtree:
            denied.append(str(path))
            raise OSError(5, 'fixture selected external scan failed', str(path))
        return real_scandir(path)

    with monkeypatch.context() as fault:
        fault.setattr(os, 'scandir', fail_selected_subtree)
        result = backup.run_backup(args)
    assert declarations == [provider_root]
    assert denied == [str(subtree)]
    assert result is False, 'selected external subtree was omitted from a successful backup'
    assert previous.read_bytes() == previous_bytes
    assert sorted(output_dir.glob('*.zip')) == [previous]
    assert not list(output_dir.glob('*.partial'))
    diagnostic = capsys.readouterr().out
    assert 'fixture selected external scan failed' in diagnostic
    assert str(subtree) in diagnostic

    assert backup.run_backup(args) is True
    assert declarations == [provider_root, provider_root]
    with zipfile.ZipFile(output) as archive:
        assert archive.read('visible.txt') == b'Hermes recovery content'
        assert archive.read('_external/provider-state/metadata.txt') == b'provider metadata'
        assert archive.read('_external/provider-state/notes/retained.txt') == b'provider durable content'
        assert archive.testzip() is None
    assert not previous.exists()
