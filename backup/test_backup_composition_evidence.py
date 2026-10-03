"""Real temp ZIP/publication/retention evidence; one synthetic composition control."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import types
import zipfile

import pytest

HERE = Path(__file__).parent

@pytest.mark.parametrize('variant', ['exact-main', 'hypothetical-composition'])
@pytest.mark.parametrize('survivor', [False, True], ids=['zero-archived', 'with-survivor'])
def test_mixed_disappearance_publication(tmp_path, monkeypatch, variant, survivor):
    import hermes_cli.backup as exact_main
    if variant == 'exact-main':
        backup = exact_main
        assert hashlib.sha256(Path(backup.__file__).read_bytes()).hexdigest() == json.loads((HERE/'source-bindings.json').read_text())['main_sha256']
    else:
        backup = types.ModuleType('hypothetical_backup_composition')
        compiled = compile((HERE/'hypothetical-backup.py').read_text(), str(HERE/'hypothetical-backup.py'), 'exec')
        exec(compiled, backup.__dict__)

    home = tmp_path/'home'
    home.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(home))
    # No config, secrets or databases: only owned ordinary fixture text files.
    victim = home/'transient.txt'
    victim.write_text('selected then removed')
    failed = home/'unreadable.txt'
    failed.write_text('simulated finite read error')
    if survivor:
        (home/'survivor.txt').write_text('useful recovery data')
    backup_dir = home/'backups'
    backup_dir.mkdir()
    current = backup_dir/'pre-update-2026-10-03-120000.zip'
    older = backup_dir/'pre-update-2026-10-01-120000.zip'
    old_salvage = backup_dir/'pre-update-2026-10-02-120000.incomplete.zip'
    for p in (current, older, old_salvage):
        with zipfile.ZipFile(p, 'w') as zf:
            zf.writestr('previous.txt', f'useful existing recovery: {p.name}')
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (current, older, old_salvage)}

    class Clock:
        @staticmethod
        def now():
            return datetime(2026, 10, 3, 12, 0, 0)
    monkeypatch.setattr(backup, 'datetime', Clock)
    real_scan = backup._iter_backup_files
    selected = []
    def scan_then_remove(*args, **kwargs):
        entries = list(real_scan(*args, **kwargs))
        selected.extend(str(rel) for _, rel in entries)
        assert set(selected) == ({'transient.txt', 'unreadable.txt', 'survivor.txt'} if survivor else {'transient.txt', 'unreadable.txt'})
        victim.unlink()
        yield from entries
    monkeypatch.setattr(backup, '_iter_backup_files', scan_then_remove)
    real_write = zipfile.ZipFile.write
    def finite_read_failure(zf, filename, arcname=None, *args, **kwargs):
        if Path(filename) == failed:
            # Main's real failed-member cleanup must remove this partial member.
            with zf.open(str(arcname), 'w') as member:
                member.write(b'partial bytes')
            raise OSError(5, 'owned fixture simulated read error')
        return real_write(zf, filename, arcname, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, 'write', finite_read_failure)
    result = backup.create_pre_update_backup(hermes_home=home, keep=1)
    fresh_salvage = backup_dir/'pre-update-2026-10-03-120000.incomplete.zip'
    archives = {}
    for p in sorted(backup_dir.glob('*.zip')):
        with zipfile.ZipFile(p) as zf:
            archives[p.name] = {'members': zf.namelist(), 'bytes': p.stat().st_size, 'crc_error': zf.testzip(), 'contents': {name: zf.read(name).decode() for name in zf.namelist()}}
    record = {'variant': variant, 'survivor': survivor, 'selected': selected, 'return': str(result) if result else None, 'archives': archives, 'prior_complete_preserved': all(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==before[p.name] for p in (current, older)), 'older_useful_salvage_preserved': old_salvage.exists(), 'fresh_salvage_published': fresh_salvage.exists(), 'partials_remaining': [str(p) for p in backup_dir.glob('*.partial')]}
    (HERE/f'{variant}-{"survivor" if survivor else "zero"}.json').write_text(json.dumps(record, indent=2)+'\n')
    assert result is None
    assert record['prior_complete_preserved']
    assert not record['partials_remaining']
    assert all('unreadable.txt' not in a['members'] for a in archives.values())
    # Existing main intent: if nothing can be salvaged, discard rather than
    # letting an empty new archive displace an older useful salvage.
    assert fresh_salvage.exists() is survivor
    assert old_salvage.exists() is (not survivor)
    if survivor:
        assert archives[fresh_salvage.name]['members'] == ['survivor.txt']
        assert archives[fresh_salvage.name]['contents'] == {'survivor.txt': 'useful recovery data'}
