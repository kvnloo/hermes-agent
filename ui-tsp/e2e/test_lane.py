"""Behavioral checks for the test runner's safety and wire instrumentation."""
import importlib.util
import json
import os
from pathlib import Path
import pty
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tern_lane',HERE/'lane.py')
assert spec is not None and spec.loader is not None
lane=importlib.util.module_from_spec(spec)
spec.loader.exec_module(lane)


class LaneTests(unittest.TestCase):
    def test_gate_accepts_only_explicit_open_states(self):
        for applies,signed_in in [(False,False),(True,True)]:
            self.assertTrue(lane.gate_open({'gate':dict(phase='off',error=None,applies=applies,signed_in=signed_in)}))

    def test_gate_rejects_unknown_signed_out_and_incomplete(self):
        for gate in [None,[],{},dict(phase='off',applies=False),dict(phase='off',error=None,applies=True,signed_in=False),
                     dict(phase='signed-out',error=None,applies=True),dict(phase='off',error='error',applies=False),
                     dict(phase='off',error=None,applies=0)]:
            with self.subTest(gate=gate): self.assertFalse(lane.gate_open({'gate':gate}))

    def test_cleanup_stops_only_exact_owned_scope(self):
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as temporary:
            root=Path(temporary); socket=str(root/'owned.sock')
            owned=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],env={**os.environ,'TERN_DAEMON_SOCKET':socket})
            peer=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],env={**os.environ,'TERN_DAEMON_SOCKET':socket+'-peer'})
            runner=object.__new__(lane.Runner); runner.children=[]; runner.env={'TERN_DAEMON_SOCKET':socket}
            try:
                runner.stop(root)
                self.assertIsNotNone(owned.poll())
                self.assertIsNone(peer.poll())
                receipt=json.loads((root/'cleanup.json').read_text())
                self.assertIn(owned.pid,receipt['detached_signalled'])
                self.assertNotIn(peer.pid,receipt['detached_signalled'])
            finally:
                for child in [owned,peer]:
                    if child.poll() is None: child.terminate()
                    child.wait(timeout=5)

    def test_stdout_observer_preserves_real_bytes_and_callback(self):
        node=shutil.which('node')
        assert node is not None
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as temporary:
            root=Path(temporary)
            shutil.copyfile(HERE/'observe-stdout.mjs',root/'observe-stdout.mjs')
            (root/'manifest.json').write_text(json.dumps(dict(proof=str(root))))
            payload='\x1b]52;c;'+ 'YW5zd2Vy' +'\x07'
            program=f'process.stdout.write({json.dumps(payload)},()=>process.stderr.write("callback"))'
            result=subprocess.run([node,'--import',str(root/'observe-stdout.mjs'),'-e',program],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,payload.encode())
            self.assertEqual(result.stderr,b'callback')
            rows=[json.loads(s) for s in (root/'clipboard-osc52.jsonl').read_text().splitlines()]
            self.assertEqual([bytes.fromhex(r['hex']) for r in rows],[payload.encode()])

    def audit(self,late):
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as temporary:
            output=Path(temporary)/'audit.json'
            master,slave=pty.openpty()
            child=subprocess.Popen([sys.executable,str(HERE/'post_exit.py'),str(output)],stdin=slave,stdout=slave,stderr=slave)
            os.close(slave)
            try:
                if late:
                    time.sleep(.1); os.write(master,late)
                code=child.wait(timeout=3)
                self.assertEqual(json.loads(output.read_text())['hex'],late.hex())
                self.assertEqual(code,int(bool(late)))
            finally:
                if child.poll() is None: child.kill(); child.wait()
                os.close(master)

    def test_post_exit_zero_bytes(self): self.audit(b'')
    def test_post_exit_late_bytes_fail(self): self.audit(b'late-tsp-bytes')

    def test_gateway_allows_only_exact_readonly_context_slash(self):
        node = shutil.which('node')
        assert node is not None
        cases = [({'command':'context','session_id':'owned'}, True),
                 ({'command':'context --extra','session_id':'owned'}, False),
                 ({'command':'compress','session_id':'owned'}, False),
                 ({'command':'context','session_id':'owned','confirmed':True}, False),
                 ({'command':'context'}, False)]
        for params, allowed in cases:
            with self.subTest(params=params), tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as temporary:
                root = Path(temporary)
                shutil.copyfile(HERE/'gateway.mjs', root/'gateway.mjs')
                (root/'manifest.json').write_text(json.dumps(dict(root=str(root), python=sys.executable,
                    proof=str(root), record=str(root/'wire.jsonl'), gate=str(root/'gate.json'))))
                # An echo subprocess observes forwarding only; no product replies are fabricated.
                request = dict(jsonrpc='2.0', id=1, method='slash.exec', params=params)
                result = subprocess.run([node, str(root/'gateway.mjs'), '-c',
                    'import sys,json; [print(json.dumps({"observed":json.loads(line)}), flush=True) for line in sys.stdin]'],
                    input=json.dumps(request)+'\n', capture_output=True, text=True, timeout=10)
                rows = [json.loads(s) for s in (root/'wire.jsonl').read_text().splitlines()]
                self.assertEqual(result.returncode, 0 if allowed else 1, result.stderr)
                self.assertEqual(any(row['dir']=='denied' for row in rows), not allowed)
                self.assertEqual(bool(result.stdout), allowed)

    def test_unknown_journey_rejected_before_startup(self):
        result=subprocess.run([sys.executable,str(HERE/'lane.py'),str(HERE),'unknown-journey'],capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,2)
        self.assertIn('invalid choice',result.stderr)


if __name__=='__main__': unittest.main()
