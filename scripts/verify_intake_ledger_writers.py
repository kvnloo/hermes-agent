#!/usr/bin/env python3
"""Exercise the existing operation's real renderer/journal with concurrent intake writers.

Run through fleet-build, with a frozen copy of render_ledger.py and ledger_journal.py.
Only the temporary directory is modified, never the live ledger or journal.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PLUGINS = Path(__file__).resolve().parents[1] / 'plugins'
sys.path.insert(0, str(PLUGINS))
from intake_ledger_match.matcher import update_ledger


def main():
    operation = Path(sys.argv[1])
    with tempfile.TemporaryDirectory(prefix='intake-writers-') as directory:
        root = Path(directory)
        for name in ('render_ledger.py', 'ledger_journal.py'):
            source = operation / name
            print(name, 'sha256=' + hashlib.sha256(source.read_bytes()).hexdigest())
            shutil.copyfile(source, root / name)
        ledger = root / 'ayo-ledger.json'
        rows = [{'id': f'R{n:02}', 'owner': 'ayo', 'status': 'open', 'ask': f'Existing ask {n}',
                 'check': '', 'evidence': '', 'note': ''} for n in range(1, 9)]
        ledger.write_text(json.dumps(rows))
        result = update_ledger(ledger, 'new-message', 'Track penguin migration across Antarctica')
        assert result['action'] == 'new', result
        # Import only in a child, so the actual module computes its paths in the copied operation.
        check = subprocess.run([sys.executable, '-c',
                                'import ledger_journal as j; assert j.LOCK == j.J + ".lock"; print(j.LOCK)'],
                               cwd=root, text=True, capture_output=True, check=False)
        assert check.returncode == 0, check.stderr
        print('SHARED_LOCK', check.stdout.strip())
        code = ('import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); '
                'from intake_ledger_match.matcher import update_ledger; '
                'update_ledger(Path(sys.argv[2]), sys.argv[3], sys.argv[4])')
        children = []
        for n in range(1, 9):
            rid = f'R{n:02}'
            for kind, command in (
                ('render', [sys.executable, str(root / 'render_ledger.py'), rid, 'done', f'evidence-{n}', 'verified']),
                ('intake', [sys.executable, '-c', code, str(PLUGINS), str(ledger), f'm{n}', rid]),
            ):
                children.append((kind, rid, subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)))
        for kind, rid, child in children:
            stdout, stderr = child.communicate(timeout=30)
            print(kind, rid, 'exit=' + str(child.returncode), stdout.strip(), stderr.strip())
            assert child.returncode == 0
        current = {r['id']: r for r in json.loads(ledger.read_text())}
        for n in range(1, 9):
            row = current[f'R{n:02}']
            assert row['status'] == 'done' and row['evidence'] == f'evidence-{n}', row
            assert row['mentions'] == [f'm{n}'], row
        assert current['I001']['source_msg_id'] == 'new-message'
        rendered = subprocess.run([sys.executable, str(root / 'render_ledger.py')], capture_output=True, text=True, check=False)
        assert rendered.returncode == 0, rendered.stderr
        assert 'I001' in (root / 'AYO-LEDGER.md').read_text()
        print('PASS: 8 journal statuses + 8 intake mentions + new row survive concurrent atomic writes and rendering')


if __name__ == '__main__':
    main()
