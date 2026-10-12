"""eyewright CLI: gate | ask | serve | mcp."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .decide import ask
from .gate import decide_gate


def _load_cfg(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _start_services():
    """Best-effort: run the supervisor once so local services are up before gating."""
    script = Path(__file__).resolve().parents[1] / "supervisor" / "svcwatch.py"
    if not script.exists():
        print(f"[eyewright] supervisor not found at {script}", file=sys.stderr)
        return
    try:
        subprocess.run([sys.executable, str(script), "--once"], timeout=180, check=False)
    except Exception as e:
        print(f"[eyewright] start-services failed: {e}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="eyewright", description="eyewright - local decision core")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="three-eye gate on a claim")
    g.add_argument("--state", required=True)
    g.add_argument("--question", required=True)
    g.add_argument("--config", default="examples/gate.json")
    g.add_argument("--start-services", action="store_true",
                   help="run the supervisor once (start any down local services) before gating")

    a = sub.add_parser("ask", help="typed decision (yes/no, choice, or scale)")
    a.add_argument("--state", required=True)
    a.add_argument("--question", required=True)
    a.add_argument("--choices", help="JSON object: option key -> description (choice)")
    a.add_argument("--levels", help="JSON array of level descriptions (score)")
    a.add_argument("--engine", default="typed", choices=["typed", "generative", "auto"],
                   help="typed (decision models; default), generative (local LLM), or auto (typed, fall back)")
    a.add_argument("--config", default="examples/gate.json")

    s = sub.add_parser("serve", help="HTTP service (/v1/gate, /v1/ask)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8090)
    s.add_argument("--token", help="bearer token for requests (default: $EYEWRIGHT_TOKEN); "
                                   "required when binding off-loopback")
    s.add_argument("--max-body", type=int, default=1000000, help="max request body bytes")
    s.add_argument("--config", default="examples/gate.json")

    m = sub.add_parser("mcp", help="MCP stdio server (needs the mcp extra)")
    m.add_argument("--config", default="examples/gate.json")
    m.add_argument("--start-services", action="store_true",
                   help="run the supervisor once before serving")

    args = ap.parse_args(argv)
    cfg = _load_cfg(args.config)

    if getattr(args, "start_services", False):
        _start_services()

    if args.cmd == "gate":
        p, trace = decide_gate(cfg, args.state, args.question)
        print(json.dumps({"p_done": round(p, 4), "decision": trace.get("decision"), "trace": trace}, indent=2))
        return 0
    if args.cmd == "ask":
        choices = json.loads(args.choices) if args.choices else None
        levels = json.loads(args.levels) if args.levels else None
        engine = None if args.engine == "typed" else args.engine
        print(json.dumps(ask(cfg, args.state, args.question, choices=choices, levels=levels, engine=engine), indent=2))
        return 0
    if args.cmd == "serve":
        from .server import serve

        serve(cfg, args.host, args.port, token=args.token, max_body=args.max_body)
        return 0
    if args.cmd == "mcp":
        from .mcp_server import run

        run(cfg)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())