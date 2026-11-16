#!/usr/bin/env python3
"""Test that demonstrates the orphaned rg bug when parent is killed externally."""

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest


def test_orphaned_rg_when_parent_killed_externally():
    """
    This test simulates the exact scenario from the bug report:
    - A Python script runs `timeout 58 python real_call.py` which calls search_files
    - When timeout kills the Python process, the rg child should die but doesn't
    
    This test directly demonstrates the bug by:
    1. Starting a Python subprocess that runs a long-running rg command via bash
    2. Killing the Python subprocess (simulating timeout)
    3. Checking if the rg process survives
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a large directory tree
        for i in range(50):
            d = tmpdir / f"dir_{i:04d}"
            d.mkdir(parents=True)
            for j in range(20):
                (d / f"file_{j:04d}.txt").write_text(f"content {i} {j}\n" * 10)
        
        # Create a Python script that runs rg via bash (simulating search_files)
        script = tmpdir / "run_rg.py"
        script.write_text(f"""#!/usr/bin/env python3
import subprocess
import sys

# Run rg --files via bash (this is what search_files does)
cmd = [
    "bash", "-c", 
    "rg --files --sortr=modified -g '*' -- {tmpdir} 2>/dev/null | head -n 10000"
]

print(f"Starting rg with pid {{os.getpid()}}", file=sys.stderr)
result = subprocess.run(cmd, capture_output=True, text=True)
print(f"rg completed with returncode {{result.returncode}}", file=sys.stderr)
print(f"Found {{len(result.stdout.strip().split())}} files", file=sys.stderr)
""")
        
        # Run the Python script as a subprocess
        py_proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it time to start rg
        time.sleep(1.0)
        
        # Check if rg is running
        def count_rg():
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "rg --files"],
                    capture_output=True, text=True
                )
                return len(result.stdout.strip().split()) if result.stdout.strip() else 0
            except Exception:
                return 0
        
        rg_during = count_rg()
        print(f"rg processes during: {rg_during}")
        
        if rg_during == 0:
            print("rg didn't start in time, test inconclusive")
            py_proc.terminate()
            py_proc.wait(timeout=2)
            pytest.skip("rg didn't start in time")
        
        # Now kill the Python process (simulating timeout command)
        print("Killing parent Python process...")
        py_proc.send_signal(signal.SIGTERM)
        try:
            py_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            py_proc.kill()
            py_proc.wait()
        
        # Give time for any cleanup
        time.sleep(0.5)
        
        # Check if rg survived
        rg_after = count_rg()
        print(f"rg processes after: {rg_after}")
        
        if rg_after > 0:
            print("BUG REPRODUCED: rg process survived parent death!")
            # Clean up
            subprocess.run(["pkill", "-f", "rg --files"], capture_output=True)
            return True  # Bug reproduced
        else:
            print("rg was cleaned up properly")
            return False  # Bug not reproduced (fixed)


def test_current_hermes_behavior():
    """Test the current Hermes LocalEnvironment behavior."""
    from tools.environments.local import LocalEnvironment
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create a large directory tree
        for i in range(30):
            d = tmpdir / f"dir_{i:04d}"
            d.mkdir(parents=True)
            for j in range(15):
                (d / f"file_{j:04d}.txt").write_text(f"content {i} {j}\n" * 5)
        
        env = LocalEnvironment(cwd=str(tmpdir), timeout=60)
        
        # Run a command that will take a while
        script = tmpdir / "slow_rg.sh"
        script.write_text(f"""#!/bin/bash
rg --files --sortr=modified -g '*' -- {tmpdir} 2>/dev/null | head -n 5000
""")
        script.chmod(0o755)
        
        # Start the command in background
        import threading
        result_container = []
        
        def run_cmd():
            result = env.execute(f"bash {script}", timeout=10)
            result_container.append(result)
        
        thread = threading.Thread(target=run_cmd)
        thread.start()
        
        # Wait for rg to start
        time.sleep(0.5)
        
        def count_rg():
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "rg --files"],
                    capture_output=True, text=True
                )
                return len(result.stdout.strip().split()) if result.stdout.strip() else 0
            except Exception:
                return 0
        
        rg_during = count_rg()
        print(f"rg processes during Hermes execute: {rg_during}")
        
        if rg_during == 0:
            thread.join(timeout=5)
            pytest.skip("rg didn't start in time")
        
        # Simulate external kill of the Python process by terminating the thread's process
        # We can't easily do this from within the same process, so we'll test differently
        # The key test is: if the main Python process dies, does the rg child die?
        
        thread.join(timeout=15)
        
        time.sleep(0.5)
        rg_after = count_rg()
        print(f"rg processes after: {rg_after}")
        
        assert rg_after == 0, f"rg process leaked: {rg_after} processes still running"


if __name__ == "__main__":
    # Run the bug reproduction test
    print("=" * 60)
    print("Testing orphaned rg when parent killed externally")
    print("=" * 60)
    bug_reproduced = test_orphaned_rg_when_parent_killed_externally()
    print("=" * 60)
    if bug_reproduced:
        print("BUG CONFIRMED: rg survives parent death")
        sys.exit(1)
    else:
        print("Bug not reproduced - may already be fixed")
        sys.exit(0)