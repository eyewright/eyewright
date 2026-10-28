"""Parity harness for `serve`: Python HTTP server vs Rust HTTP server.

Each side gets its own stub engine and its own port, runs the same request
script, and the results are compared pairwise (status, canonical JSON body,
Content-Type). Tokens, the body cap, deep health and the error paths are all
exercised.
"""

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as R  # noqa: E402

ROOT = R.ROOT
TOKEN = "parity-token"
MAX_BODY = 512
SCRIPT = {
    "p": [
        0.9,
        {"choice": "b", "probabilities": {"a": 0.1, "b": 0.9}, "confidence": 0.9},
    ]
}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_ready(port, proc, timeout=20.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise SystemExit(f"server exited early ({proc.returncode}): {out}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise SystemExit(f"server on {port} never became ready")


def call(port, method, path, body=None, token=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode(), r.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), e.headers.get("Content-Type")


def requests():
    gate = json.dumps({"state": "s", "question": "q"}).encode()
    ask = json.dumps({"state": "s", "question": "q", "choices": {"a": "x", "b": "y"}}).encode()
    return [
        ("health", "GET", "/health", None, False),
        ("root", "GET", "/", None, False),
        ("not-found", "GET", "/nope", None, False),
        ("deep-health", "GET", "/health/deep", None, True),
        ("deep-unauthorized", "GET", "/health/deep", None, False),
        ("gate", "POST", "/v1/gate", gate, True),
        ("gate-unauthorized", "POST", "/v1/gate", gate, False),
        ("ask", "POST", "/v1/ask", ask, True),
        ("gate-invalid-json", "POST", "/v1/gate", b"{not json", True),
        ("gate-too-large", "POST", "/v1/gate", json.dumps({"state": "x" * 700}).encode(), True),
        ("post-not-found", "POST", "/nope", b"{}", True),
    ]


def run_side(side, tmpdir):
    stub, stub_port = R.start_stub(SCRIPT, tmpdir / "stub.jsonl")
    port = free_port()
    cfg = json.loads(json.dumps(R.BASE_CONFIG))
    raw = json.dumps(cfg).replace("{STUB}", f"http://127.0.0.1:{stub_port}")
    cfg_path = tmpdir / "config.json"
    cfg_path.write_text(raw, encoding="utf-8")

    argv = (
        [sys.executable, str(R.PY_ENTRY), "serve"]
        if side == "py"
        else [str(R.RS_BIN), "serve"]
    ) + [
        "--config",
        str(cfg_path),
        "--port",
        str(port),
        "--token",
        TOKEN,
        "--max-body",
        str(MAX_BODY),
    ]
    proc = subprocess.Popen(
        argv,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_ready(port, proc)
        out = []
        for _, method, path, body, auth in requests():
            status, text, ctype = call(port, method, path, body, TOKEN if auth else None)
            out.append((status, text.replace(f"http://127.0.0.1:{stub_port}", "<STUB>"), ctype))
        return out
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        stub.terminate()
        stub.wait(timeout=5)


def main():
    if not R.RS_BIN.exists():
        raise SystemExit(f"missing {R.RS_BIN}; build it first")
    results = {}
    for side in ("py", "rs"):
        with tempfile.TemporaryDirectory(prefix=f"ew-serve-{side}-") as td:
            results[side] = run_side(side, Path(td))

    failed = 0
    names = [n for n, *_ in requests()]
    for name, py, rs in zip(names, results["py"], results["rs"]):
        py_body = R.canonical(py[1])
        rs_body = R.canonical(rs[1])
        problems = []
        if py[0] != rs[0]:
            problems.append(f"status {py[0]} != {rs[0]}")
        if py_body != rs_body:
            problems.append(f"body:\n  want {py_body!r}\n  got  {rs_body!r}")
        if (py[2] or "").split(";")[0] != (rs[2] or "").split(";")[0]:
            problems.append(f"content-type {py[2]!r} != {rs[2]!r}")
        if problems:
            failed += 1
            print(f"FAIL {name}")
            for p in problems:
                print("  " + p.replace("\n", "\n  "))
        else:
            print(f"ok   {name}")
    print(f"PARITY {len(names) - failed}/{len(names)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
