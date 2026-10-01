import sys, os, tempfile, pathlib, traceback
sys.path.insert(0, os.getcwd())
from evals.postmortem.tests.test_postmortem_harness import _mk_db
from evals.postmortem.forensics import logcalls
d = pathlib.Path(tempfile.mkdtemp(dir=os.environ["HOME"]))
_mk_db(d / "state.db")
(d / "agent.log").write_text("2026-09-06 19:32:01,549 INFO [root] agent.conversation_loop: API call #1: model=m provider=nous in=500 out=7 total=507 latency=0.2s cache_state=no_field cache_scope=response\n", encoding="utf-8")
try:
    rc = logcalls.main(["--db", str(d / "state.db"), "--out", str(d / "out"), "--logs", str(d / "agent.log")])
    print("rc", rc)
except Exception as e:
    print("EXC", type(e).__name__, e)
