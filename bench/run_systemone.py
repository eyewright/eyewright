"""Run a System One model (Ollama /v1/systemone, e.g. tev1) over cases.jsonl."""
import argparse
import json
import time
import urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="tev1:0.8b")
ap.add_argument("--url", default="http://localhost:11434/v1/systemone")
ap.add_argument("--cases", default="cases.jsonl")
ap.add_argument("--out", default="")
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--timeout", type=float, default=120)
ap.add_argument("--api-key", default="")
args = ap.parse_args()

out = args.out or ("responses-" + args.model.replace(":", "_").replace("/", "_") + ".jsonl")
cases = [json.loads(line) for line in open(args.cases, encoding="utf-8")]
if args.limit:
    cases = cases[: args.limit]

ok = 0
with open(out, "w", encoding="utf-8") as fo:
    for i, c in enumerate(cases):
        body = json.dumps({"model": args.model, "state": c["state"], "questions": c["questions"]}).encode()
        req = urllib.request.Request(args.url, data=body, headers={"Content-Type": "application/json"})
        if args.api_key:
            req.add_header("Authorization", "Bearer " + args.api_key)
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as r:
                resp = json.loads(r.read().decode())
            rec = {"id": c["id"], "workflow": c["workflow"], "ok": True, "resp": resp,
                   "ms": round((time.perf_counter() - t0) * 1000, 1)}
            ok += 1
        except Exception as e:
            rec = {"id": c["id"], "workflow": c["workflow"], "ok": False, "error": str(e),
                   "ms": round((time.perf_counter() - t0) * 1000, 1)}
        fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fo.flush()
        if (i + 1) % 25 == 0 or i == len(cases) - 1:
            print(f"{i + 1}/{len(cases)} ok={ok}", flush=True)

print(f"done -> {out} ({ok}/{len(cases)} ok)")