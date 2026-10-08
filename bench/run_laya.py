"""Run a local Laya checkpoint (safetensors via the official laya package) over cases.jsonl."""
import argparse
import json
import os
import time

os.environ.setdefault("USE_TF", "0")

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", required=True, help="local path or HF repo id")
ap.add_argument("--subfolder", default="")
ap.add_argument("--name", required=True)
ap.add_argument("--cases", default="cases.jsonl")
ap.add_argument("--out", default="")
ap.add_argument("--limit", type=int, default=0)
args = ap.parse_args()

out = args.out or f"responses-laya-{args.name}.jsonl"
print(f"loading checkpoint: {args.checkpoint} subfolder={args.subfolder or '-'} ...", flush=True)

import laya  # noqa: E402

if args.subfolder:
    agent = laya.load(args.checkpoint, subfolder=args.subfolder)
else:
    agent = laya.load(args.checkpoint)
print("loaded", flush=True)

cases = [json.loads(line) for line in open(args.cases, encoding="utf-8")]
if args.limit:
    cases = cases[: args.limit]

ok = 0
with open(out, "w", encoding="utf-8") as fo:
    for i, c in enumerate(cases):
        t0 = time.perf_counter()
        try:
            res = agent.predict(c["state"], c["questions"])
            rec = {"id": c["id"], "workflow": c["workflow"], "ok": True, "resp": res,
                   "ms": round((time.perf_counter() - t0) * 1000, 1)}
            ok += 1
        except Exception as e:
            rec = {"id": c["id"], "workflow": c["workflow"], "ok": False, "error": repr(e),
                   "ms": round((time.perf_counter() - t0) * 1000, 1)}
        fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fo.flush()
        if (i + 1) % 25 == 0 or i == len(cases) - 1:
            print(f"{i + 1}/{len(cases)} ok={ok}", flush=True)

print(f"done -> {out} ({ok}/{len(cases)} ok)")