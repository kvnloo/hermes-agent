import tools, sys; print("tools from:", tools.__file__)
import threading, sys, time
from unittest.mock import patch
import tools.process_registry as prm
from tools.process_registry import ProcessSession, process_registry as reg
s = ProcessSession(id="proc_deadlock_probe", command="true", task_id="", notify_on_complete=True)
s.started_at = time.time()
reg._running[s.id] = s
done = threading.Event()
def run():
    with patch("tools.process_registry.save_completed_result", lambda session: None), \
         patch.object(reg, "_write_checkpoint", lambda: None):
        reg._finish_exited(s, 0)
    done.set()
t = threading.Thread(target=run, daemon=True); t.start()
ok = done.wait(5)
print("reader finished:", ok, "| queue size:", reg.completion_queue.qsize(), "| registry lock held:", reg._lock.locked())
sys.exit(0 if ok else 3)
