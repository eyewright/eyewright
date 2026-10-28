"""Parity harness: Python eyewright vs the Rust port.

    python parity/run.py              # compare against parity/golden/
    python parity/run.py --capture    # (re)write goldens from Python
    python parity/run.py --side py    # Python only (determinism check)
    python parity/run.py --only gate- # subset by name substring

Every case starts a fresh stub engine, writes a temp config, and runs the CLI
as a subprocess. Compared: exit code, canonical JSON stdout, and required
stderr substrings. The stub is real HTTP, so request shape and error handling
are part of the test.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARITY = ROOT / "parity"
GOLDEN = PARITY / "golden"
STUB = PARITY / "stub_engine.py"
PY_ENTRY = PARITY / "py_entry.py"
PY_GEN_ENTRY = PARITY / "py_gen_entry.py"
RS_BIN = ROOT / "rust" / "target" / "release" / "eyewright.exe"

BASE_CONFIG = {
    "primary": {
        "name": "p",
        "type": "systemone-http",
        "url": "{STUB}/v1/systemone",
        "model": "p",
    },
    "consults": [],
    "attempts": 1,
    "retry_backoff_s": 0,
    "timeout_s": 5,
}


def start_stub(script, transcript):
    script_path = transcript.with_suffix(".script.json")
    script_path.write_text(json.dumps(script), encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(STUB), str(script_path), str(transcript)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = proc.stdout.readline().strip()
    if not line.startswith("PORT "):
        proc.kill()
        raise SystemExit(f"stub failed to start: {line!r} {proc.stderr.read()!r}")
    return proc, int(line.split()[1])


def scrub_errors(node):
    """Error *wording* is not behavior; presence and the resulting decision are.

    Replaces the value of any `error` / `*_error*` string with <ERR> so a
    timeout message from urllib and one from ureq still compare equal.
    """
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if isinstance(value, str) and (key == "error" or "_error" in key):
                out[key] = "<ERR>" if value else value
            else:
                out[key] = scrub_errors(value)
        return out
    if isinstance(node, list):
        return [scrub_errors(v) for v in node]
    return node


def canonical(stdout: str):
    """JSON object comparison: key order and whitespace are not semantic."""
    text = stdout.strip()
    if not text:
        return ""
    try:
        return json.dumps(scrub_errors(json.loads(text)), sort_keys=True, separators=(",", ":"))
    except json.JSONDecodeError:
        return text


def normalize(text, stub_url, tmpdir):
    home = str(Path.home())
    for old, new in (
        (stub_url, "<STUB>"),
        (str(tmpdir), "<TMP>"),
        (str(ROOT), "<REPO>"),
        (str(ROOT).replace("\\", "/"), "<REPO>"),
        (home, "<HOME>"),
        (home.replace("\\", "/"), "<HOME>"),
    ):
        text = text.replace(old, new)
    return text


def run_case(case, side, tmpdir):
    transcript = tmpdir / "stub.jsonl"
    stub, port = start_stub(case.get("script") or {}, transcript)
    stub_url = f"http://127.0.0.1:{port}"
    try:
        cfg = json.loads(json.dumps(BASE_CONFIG))
        cfg.update(case.get("config") or {})
        raw = json.dumps(cfg).replace("{STUB}", stub_url)
        cfg_path = tmpdir / "config.json"
        cfg_path.write_text(raw, encoding="utf-8")

        argv = (
            [sys.executable, str(PY_GEN_ENTRY if case.get("gen") else PY_ENTRY)]
            if side == "py"
            else [str(RS_BIN)]
        )
        argv += (case.get("cmd") or ["gate"]) + [
            "--config",
            str(cfg_path),
            "--state",
            "s",
            "--question",
            "q",
        ]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        if case.get("gen"):
            env["EYEWRIGHT_OLLAMA_URL"] = stub_url
        try:
            proc = subprocess.run(
                argv,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return {"exit": -1, "stdout": "", "stderr": "HARNESS TIMEOUT"}, transcript
        return {
            "exit": proc.returncode,
            "stdout": canonical(normalize(proc.stdout, stub_url, tmpdir)),
            "raw_stdout": normalize(proc.stdout, stub_url, tmpdir),
            "stderr": normalize(proc.stderr, stub_url, tmpdir),
        }, transcript
    finally:
        stub.terminate()
        stub.wait(timeout=5)


def check(case, got, golden):
    problems = []
    if got["exit"] != golden["exit"]:
        problems.append(f"exit {got['exit']} != {golden['exit']}")
    if got["stdout"] != golden["stdout"]:
        problems.append(f"stdout:\n  want {golden['stdout']!r}\n  got  {got['stdout']!r}")
    for needle in case.get("stderr_contains") or []:
        if needle not in got["stderr"]:
            problems.append(f"stderr missing {needle!r}: {got['stderr'][-400:]!r}")
    for needle in case.get("stdout_contains") or []:
        if needle not in got["raw_stdout"]:
            problems.append(f"stdout missing {needle!r}: {got['raw_stdout'][:400]!r}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", action="store_true")
    ap.add_argument("--side", choices=["py", "rs", "both"], default="both")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    cases = json.loads((PARITY / "cases.json").read_text(encoding="utf-8"))["cases"]
    cases = [c for c in cases if args.only in c["name"]]
    GOLDEN.mkdir(exist_ok=True)

    if not args.capture and args.side in ("rs", "both") and not RS_BIN.exists():
        raise SystemExit(f"missing {RS_BIN}; build it first (cargo build --release in rust/)")

    failed = 0
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="ew-parity-") as td:
            tmpdir = Path(td)
            if args.capture:
                got, _ = run_case(case, "py", tmpdir)
                (GOLDEN / f"{case['name']}.json").write_text(
                    json.dumps({"exit": got["exit"], "stdout": got["stdout"]}, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"cap  {case['name']}  exit={got['exit']}")
                continue
            if args.side == "py":
                # Determinism: the same case twice must produce the same bytes.
                first, _ = run_case(case, "py", tmpdir)
                second, _ = run_case(case, "py", tmpdir)
                problems = [] if first == second else ["Python side is nondeterministic"]
            else:
                golden = json.loads((GOLDEN / f"{case['name']}.json").read_text(encoding="utf-8"))
                got, _ = run_case(case, "rs", tmpdir)
                problems = check(case, got, golden)
        if problems:
            failed += 1
            print(f"FAIL {case['name']}")
            for p in problems:
                print("  " + p.replace("\n", "\n  "))
        else:
            print(f"ok   {case['name']}")

    total = len(cases)
    print(f"PARITY {total - failed}/{total}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
