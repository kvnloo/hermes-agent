#!/usr/bin/env python3
"""Real non-Tern PTY: actual no-handshake 75, then actual launcher to actual Ink.

Only build-entry resolution is overridden so this never installs dependencies or
uses another checkout's bundled products. No UI/transport/exit is mocked.
"""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time


def selector_cases():
    """Environment-marker probes. These are NOT real SSH or multiplexer sessions."""
    return [
        ('tern-terminal', {'TERM_PROGRAM': 'tern'}, True),
        ('ordinary-terminal', {'TERM_PROGRAM': 'xterm-256color'}, False),
        ('ssh-marker-only', {'TERM_PROGRAM': 'xterm', 'SSH_CONNECTION': 'fixture-only'}, False),
        ('explicit-ssh-probe', {'TERM_PROGRAM': 'xterm', 'SSH_CONNECTION': 'fixture-only', 'HERMES_TERN': '1'}, True),
        ('tmux-marker-only', {'TERM_PROGRAM': 'tern', 'TMUX': '/fixture/tmux,0,0'}, False),
        ('screen-marker-only', {'TERM_PROGRAM': 'tern', 'STY': 'fixture-screen'}, False),
        ('zellij-marker-only', {'TERM_PROGRAM': 'tern', 'ZELLIJ': '0'}, False),
        ('explicit-multiplexer-probe', {'TERM_PROGRAM': 'tern', 'TMUX': '/fixture/tmux,0,0', 'HERMES_TERN': '1'}, True),
        ('explicit-opt-out', {'TERM_PROGRAM': 'tern', 'HERMES_TERN': '0'}, False),
    ]


def child(root, node, out):
    sys.path.insert(0, str(root))
    import hermes_cli.main_tui_launch as launch
    from hermes_cli.main import _tern_terminal_early

    # Real launch selection code, tested with explicit *synthetic* environment
    # values before launching the actual PTY/Ink path. Never claim real SSH.
    selection = []
    for name, hints, expected in selector_cases():
        early = _tern_terminal_early(hints)
        wanted = launch._tern_frontend_wanted(hints)
        selection.append(dict(name=name, hints=hints, early=early, wanted=wanted, expected=expected,
                              evidenceClass='environment-marker-only'))
    (out/'selector-matrix.json').write_text(json.dumps(selection, indent=2)+'\n')
    assert all(row['early'] is row['expected'] and row['wanted'] is row['expected'] for row in selection), selection
    launch._make_tsp_argv = lambda _root: ([node,str(root/'ui-tsp/dist/entry.js')],root/'ui-tsp')
    launch._make_tui_argv = lambda _root,_dev: ([node,str(root/'ui-tui/dist/entry.js')],root/'ui-tui')
    real_call = subprocess.call
    def observed(argv, **kwargs):
        with (out/'calls.jsonl').open('a') as log:
            log.write(json.dumps(dict(event='start',argv=argv))+'\n')
        code=real_call(argv,**kwargs)
        with (out/'calls.jsonl').open('a') as log:
            log.write(json.dumps(dict(event='exit',argv=argv,code=code))+'\n')
        return code
    launch.subprocess.call=observed
    launch._launch_tui()


def run_pty(argv, env, root, output, ink=False):
    master,slave=pty.openpty()
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',36,120,0,0))
    proc=subprocess.Popen(argv,cwd=root,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
    os.close(slave)
    data=bytearray(); start=time.monotonic(); sent=False; ready=False
    try:
        while time.monotonic()-start<60:
            readable,_,_=select.select([master],[],[],.1)
            if readable:
                try: chunk=os.read(master,65536)
                except OSError: break
                if not chunk: break
                data.extend(chunk)
            text=data.decode(errors='replace')
            if ink and 'hermes' in text.lower() and 'entry.js' not in text:
                ready=True
            # Readiness: actual Ink output and its own gateway startup; not just PID liveness.
            if ink and not sent and time.monotonic()-start>12 and len(data)>1000:
                ready=True; os.write(master,b'\x04'); sent=True
            if proc.poll() is not None: break
        if proc.poll() is None:
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: raise RuntimeError('PTY child did not exit after bounded quit')
        output.write_bytes(data)
        return dict(exit=proc.returncode,bytes=len(data),ink_painted=ready,quit_sent=sent)
    finally:
        output.write_bytes(data)
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait(timeout=5)
        os.close(master)


def run_non_tty(argv, env, root, output, timeout=20):
    """Probe the actual entry process with no terminal, keeping bounded bytes."""
    with output.open('wb') as capture:
        result = subprocess.run(argv, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                stdout=capture, stderr=subprocess.STDOUT, timeout=timeout,
                                check=False)
    return dict(exit=result.returncode, bytes=output.stat().st_size,
                evidenceClass='real-non-tty-process')


def main(root,node,out):
    out.mkdir(mode=0o700)
    home=out/'home'; home.mkdir(mode=0o700)
    env={k:os.environ[k] for k in ('PATH','LANG','TMPDIR','OPENUI_TELEMETRY_DISABLED','DO_NOT_TRACK') if k in os.environ}
    env.update(HOME=str(home),HERMES_HOME=str(home/'hermes'),HERMES_PYTHON=sys.executable,
        HERMES_PYTHON_SRC_ROOT=str(root),HERMES_NODE=node,HERMES_TUI_CWD=str(root),
        HERMES_TUI_SPLASH='0',TERM='xterm-256color',TERM_PROGRAM='xterm',HERMES_TERN='1',
        OPENAI_API_KEY='inert-e2e-not-a-credential',PYTHONPATH=str(root))
    Path(env['HERMES_HOME']).mkdir()
    (Path(env['HERMES_HOME'])/'config.yaml').write_text('model:\n  default: e2e-inert\n  provider: custom\n  base_url: http://127.0.0.1:9/v1\n  api_key: inert-e2e-not-a-credential\nauth:\n  adopt_external_logins: false\ntelemetry:\n  shared_metrics:\n    enabled: false\n    send: false\n')
    build=subprocess.run([node,str(root/'scripts/build/tui.mjs')],cwd=root,env=env,capture_output=True,text=True,timeout=120)
    (out/'build.log').write_text(build.stdout+build.stderr)
    assert build.returncode==0,'Ink build failed'
    entry=[node,str(root/'ui-tsp/dist/entry.js')]
    no_tsp=run_pty(entry,env,root,out/'no-tsp.pty')
    assert no_tsp['exit']==75,no_tsp
    non_tty=run_non_tty(entry,env,root,out/'non-tty.out')
    assert non_tty['exit']==75,non_tty

    # The subprocesses below each have a real PTY, but only simulated SSH/mux
    # ENVIRONMENT MARKERS. They assert fail-closed probing, not transport pass-through.
    marker_probes=[]
    for name, hints in [
        ('ssh-marker', {'TERM_PROGRAM':'xterm', 'SSH_CONNECTION':'fixture-only'}),
        ('tmux-marker', {'TERM_PROGRAM':'tern', 'TMUX':'/fixture/tmux,0,0'}),
        ('screen-marker', {'TERM_PROGRAM':'tern', 'STY':'fixture-screen'}),
        ('zellij-marker', {'TERM_PROGRAM':'tern', 'ZELLIJ':'0'}),
    ]:
        probe_env=dict(env,**hints,HERMES_TERN='1')
        result=run_pty(entry,probe_env,root,out/f'{name}.pty')
        assert result['exit']==75,(name,result)
        marker_probes.append(dict(name=name,**result,evidenceClass='real-PTY + environment-marker-only'))
    ink=run_pty([sys.executable,__file__,'--child',str(root),node,str(out)],env,root,out/'launcher.pty',ink=True)
    calls=[json.loads(s) for s in (out/'calls.jsonl').read_text().splitlines()]
    exits=[x for x in calls if x['event']=='exit']
    assert len(exits)==2 and exits[0]['code']==75, calls
    assert 'ui-tsp/dist/entry.js' in exits[0]['argv'][1],calls
    assert 'ui-tui/dist/entry.js' in exits[1]['argv'][1],calls
    assert exits[1]['code'] in (0,130) and ink['ink_painted'],ink
    selection=json.loads((out/'selector-matrix.json').read_text())
    dump=dict(evidenceClass='real-PTY-launcher (prebuilt entry resolution)',no_tsp=no_tsp,
              non_tty=non_tty,marker_probes=marker_probes,selector_matrix=selection,
              actual_ssh='not-run',actual_multiplexer='not-run',native_window='not-run',
              ink=ink,calls=calls)
    (out/'result.json').write_text(json.dumps(dump,indent=2)+'\n')
    print(json.dumps(dump,indent=2))


if __name__=='__main__':
    if sys.argv[1]=='--child': child(Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4]))
    else: main(Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]))
