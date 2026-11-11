"""Offline synthetic-git contract tests; NOT Hermes head results."""
from pathlib import Path
import tempfile
import unittest
from review_followup import HEADS, git, merge_probe, pathlib_probe


def run(path, *args):
    cp = git(path, *args)
    if cp.returncode:
        raise AssertionError((args, cp.stderr))
    return cp.stdout.strip()


class ReviewFollowupTests(unittest.TestCase):
    def test_path_import_detection(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            run(p, "init", "-q")
            run(p, "config", "user.email", "test@example.invalid")
            run(p, "config", "user.name", "Tester")
            f = p / "tui_gateway/methods_onboarding.py"
            f.parent.mkdir()
            f.write_text("def _due_stamp():\n    return Path('x')\n")
            run(p, "add", ".")
            run(p, "commit", "-qm", "old")
            old = run(p, "rev-parse", "HEAD")
            self.assertTrue(pathlib_probe(p, "old", old)["potential_NameError"])
            f.write_text("from pathlib import Path\n\ndef _due_stamp():\n    return Path('x')\n")
            run(p, "commit", "-qam", "fixed")
            new = run(p, "rev-parse", "HEAD")
            self.assertFalse(pathlib_probe(p, "new", new)["potential_NameError"])

    def test_merge_conflicts_and_missing_merge_base(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            run(p, "init", "-q")
            run(p, "config", "user.email", "test@example.invalid")
            run(p, "config", "user.name", "Tester")
            f = p / "tools/memory_tool.py"
            f.parent.mkdir()
            f.write_text("dispatch = 'base'\n")
            run(p, "add", ".")
            run(p, "commit", "-qm", "base")
            base = run(p, "rev-parse", "HEAD")
            run(p, "checkout", "-qb", "a")
            f.write_text("dispatch = 'read'\n")
            run(p, "commit", "-qam", "read")
            a = run(p, "rev-parse", "HEAD")
            run(p, "checkout", "-q", "-b", "b", base)
            f.write_text("dispatch = 'governance'\n")
            run(p, "commit", "-qam", "governance")
            b = run(p, "rev-parse", "HEAD")
            original = dict(HEADS)
            try:
                HEADS.update(read=a, chain=b)
                outcome = merge_probe(p, "read", "chain")
                self.assertEqual(outcome["status"], "CONFLICT")
                self.assertTrue(any("memory_tool.py" in x for x in outcome["conflicts"]))
                self.assertEqual(run(p, "rev-parse", "HEAD"), b)
            finally:
                HEADS.clear()
                HEADS.update(original)


if __name__ == "__main__":
    unittest.main()
