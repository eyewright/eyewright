"""oracle CLI: gate | ask | serve | mcp."""

import argparse
import json
import sys
from pathlib import Path

from .decide import ask
from .gate import decide_gate


def _load_cfg(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="oracle", description="The Oracle - local decision core")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gate", help="three-eye gate on a claim")
    g.add_argument("--state", required=True)
    g.add_argument("--question", required=True)
    g.add_argument("--config", default="examples/gate.json")

    a = sub.add_parser("ask", help="typed decision (yes/no, choice, or scale)")
    a.add_argument("--state", required=True)
    a.add_argument("--question", required=True)
    a.add_argument("--choices", help="JSON object: option key -> description (choice)")
    a.add_argument("--levels", help="JSON array of level descriptions (score)")
    a.add_argument("--config", default="examples/gate.json")

    s = sub.add_parser("serve", help="HTTP service (/v1/gate, /v1/ask)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8090)
    s.add_argument("--config", default="examples/gate.json")

    m = sub.add_parser("mcp", help="MCP stdio server (needs the mcp extra)")
    m.add_argument("--config", default="examples/gate.json")

    args = ap.parse_args(argv)
    cfg = _load_cfg(args.config)

    if args.cmd == "gate":
        p, trace = decide_gate(cfg, args.state, args.question)
        print(json.dumps({"p_done": round(p, 4), "decision": trace.get("decision"), "trace": trace}, indent=2))
        return 0
    if args.cmd == "ask":
        choices = json.loads(args.choices) if args.choices else None
        levels = json.loads(args.levels) if args.levels else None
        print(json.dumps(ask(cfg, args.state, args.question, choices=choices, levels=levels), indent=2))
        return 0
    if args.cmd == "serve":
        from .server import serve

        serve(cfg, args.host, args.port)
        return 0
    if args.cmd == "mcp":
        from .mcp_server import run

        run(cfg)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())