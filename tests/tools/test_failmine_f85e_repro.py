"""failmine f85e62fa123e repro: an out-of-band write (terminal sed -i / execute_code
open().write) after read_file makes the next whole-file write_file refuse; a re-read
clears it. Not for upstream: documents designed behaviour on main."""
import json
import os
import subprocess
import tempfile
import time

from tools import file_state
from tools.file_tools import read_file_tool, write_file_tool


def test_out_of_band_shell_edit_blocks_then_reread_allows():
    file_state.get_registry().clear()
    d = tempfile.mkdtemp()
    p = os.path.join(d, "card.ts")
    with open(p, "w") as f:
        f.write("const a = 1\n")
    read_file_tool(p, task_id="t1")
    time.sleep(0.05)
    # the agent's own terminal call: invisible to the file-state registry
    subprocess.run(["sed", "-i", "s/1/2/", p], check=True)

    r = json.loads(write_file_tool(p, "const a = 3\n", task_id="t1"))
    assert r.get("stale_write_blocked") is True
    assert "modified since you last read it on disk" in r["error"]
    assert open(p).read() == "const a = 2\n"  # nothing clobbered

    read_file_tool(p, task_id="t1")
    r = json.loads(write_file_tool(p, "const a = 3\n", task_id="t1"))
    assert "error" not in r, r
    assert open(p).read() == "const a = 3\n"
