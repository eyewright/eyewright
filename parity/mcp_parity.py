"""Parity harness for `mcp`: Python stdio server vs Rust stdio server.

Each side gets its own stub and config, receives the same newline-delimited
JSON-RPC script, and the responses are compared by id. Covers initialize,
tools/list, both tools, an unknown tool, ping and an unknown method.
"""

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run as R  # noqa: E402

SCRIPT = {
    "p": [
        0.9,
        {"choice": "b", "probabilities": {"a": 0.1, "b": 0.9}, "confidence": 0.9},
    ]
}

MESSAGES = [
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "parity", "version": "1.0"},
        },
    },
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "eyewright_gate", "arguments": {"state": "s", "question": "q"}},
    },
    {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "eyewright_ask",
            "arguments": {"state": "s", "question": "q", "choices": {"a": "x", "b": "y"}},
        },
    },
    {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {"name": "nope", "arguments": {}},
    },
    {"jsonrpc": "2.0", "id": 6, "method": "ping"},
    {"jsonrpc": "2.0", "id": 7, "method": "no/such"},
]


def run_side(side, tmpdir):
    stub, stub_port = R.start_stub(SCRIPT, tmpdir / "stub.jsonl")
    cfg = json.loads(json.dumps(R.BASE_CONFIG))
    cfg["primary"]["url"] = f"http://127.0.0.1:{stub_port}/v1/systemone"
    cfg_path = tmpdir / "config.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    argv = (
        [sys.executable, str(R.PY_ENTRY), "mcp"]
        if side == "py"
        else [str(R.RS_BIN), "mcp"]
    ) + ["--config", str(cfg_path)]
    proc = subprocess.Popen(
        argv,
        cwd=str(R.ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    killer = threading.Timer(60, proc.kill)
    killer.start()
    try:
        out = {}
        for msg in MESSAGES:
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
            if msg.get("id") is None:
                continue
            while True:
                line = proc.stdout.readline()
                if not line:
                    raise SystemExit(
                        f"{side} closed stdout; stderr: {proc.stderr.read()[-800:]}"
                    )
                obj = json.loads(line)
                if obj.get("id") == msg["id"]:
                    out[msg["id"]] = obj
                    break
        return out
    finally:
        killer.cancel()
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
        with tempfile.TemporaryDirectory(prefix=f"ew-mcp-{side}-") as td:
            results[side] = run_side(side, Path(td))

    failed = 0
    ids = [m["id"] for m in MESSAGES if m.get("id") is not None]
    for msg_id in ids:
        py = R.canonical(json.dumps(results["py"][msg_id]))
        rs = R.canonical(json.dumps(results["rs"][msg_id]))
        if py != rs:
            failed += 1
            print(f"FAIL id={msg_id}")
            print(f"  want {py!r}")
            print(f"  got  {rs!r}")
        else:
            print(f"ok   id={msg_id}")
    print(f"PARITY {len(ids) - failed}/{len(ids)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
