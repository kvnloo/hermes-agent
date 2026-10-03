"""Emit a hypothetical bounded composition; never edit a checkout source file."""
import argparse, ast, difflib, hashlib, json, subprocess
from pathlib import Path
HERE = Path(__file__).parent
parser = argparse.ArgumentParser()
parser.add_argument('--repo', required=True, type=Path, help='Repository containing the two pinned source commits')
REPO = parser.parse_args().repo.resolve()
MAIN = 'bd0affe5e5f723579df8902852f5d0c47795f355'
DONOR = '5ef448a688b9cf47c382c372798b854a85982c1d'
def source(ref):
    return subprocess.check_output(['git', 'show', f'{ref}:hermes_cli/backup.py'], cwd=REPO, text=True)
main, donor = source(MAIN), source(DONOR)
def function(text, name):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return '\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])
helpers = ['_vanished_since_scan', '_in_kanban_scratch_workspace', '_confirmed_enoent', '_db_vanished_since_scan']
writer = function(donor, '_write_zip_entries')
assert writer.count('zf.write(abs_path, arcname=str(rel_path))') == 1
writer = writer.replace('zf.write(abs_path, arcname=str(rel_path))', '_write_zip_file(zf, abs_path, str(rel_path))')
overlay = main.replace(function(main, '_write_zip_entries'), '\n\n\n'.join([*(function(donor, name) for name in helpers), writer]))
# Preserve current main publication/error logic. Connect the donor's existing
# vanished callback only to the automatic path, not the manual backup caller.
auto = function(main, '_write_full_zip_backup_locked')
needle = 'on_error=lambda rel, exc: errors.append(f"{rel}: {exc}"),'
assert auto.count(needle) == 1
modified = auto.replace(needle, needle + '\n                on_vanished=lambda rel: logger.debug("Skipping %s in zip backup: vanished after scan", rel),')
overlay = overlay.replace(auto, modified)
(HERE/'main-backup.py').write_text(main)
(HERE/'donor-backup.py').write_text(donor)
(HERE/'hypothetical-backup.py').write_text(overlay)
(HERE/'composition.diff').write_text(''.join(difflib.unified_diff(main.splitlines(True), overlay.splitlines(True), fromfile='exact-main-backup.py', tofile='hypothetical-backup.py')))
sha = lambda t: hashlib.sha256(t.encode()).hexdigest()
(HERE/'source-bindings.json').write_text(json.dumps({'main': MAIN, 'donor': DONOR, 'main_sha256': sha(main), 'donor_sha256': sha(donor), 'overlay_sha256': sha(overlay), 'classification': 'hypothetical partial composition; not cherry-pick/integrated PR or production fix', 'unchanged_main_functions': ['_write_zip_file', '_atomic_output_path', '_create_prefixed_full_backup', '_prune_incomplete_zips'], 'modifications': ['four donor classification helpers', 'donor writer retaining main _write_zip_file', 'automatic vanished callback only']}, indent=2)+'\n')
