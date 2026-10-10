"""Exact owner module: real os.walk with a single injected filesystem denial."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tree_fingerprint as subject

class WalkErrorContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'agent' / 'nested').mkdir(parents=True)
        (self.root / 'agent' / '__init__.py').write_text('ROOT = 1\n')
        (self.root / 'agent' / 'nested' / 'worker.py').write_text('VALUE = 1\n')
        subject._content_memo.clear()
        subject.reset_boot()

    def denied_scan(self):
        original = subject.os.scandir
        blocked = self.root / 'agent' / 'nested'
        def scan(path):
            if Path(path) == blocked:
                raise PermissionError(13, 'fixture subtree denial', str(path))
            return original(path)
        return patch.object(subject.os, 'scandir', side_effect=scan)

    def test_unchanged_tree_is_clean(self):
        subject.record_boot(self.root)
        self.assertIsNone(subject.detect_skew(self.root))

    def test_real_content_change_is_detected(self):
        subject.record_boot(self.root)
        (self.root / 'agent' / 'nested' / 'worker.py').write_text('VALUE = 200\n')
        self.assertIsNotNone(subject.detect_skew(self.root))

    def test_unreadable_subtree_fingerprint_fails_open(self):
        with self.denied_scan():
            self.assertIsNone(subject.content_fingerprint(self.root))

    def test_unreadable_subtree_does_not_invent_skew(self):
        subject.record_boot(self.root)
        with self.denied_scan():
            self.assertIsNone(subject.detect_skew(self.root))

if __name__ == '__main__':
    unittest.main(verbosity=2)
