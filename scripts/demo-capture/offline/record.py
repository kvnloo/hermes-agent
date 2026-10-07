#!/usr/bin/env python3
"""Record a real Hermes session in a headless Tern, as the protocol stream it sent.

    record.py NAME --prompt "..." [--model ID --provider NAME] [--cwd DIR] [--design kerykeion]
              [--size 1280x720] [--timeout 300] [--beside "COMMAND"]

With --beside "COMMAND" the window is split first and a real shell is recorded next to the session
(NAME.shell.jsonl: what its pty printed, with times), for render.py to print into the pane beside.

A headless Tern (`tern serve`, own config, daemon and HOME under $DEMO_STATE) runs the real
frontend on the real gateway with TERN_TSP_RECORD set, so every message Hermes sends Tern is
written to $DEMO_REC/NAME.jsonl with its wall-clock time. The prompt is typed a key at a time.
Nothing is screen-captured: render.py replays the stream into Tern's offscreen renderer.
"""
import argparse
import base64
import fcntl
import json
import os
import pty
import random
import signal
import struct
import subprocess
import sys
import termios
import threading
import time

here = os.path.dirname(os.path.abspath(__file__))
repo = os.path.abspath(os.path.join(here, "../../.."))
state = os.environ.get("DEMO_STATE", "/tmp/hermes-demo-capture")
rec = os.environ.get("DEMO_REC", os.path.join(state, "rec"))

parser = argparse.ArgumentParser()
parser.add_argument("name")
parser.add_argument("--prompt", default="")
parser.add_argument("--model", default=os.environ.get("DEMO_HERMES_MODEL", "openrouter/free"))
parser.add_argument("--provider", default=os.environ.get("DEMO_HERMES_PROVIDER", "openrouter"))
parser.add_argument("--hermes-home", default=os.environ.get("DEMO_HERMES_HOME", os.path.join(state, "hermes-home")))
parser.add_argument("--cwd", default=os.environ.get("DEMO_HERMES_CWD", os.path.join(state, "home/code/courier")))
parser.add_argument("--design", default="kerykeion")
parser.add_argument("--splash-fps", default="120")
parser.add_argument("--size", default="1280x720")
parser.add_argument("--timeout", type=float, default=300)
parser.add_argument("--hold", type=float, default=2.5, help="seconds to keep recording after the turn ends")
parser.add_argument("--seed", type=int, default=7)
parser.add_argument("--key-from", help="a dotenv file to take OPENROUTER_API_KEY from, for a Hermes home that has no credentials of its own")
parser.add_argument("--beside", help="also record a real shell beside the session: this command line, typed into zsh in a pty")
args = parser.parse_args()

os.makedirs(rec, exist_ok=True)
take = os.path.join(rec, args.name)
sock = os.path.join(rec, "rec.sock")
width, height = (int(v) for v in args.size.split("x"))
clean = {k: v for k, v in os.environ.items() if not k.startswith("TERN_")}
clean.update(HOME=os.path.join(state, "home"), TERN_CONFIG_DIR=state, TERN_DAEMON_SOCKET=os.path.join(rec, "daemon.sock"))


def ctl(*words, check=True):
    out = subprocess.run(["tern", "ctl", "--control", sock, *words], capture_output=True, text=True).stdout
    reply = json.loads(out) if out.strip().startswith("{") else {"ok": False, "error": out.strip()}
    if check and not reply.get("ok"):
        sys.exit(f"record: `{' '.join(words)}` failed: {reply.get('error')}")
    return reply


def quoted(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def shown(selector):
    nodes = ctl("tree", selector, check=False).get("nodes") or []
    return nodes[0].get("text", "") if nodes else None


def sent(text):
    """Whether Hermes has sent `text` to Tern yet (the DOM only holds what is on screen)."""
    try:
        with open(take + ".jsonl") as stream:
            return any(text in line for line in stream if '"dir":"out"' in line)
    except OSError:
        return False


class Shell:
    """zsh in a pty of the pane's size; everything it prints is kept with its wall-clock time."""

    def __init__(self, path, cols, rows, cwd):
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
            os.chdir(cwd)
            env = {
                "HOME": os.path.expanduser("~"), "LANG": "en_US.UTF-8", "TERM": "xterm-256color",
                "PATH": os.path.expanduser("~/.local/bin") + ":/usr/local/bin:/usr/bin:/bin",
                "PROMPT": "%B%F{blue}%1~%f%b ❯ ", "PYTHONDONTWRITEBYTECODE": "1",
            }
            os.execvpe("zsh", ["zsh", "-f"], env)
        self.log = open(path, "w")
        threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        while True:
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                return
            if not data:
                return
            self.log.write(json.dumps({"t": round(time.time() * 1000), "d": base64.b64encode(data).decode()}) + "\n")
            self.log.flush()

    def type(self, text, rng):
        for char in text:
            os.write(self.fd, char.encode())
            time.sleep(0.04 + rng.random() * 0.06)
        time.sleep(0.5)
        os.write(self.fd, b"\r")

    def close(self):
        try:
            os.killpg(os.getpgid(self.pid), signal.SIGHUP)
        except OSError:
            pass


for stale in (sock, take + ".jsonl", take + ".shell.jsonl"):
    if os.path.exists(stale):
        os.remove(stale)

serve = subprocess.Popen(
    ["tern", "serve", "--control", sock, "--out", os.path.join(rec, "shots")],
    env=clean, stdout=open(take + ".tern.log", "w"), stderr=subprocess.STDOUT, start_new_session=True,
)
deadline = time.time() + 15
while not os.path.exists(sock):
    if time.time() > deadline:
        sys.exit("record: the headless Tern did not start")
    time.sleep(0.1)
time.sleep(0.5)

marks = {}
try:
    ctl("size", str(width), str(height))
    ctl("appearance", "dark")
    time.sleep(0.5)

    # The session itself: the frontend this checkout built, on the gateway of the chosen Hermes home.
    script = take + ".sh"
    # The key is read when the session starts; this script never holds or writes its value.
    key = ""
    if args.key_from:
        dotenv = os.path.expanduser(args.key_from)
        key = "export OPENROUTER_API_KEY=\"$(sed -n 's/^OPENROUTER_API_KEY=//p' '" + dotenv + "' | tail -1 | tr -d '\\042\\047')\""
    with open(script, "w") as out:
        out.write(f"""#!/bin/sh
echo $$ > "{take}.pid"
cd "{repo}"
export HERMES_TERN=1 TERM_PROGRAM=tern HERMES_PYTHON_SRC_ROOT="{repo}"
export HERMES_PYTHON="{os.environ.get('HERMES_PYTHON', '/workspace/hermes-home/hermes-agent/venv/bin/python')}"
export HERMES_HOME="{args.hermes_home}"
export HERMES_TUI_SPLASH="{args.design}" HERMES_TUI_SPLASH_FPS="{args.splash_fps}"
export HERMES_MODEL="{args.model}" HERMES_INFERENCE_MODEL="{args.model}"
export HERMES_TUI_PROVIDER="{args.provider}" HERMES_INFERENCE_PROVIDER="{args.provider}"
export HERMES_TUI_CWD="{args.cwd}"
export TERN_TSP_RECORD="{take}.jsonl"
{key}
# The stage's HOME is not yours: keep your Python's user packages (pytest) reachable for the agent's shell.
export PYTHONUSERBASE="{os.path.expanduser('~/.local')}" PYTHONDONTWRITEBYTECODE=1 PATH="{os.path.expanduser('~/.local/bin')}:$PATH"
unset TMUX STY ZELLIJ
exec node "{repo}/ui-tsp/dist/entry.js" 2> "{take}.err"
""")
    os.chmod(script, 0o755)

    marks["run"] = time.time()
    ctl("run", quoted(script))

    # Any key skips the splash, so nothing is typed until the composer is on screen.
    deadline = time.time() + 60
    while shown(".sf-editor") is None:
        if time.time() > deadline:
            sys.exit(f"record: no composer after 60 s (see {take}.err)")
        time.sleep(0.25)
    # The composer exists under the splash: wait for the splash's own surface to go.
    while shown("[data-role='hermes.splash']") is not None:
        if time.time() > deadline:
            sys.exit("record: the splash never handed off")
        time.sleep(0.2)
    marks["chrome"] = time.time()
    pane = ctl("state")["panes"][0]
    time.sleep(1.6)

    shell = None
    beside = None
    rng = random.Random(args.seed)
    if args.beside:
        ctl("split", "right")
        time.sleep(1.0)
        now = ctl("state")
        right = next(p for p in now["panes"] if p["id"] == now["focused"]["id"])
        pane = next(p for p in now["panes"] if p["id"] != right["id"])
        beside = {"cols": right["cols"], "rows": right["rows"], "command": args.beside}
        ctl("focus", "left")
        marks["shell"] = time.time()
        shell = Shell(take + ".shell.jsonl", right["cols"], right["rows"], args.cwd)
        time.sleep(1.2)
        shell.type(args.beside, rng)
        time.sleep(3.0)

    if args.prompt:
        marks["type"] = time.time()
        for char in args.prompt:
            ctl("type", quoted(char))
            time.sleep(0.035 + rng.random() * 0.06 + (0.05 if char == " " else 0) + (0.14 if char in ",.;:?!" else 0))
        time.sleep(0.7)
        marks["enter"] = time.time()
        ctl("key", "enter")

        deadline = time.time() + args.timeout
        while not sent(" this turn"):
            if time.time() > deadline:
                print("record: the turn did not finish in time; keeping what was recorded", file=sys.stderr)
                break
            time.sleep(0.5)
        marks["done"] = time.time()
    time.sleep(args.hold)
    marks["end"] = time.time()
    text = shown(".sf-main") or ""
finally:
    if "shell" in dir() and shell:
        shell.close()
    try:
        os.kill(int(open(take + ".pid").read()), signal.SIGTERM)
    except (OSError, ValueError):
        pass
    time.sleep(0.4)
    ctl("quit", check=False)
    try:
        serve.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(serve.pid, signal.SIGTERM)

lines = sum(1 for _ in open(take + ".jsonl")) if os.path.exists(take + ".jsonl") else 0
meta = {
    "cols": pane["cols"], "rows": pane["rows"], "cwd": args.cwd, "design": args.design, "height": height,
    "marks_ms": {k: round(v * 1000) for k, v in marks.items()}, "messages": lines, "model": args.model,
    "prompt": args.prompt, "provider": args.provider, "width": width,
}
if beside:
    meta["beside"] = beside
json.dump(meta, open(take + ".meta.json", "w"), indent=1)
turn = marks.get("done", 0) - marks.get("enter", 0)
print(f"record: {take}.jsonl  {lines} messages, pane {pane['cols']}x{pane['rows']}, turn {turn:.1f} s")
print("record: transcript: " + " ".join(text.split())[:700])
