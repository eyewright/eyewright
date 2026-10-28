"""Phase 5: determinism check and live shadow run.

    python parity/shadow.py --determinism   # same question twice to Python
    python parity/shadow.py --shadow        # same question to Python and Rust

Both servers run against the real eyes (laya-serve, Ollama) using
examples/gate.json. If determinism fails, the shadow run proves nothing and
this script refuses to run it.
"""

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as R  # noqa: E402

CONFIG = R.ROOT / "examples" / "gate.json"
QUESTIONS = [
    ("The deployment is scheduled for Friday.", "Is the deployment scheduled for Friday?"),
    ("The Earth orbits the Sun.", "Is the statement true?"),
    ("Temperature is zero and the prompt is fixed.", "Will two runs agree?"),
    ("Paris is the capital of France.", "Is the statement true?"),
    ("The tests passed on the last run.", "Is the work ready to merge?"),
    ("No one has reviewed this code.", "Is the code ready to ship?"),
    ("The patch fixes the reported bug and adds a regression test.", "Is the patch complete?"),
    ("The user asked for a summary, not a rewrite.", "Did the agent follow the request?"),
]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(side, port):
    argv = (
        [sys.executable, str(R.PY_ENTRY), "serve"]
        if side == "py"
        else [str(R.RS_BIN), "serve"]
    ) + ["--config", str(CONFIG), "--port", str(port)]
    proc = subprocess.Popen(
        argv,
        cwd=str(R.ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"{side} exited early: {proc.stdout.read()[-800:]}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                if r.status == 200:
                    return proc
        except Exception:
            time.sleep(0.1)
    proc.kill()
    raise SystemExit(f"{side} never became ready")


def gate(port, state, question):
    body = json.dumps({"state": state, "question": question}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/gate",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def run(mode):
    py_port = free_port()
    py = start("py", py_port)
    rs = None
    try:
        if mode == "shadow":
            rs_port = free_port()
            rs = start("rs", rs_port)

        failed = 0
        for i, (state, question) in enumerate(QUESTIONS, 1):
            first = gate(py_port, state, question)
            port_b = py_port if mode == "determinism" else rs_port
            second = gate(port_b, state, question)
            same = R.canonical(json.dumps(first)) == R.canonical(json.dumps(second))
            label = "py==py" if mode == "determinism" else "py==rs"
            if not same:
                failed += 1
                print(f"FAIL q{i} ({label})  {state[:50]}")
                print(f"  first  {R.canonical(json.dumps(first))}")
                print(f"  second {R.canonical(json.dumps(second))}")
            else:
                decision = first.get("decision")
                print(f"ok   q{i}  p={first.get('p_done')}  {decision:<22} {label}")
        total = len(QUESTIONS)
        print(f"{mode.upper()} {total - failed}/{total}")
        return 1 if failed else 0
    finally:
        for proc in (py, rs):
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    mode = "shadow" if "--shadow" in sys.argv else "determinism"
    sys.exit(run(mode))
