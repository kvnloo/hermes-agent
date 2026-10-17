#!/usr/bin/env python3
"""Owned Tern/Hermes feature runner. Never connects to an ambient daemon/display."""
import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

SOURCE = Path(__file__).resolve().parent
JOURNEYS = ('smoke', 'settings', 'file-links', 'answer-copy', 'todo-hud', 'shortcuts', 'ink-fallback', 'openui')


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def gate_open(state):
    gate = state.get('gate')
    if not isinstance(gate, dict):
        return False
    return gate.get('phase') == 'off' and 'error' in gate and gate['error'] is None and (
        gate.get('applies') is False or (gate.get('applies') is True and gate.get('signed_in') is True))


class Runner:
    def __init__(self, args):
        self.args = args
        self.root = args.worktree.resolve(strict=True)
        self.head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()
        self.out = args.receipts / f'{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{self.head[:10]}'
        self.out.mkdir(parents=True, mode=0o700, exist_ok=False)
        self.scratch = Path(tempfile.mkdtemp(prefix='tern-e2e-', dir=os.environ['TMPDIR'])).resolve()
        self.results = []
        self.node = str(args.node.resolve(strict=True))
        # Do not resolve Python: its venv executable spelling is significant.
        self.python = str(args.python.absolute())
        self.base_env = {k:os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'TZ') if k in os.environ}
        self.base_env.update(PATH=str(Path(self.node).parent)+':'+self.base_env.get('PATH','/usr/bin:/bin'),
                             TERM='xterm-256color', SHELL='/bin/bash', TMPDIR=str(self.scratch),
                             OPENUI_TELEMETRY_DISABLED='1', DO_NOT_TRACK='1')
        dump(self.out/'source.json', dict(head=self.head, worktree=str(self.root), harness=str(SOURCE),
             harness_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip(),
             harness_dirty=subprocess.check_output(['git','status','--porcelain'],cwd=SOURCE,text=True),
             dirty=subprocess.check_output(['git','status','--porcelain'],cwd=self.root,text=True),
             command=sys.argv, model_calls_allowed=False, scratch=str(self.scratch)))

    def command(self, argv, directory, env, log, timeout=60, check=True):
        with (self.out/'commands.jsonl').open('a') as f:
            f.write(json.dumps(dict(argv=list(map(str,argv)),cwd=str(directory),log=str(log)))+'\n')
        result = subprocess.run(list(map(str,argv)), cwd=directory, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout, text=True)
        log.write_text(result.stdout)
        if check and result.returncode:
            raise RuntimeError(f'command exit {result.returncode}: {argv}; log={log}')
        return result

    def ctl(self, lane, scenario, input_action=False):
        def call(cmd):
            log = lane/'control.jsonl'
            result = subprocess.run(['tern','ctl','--control',str(self.port),cmd],env=self.env,
                                    capture_output=True,text=True,timeout=30)
            with log.open('a') as f: f.write(json.dumps(dict(command=cmd,code=result.returncode,stdout=result.stdout,stderr=result.stderr))+'\n')
            value = json.loads(result.stdout)
            if result.returncode or value.get('ok') is not True: raise RuntimeError(f'control failed: {cmd}: {value}')
            return value
        if input_action and not gate_open(call('state')): raise RuntimeError('native gate blocks input')
        value = call(scenario)
        if input_action and not gate_open(call('state')): raise RuntimeError('gate changed after input; do not retry')
        return value

    def process(self, argv, lane, name):
        log = lane/f'{name}.log'
        with log.open('w') as f:
            child = subprocess.Popen(list(map(str,argv)),cwd=lane,env=self.env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
        self.children.append(child)
        with (self.out/'commands.jsonl').open('a') as f:
            f.write(json.dumps(dict(argv=list(map(str,argv)),pid=child.pid,cwd=str(lane),log=str(log)))+'\n')
        return child

    def stop(self, lane):
        for child in reversed(self.children):
            if child.poll() is None:
                try: os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL); child.wait(timeout=5)
        # Tern auto-spawns a detached daemon. Match its exact owned socket environment,
        # never process names or a host-wide pkill. Re-check PID start time before kill.
        found = []
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit(): continue
            try:
                stat = (proc/'stat').read_text().split()[21]
                env = (proc/'environ').read_bytes().split(b'\0')
                owned_socket = f'TERN_DAEMON_SOCKET={self.env["TERN_DAEMON_SOCKET"]}'.encode() in env
                owned_home = f'HERMES_HOME={lane / "proof/hermes-home"}'.encode() in env
                if not (owned_socket or owned_home): continue
                pid = int(proc.name)
                if pid == os.getpid(): continue
                if (proc/'stat').read_text().split()[21] == stat:
                    os.kill(pid,signal.SIGTERM); found.append(pid)
            except (FileNotFoundError, ProcessLookupError, PermissionError): continue
        time.sleep(.2)
        survivors = []
        for pid in found:
            proc=Path('/proc')/str(pid)
            try:
                env=(proc/'environ').read_bytes().split(b'\0')
                if f'TERN_DAEMON_SOCKET={self.env["TERN_DAEMON_SOCKET"]}'.encode() in env or f'HERMES_HOME={lane / "proof/hermes-home"}'.encode() in env:
                    os.kill(pid,signal.SIGKILL)
                    survivors.append(pid)
            except (FileNotFoundError,ProcessLookupError,PermissionError): continue
        dump(lane/'cleanup.json',dict(supervised=[dict(pid=p.pid,exit=p.poll()) for p in self.children],detached_signalled=found,kill_required=survivors))

    def isolation(self, lane, mode):
        lane.mkdir(mode=0o700)
        self.children=[]
        run = self.scratch/str(len(self.results))
        run.mkdir(mode=0o700)
        for name in ('home','config','data','state','cache','run','logs','shots'):
            (run/name).mkdir(mode=0o700)
        (run/'config/plugins').mkdir(mode=0o700)
        self.env=dict(self.base_env,HOME=str(run/'home'),XDG_CONFIG_HOME=str(run/'config'),
            XDG_DATA_HOME=str(run/'data'),XDG_STATE_HOME=str(run/'state'),XDG_CACHE_HOME=str(run/'cache'),
            XDG_RUNTIME_DIR=str(run/'run'),TERN_CONFIG_DIR=str(run/'config'),TERN_DAEMON_SOCKET=str(run/'daemon.sock'),
            STENCIL_LOG_DIR=str(lane/'logs'))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); self.port=sock.getsockname()[1]
        plugin=self.command(['tern','plugin','dir'],lane,self.env,lane/'plugin-dir.log').stdout.strip()
        if not Path(plugin).resolve().is_relative_to(run): raise RuntimeError(f'plugin path escaped owned runtime: {plugin}')
        if mode == 'native-window':
            self.env.update(WLR_BACKENDS='headless',WLR_RENDERER='gles2',WLR_HEADLESS_OUTPUTS='1',LD_LIBRARY_PATH=self.args.sway_lib)
            config=run/'sway.conf'; config.write_text('output * resolution 1800x1100\n')
            child=self.process([self.args.sway,'--config',config],lane,'sway')
            sockets=[]
            for _ in range(100):
                sockets=[p for p in (run/'run').glob('wayland-*') if p.is_socket()]
                if sockets: break
                if child.poll() is not None: raise RuntimeError('Sway exited')
                time.sleep(.1)
            if not sockets: raise RuntimeError('private compositor socket timed out')
            self.env['WAYLAND_DISPLAY']=sockets[0].name
        else:
            self.env['WAYLAND_DISPLAY']='wayland-e2e-headless-no-display'
        dump(lane/'isolation.json',dict(proof=str(lane/'proof'),runtime=self.env['XDG_RUNTIME_DIR'],
            display=self.env['WAYLAND_DISPLAY'],config=self.env['TERN_CONFIG_DIR'],daemon=self.env['TERN_DAEMON_SOCKET'],
            evidenceClass=mode,shots=str(run/'shots')))
        argv=['tern','--control',str(self.port),str(lane)] if mode == 'native-window' else ['tern','serve','--control',str(self.port),'--out',str(run/'shots'),str(lane)]
        child=self.process(argv,lane,'tern')
        for _ in range(100):
            try:
                state=self.ctl(lane,'state'); break
            except (ConnectionError,subprocess.SubprocessError,ValueError,RuntimeError):
                if child.poll() is not None: raise RuntimeError('Tern exited before control ready')
                time.sleep(.1)
        else: raise RuntimeError('Tern control timed out')
        deadline=time.monotonic()+8
        while state.get('gate',{}).get('phase')=='reading' and time.monotonic()<deadline:
            time.sleep(.2); state=self.ctl(lane,'state')
        dump(lane/'startup-state.json',state)
        return state

    def prepare(self,lane):
        proof=lane/'proof'
        args=[self.node,SOURCE/'run.mjs','prepare','--root',self.root,'--entry',self.root/'ui-tsp/dist/entry.js',
              '--control',str(self.port),'--pane','0','--proof-dir',proof,'--python',self.python,'--framework-root',self.args.framework]
        self.command(args,lane,self.env,lane/'prepare.log')
        m=json.loads((proof/'manifest.json').read_text())
        state=self.ctl(lane,'state')
        assert str(state['focused']['id'])==m['pane'] and state['focused']['busy'] is False
        assert not state['focused']['running']
        command=f'cd {shlex_quote(str(self.root))} && {shlex_quote(self.node)} {shlex_quote(m["launch"])}'
        self.ctl(lane,'run '+json.dumps(command),True)
        return m

    def feature(self,journey,mode):
        lane=self.out/f'{mode}-{journey}'
        result=dict(journey=journey,evidenceClass=mode,status='fail')
        try:
            state=self.isolation(lane,mode)
            if not gate_open(state):
                result.update(status='blocked',reason='isolated Tern account gate: '+state['gate']['phase'])
                if mode=='native-window':
                    self.ctl(lane,'wait 1000')
                    dump(lane/'gate-tree.json',self.ctl(lane,'tree'))
                    dump(lane/'gate-post-wait-state.json',self.ctl(lane,'state'))
                    self.command(['grim','-o','HEADLESS-1',lane/'gate-diagnostic.png'],lane,self.env,lane/'grim.log')
                return result
            m=self.prepare(lane)
            time.sleep(.3)
            self.command([self.node,Path(m['project'])/'features.ts',Path(m['proof'])/'manifest.json',journey],
                         lane,self.env,lane/'features.log',timeout=600)
            steps=json.loads((Path(m['proof'])/'steps.json').read_text())
            result.update(status='blocked' if any(s['status']=='blocked' for s in steps['results']) else 'pass',steps=steps)
            if journey=='settings' and mode=='native-window':
                self.ctl(lane,'key escape',True)
                suite_args=[self.node,SOURCE/'run.mjs','run','--root',self.root,'--entry',m['entry'],
                    '--control',str(self.port),'--pane',m['pane'],'--proof-dir',m['proof'],'--python',self.python,'--framework-root',self.args.framework]
                self.command(suite_args,lane,self.env,lane/'full-settings.log',timeout=7200)
                result['full_settings_suite']='all ten original serial cases executed; framework report retained'
            if journey=='smoke':
                deadline=time.monotonic()+10
                while time.monotonic()<deadline:
                    state=self.ctl(lane,'state')
                    if not state['focused']['running'] and state['focused']['busy'] is False: break
                    time.sleep(.1)
                else: raise RuntimeError('Hermes did not return to idle shell')
                marker=lane/'shell-readback.txt'
                self.ctl(lane,'run '+json.dumps(f"printf '%s' E2E_SHELL_OK > {shlex_quote(str(marker))}"),True)
                deadline=time.monotonic()+5
                while not marker.exists() and time.monotonic()<deadline: time.sleep(.1)
                assert marker.read_text()=='E2E_SHELL_OK'
                # A successful command alone cannot prove absence of raw leaked bytes.
                result['clean_quit']='shell readback passed; pending-byte audit in launch wrapper'
                pending=Path(m['proof'])/'post-exit-bytes.json'
                assert pending.exists(), 'post-exit byte audit missing'
                audit=json.loads(pending.read_text()); assert audit['hex']=='',audit
                result['post_exit_bytes']=0
            if journey=='file-links':
                shot=self.ctl(lane,'shot opened-read-link')
                source=Path(shot['png']).resolve()
                assert source.is_relative_to(Path(m['shots']).resolve()) or source.is_relative_to(lane/'target/shots'), 'shot escaped private output'
                shutil.copyfile(source,lane/'opened-read-link.control.png')
                shutil.copyfile(shot['layout'],lane/'opened-read-link.layout.json')
                if mode=='native-window':
                    self.command(['grim','-o','HEADLESS-1',lane/'opened-read-link.native.png'],lane,self.env,lane/'grim-file.log')
                result['artifact_capture']='whole-window control shot; native PNG separately named when available'
        except Exception as error:
            result.update(status='fail',error=str(error))
            steps_path=lane/'proof/steps.json'
            if steps_path.exists(): result['steps']=json.loads(steps_path.read_text())
            (lane/'error.txt').write_text(str(error)+'\n')
        finally:
            if hasattr(self,'children'): self.stop(lane)
            self.results.append(result); dump(self.out/'summary.json',self.results)
        return result

    def run(self):
        self.command([self.node,self.root/'ui-tsp/scripts/build.mjs'],self.root,self.base_env,self.out/'build.log',timeout=120)
        requested=self.args.journeys
        native=[j for j in requested if j!='ink-fallback']
        if native:
            first=self.feature(native[0],'native-window')
            if first['status']=='blocked':
                for journey in native[1:]:
                    self.results.append(dict(journey=journey,evidenceClass='native-window',status='blocked',reason=first['reason'],gate_receipt=f'native-window-{native[0]}/startup-state.json'))
                # All ten full native Settings cases remain blocked, not narrowed or green.
                cases=re.findall(r"^  test\('([^']+)'", (SOURCE/'native-settings.e2e.ts').read_text(), re.MULTILINE)
                assert len(cases)==10, 'Full native Settings case inventory changed; review acceptance before running'
                dump(self.out/'full-settings-suite.json',dict(cases=[dict(name=name,status='blocked',reason=first['reason']) for name in cases],status='blocked',source='ui-tsp/e2e/native-settings.e2e.ts'))
                for journey in native: self.feature(journey,'tern-serve')
            else:
                for journey in native[1:]: self.feature(journey,'native-window')
        if 'ink-fallback' in requested:
            result=self.command([self.python,SOURCE/'ink_fallback.py',self.root,self.node,self.out/'ink-fallback'],self.root,self.base_env,self.out/'ink-fallback.log',timeout=180,check=False)
            self.results.append(dict(journey='ink-fallback',status='pass' if result.returncode==0 else 'fail',evidenceClass='real-PTY-launcher (prebuilt entry resolution)'))
        dump(self.out/'summary.json',self.results)
        print(json.dumps(dict(receipt=str(self.out),results=self.results),indent=2))
        return 1 if any(r['status']=='fail' for r in self.results) else 2 if any(r['status']=='blocked' for r in self.results) else 0


def shlex_quote(value):
    import shlex
    return shlex.quote(value)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('worktree',type=Path)
    p.add_argument('journeys',nargs='*',choices=JOURNEYS)
    p.add_argument('--receipts',type=Path,default=Path('/mnt/zer0models/project-artifacts/hermes-tern-e2e'))
    p.add_argument('--node',type=Path,default=Path(shutil.which('node') or 'node'))
    p.add_argument('--python',type=Path,default=Path('/workspace/hermes-home/hermes-agent/venv/bin/python'))
    p.add_argument('--framework',type=Path,default=Path('/mnt/zer0models/hermes-wt/e2e'))
    p.add_argument('--sway',default='/home/kvn/.local/opt/sway-nested/bin/sway')
    p.add_argument('--sway-lib',default='/home/kvn/.local/opt/sway-nested/lib')
    args=p.parse_args()
    if not args.journeys: args.journeys=list(JOURNEYS)
    return Runner(args).run()


if __name__=='__main__':
    raise SystemExit(main())
