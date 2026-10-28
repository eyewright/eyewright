"""Python side of the generative parity cases.

Only the transport is redirected: `_post_json` is patched to send the same
payload to the parity stub instead of localhost:11434. Prompt building, JSON
extraction, normalization and the auto-fallback logic are the real code.
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eyewright.generative as G  # noqa: E402
from eyewright.decide import ask  # noqa: E402

_original_post = G._post_json


def redirected(url, payload, timeout=120):
    base = os.environ["EYEWRIGHT_OLLAMA_URL"].rstrip("/")
    return _original_post(base + "/api/chat", payload, timeout)


G._post_json = redirected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="ask")
    ap.add_argument("--config", required=True)
    ap.add_argument("--state", default="")
    ap.add_argument("--question", default="")
    ap.add_argument("--choices")
    ap.add_argument("--levels")
    ap.add_argument("--engine", default="generative")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = ask(
        cfg,
        args.state,
        args.question,
        choices=json.loads(args.choices) if args.choices else None,
        levels=json.loads(args.levels) if args.levels else None,
        engine=None if args.engine == "typed" else args.engine,
    )
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
