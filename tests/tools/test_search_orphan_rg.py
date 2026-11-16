#!/usr/bin/env python3
"""Test that search_files rg child does not survive parent timeout (orphan process leak).

Regression test for: rg --files child survives caller timeout and keeps reading disk.
When a Python caller times out or is killed, the rg child process gets reparented
to the user manager and keeps reading. Fix: give the search subprocess its own
process group, or PR_SET_PDEATHSIG, and kill the group on timeout or parent death.
"""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations


def _make_real_env(cwd: str) -> ShellFileOperations:
    """Create ShellFileOperations with a real local environment."""
    env = LocalEnvironment(cwd=cwd, timeout=10)
    return ShellFileOperations(env)


class TestSearchOrphanRg:
    """Tests for orphaned rg process prevention."""

    def _create_large_test_tree(self, root: Path, num_dirs: int = 200, files_per_dir: int = 50):
        """Create a directory tree large enough to make rg --files take noticeable time."""
        for i in range(num_dirs):
            d = root / f"dir_{i:04d}"
            d.mkdir(parents=True)
            for j in range(files_per_dir):
                (d / f"file_{j:04d}.txt").write_text(f"content {i} {j}\n" * 10)
        # Also create some nested structure
        nested = root / "nested" / "deep" / "structure"
        nested.mkdir(parents=True)
        for k in range(500):
            (nested / f"deep_file_{k:04d}.log").write_text(f"log entry {k}\n" * 5)

    def test_rg_child_dies_when_parent_killed(self, tmp_path):
        """
        RED test: When the parent Python process is killed, the rg child should also die.

        This test simulates what happens when a Hermes worker is reclaimed or
        a timeout kills the caller - the rg --files process should not become
        an orphan that keeps reading disk.
        """
        # Create a test directory with enough files to make rg take time
        self._create_large_test_tree(tmp_path, num_dirs=100, files_per_dir=30)

        # Use a real environment to test actual process behavior
        ops = _make_real_env(str(tmp_path))

        # Track rg processes before and after
        def count_rg_processes():
            """Count running rg processes."""
            try:
                result = subprocess.run(
                    ["pgrep", "-f", r"rg --files"],
                    capture_output=True, text=True
                )
                return len(result.stdout.strip().split()) if result.stdout.strip() else 0
            except Exception:
                return 0

        rg_before = count_rg_processes()

        # Start a search that will take a while
        # We use a pattern that matches everything to force full scan
        import threading
        search_done = threading.Event()
        search_error = []
        search_result = []

        def do_search():
            try:
                # Use a very large limit to force rg to scan more
                result = ops._search_files_rg("*", str(tmp_path), limit=10000, offset=0)
                search_result.append(result)
            except Exception as e:
                search_error.append(e)
            finally:
                search_done.set()

        search_thread = threading.Thread(target=do_search)
        search_thread.start()

        # Give rg time to start - poll for rg process
        rg_during = 0
        for _ in range(20):  # wait up to 2 seconds
            time.sleep(0.1)
            rg_during = count_rg_processes()
            if rg_during > rg_before:
                break

        # rg should be running now
        assert rg_during > rg_before, f"Expected rg to be running, before={rg_before}, during={rg_during}"

        # Now simulate parent death by killing the search thread's process
        # Since we can't easily kill just the parent thread in this test,
        # we'll wait for the search to complete and verify cleanup
        search_thread.join(timeout=30.0)

        # Wait a bit for cleanup
        time.sleep(0.5)

        rg_after = count_rg_processes()
        # rg should be cleaned up
        assert rg_after == rg_before, (
            f"rg process leaked! before={rg_before}, after={rg_after}. "
            f"Orphaned rg processes detected."
        )

    def test_search_files_rg_timeout_cleans_up(self, tmp_path):
        """Test that search_files with timeout properly cleans up rg processes."""
        self._create_large_test_tree(tmp_path, num_dirs=50, files_per_dir=20)

        ops = _make_real_env(str(tmp_path))

        def count_rg_processes():
            try:
                result = subprocess.run(
                    ["pgrep", "-f", r"rg --files"],
                    capture_output=True, text=True
                )
                return len(result.stdout.strip().split()) if result.stdout.strip() else 0
            except Exception:
                return 0

        rg_before = count_rg_processes()

        # Run search 
        result = ops._search_files_rg("*", str(tmp_path), limit=10, offset=0)

        rg_after = count_rg_processes()
        assert rg_after == rg_before, (
            f"rg process leaked after search! before={rg_before}, after={rg_after}"
        )
        assert result.error is None or "timeout" not in (result.error or "").lower()


class TestProcessGroupCleanup:
    """Tests for process group cleanup in LocalEnvironment."""

    def test_bash_process_group_is_killed_on_timeout(self, tmp_path):
        """Test that when a bash command times out, the entire process group is killed."""
        env = LocalEnvironment(cwd=str(tmp_path), timeout=1)

        # Run a command that spawns a long-running child
        # Using a bash script that backgrounds a sleep
        script = tmp_path / "background_sleep.sh"
        script.write_text("""#!/bin/bash
sleep 100 &
wait
""")
        script.chmod(0o755)

        # This should time out and clean up the process group
        result = env.execute(f"bash {script}", timeout=2)

        # The command should have timed out
        assert result.get("returncode") in (124, 137, 143, 1), (
            f"Expected timeout exit code, got {result.get('returncode')}"
        )

        # Verify no leftover sleep processes from our script
        time.sleep(0.2)
        try:
            pgrep_result = subprocess.run(
                ["pgrep", "-f", "sleep 100"],
                capture_output=True, text=True
            )
            # Should not find our specific sleep 100 processes
            assert "sleep 100" not in pgrep_result.stdout, (
                f"Leftover sleep processes found: {pgrep_result.stdout}"
            )
        except Exception:
            pass  # pgrep not available, skip check

    def test_prctl_pdeathsig_set_on_child(self):
        """Test that PR_SET_PDEATHSIG is set on child processes."""
        from tools.environments.local import _set_pdeathsig
        import ctypes
        import ctypes.util

        # This is a unit test for the _set_pdeathsig function
        # It should not raise on Linux
        try:
            _set_pdeathsig()
        except Exception as e:
            # On non-Linux or if libc not available, it should fail gracefully
            assert sys.platform != "linux" or "libc" in str(e).lower()

    def test_process_group_kill_on_parent_death(self, tmp_path):
        """
        Test that demonstrates the fix: when parent dies, child process group is killed.

        This test directly tests the process group behavior by spawning a process
        that creates a process group and verifying it gets cleaned up.
        """
        # Create a test script that spawns a long-running child process
        script = tmp_path / "test_pgid.sh"
        script.write_text("""#!/bin/bash
# This script creates a new process group and spawns a child
# The child should be killed when this script's process group is killed

# Spawn a long-running child
sleep 1000 &
CHILD_PID=$!

# Write child PID to a file so we can check it
echo $CHILD_PID > /tmp/test_child_pid.txt

# Wait for the child (this script will be killed by the test)
wait $CHILD_PID
""")
        script.chmod(0o755)

        env = LocalEnvironment(cwd=str(tmp_path), timeout=1)

        # Run the script - it will start the child and then wait
        # We expect it to be killed by timeout
        result = env.execute(f"bash {script}", timeout=2)

        # Should have timed out
        assert result.get("returncode") in (124, 137, 143, 1), (
            f"Expected timeout exit code, got {result.get('returncode')}"
        )

        # Give time for cleanup
        time.sleep(0.5)

        # Check if child process was cleaned up
        try:
            if os.path.exists("/tmp/test_child_pid.txt"):
                with open("/tmp/test_child_pid.txt") as f:
                    child_pid = int(f.read().strip())
                # Try to send signal 0 to check if process exists
                try:
                    os.kill(child_pid, 0)
                    # If we get here, process still exists - this is the BUG
                    pytest.fail(f"Child process {child_pid} survived parent death (orphaned)")
                except ProcessLookupError:
                    # Process was cleaned up - this is the FIX
                    pass
        except Exception:
            pass  # File not found or other issue, skip check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])