"""Ask von only the noul questions of the test split (for calibrated comparisons)."""
import argparse
import json
import os
import time
import urllib.request

OUT_DIR = os.path.expanduser(os.environ.get("EYEWRIGHT_VON_OUT", "~/ai-cache/von-calibrated"))
ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:8001/v1/systemone")
ap.add_argument("--key-file", default=".von-api-key")
ap.add_argument("--cases", default="cases.jsonl")
ap.add_argument("--out", default=os.path.join(OUT_DIR, "responses-von-calibrated.jsonl"))
args = ap.parse_args()

os.makedirs(os.path.dirname(args.out), exist_ok=True)

key = open(args.key_file, encoding="utf-8").read().strip()
cases = [json.loads(l) for l in open(args.cases, encoding="utf-8")]
ok = 0
# Unique temp file + atomic replace: two concurrent runs once interleaved their flushed
# lines into a corrupt responses file. With this, the canonical path always ends up as
# one complete writer's output instead of a splice.
tmp = f"{args.out}.{os.getpid()}.tmp"
with open(tmp, "w", encoding="utf-8") as fo:
    for i, c in enumerate(cases):
        qs = {q: v for q, v in c["questions"].items() if v.get("type") == "noul"}
        if not qs:
            continue
        body = json.dumps({"model": "von-1.3.0", "state": c["state"], "questions": qs}).encode()
        req = urllib.request.Request(args.url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        })
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                resp = json.loads(r.read().decode())
            rec = {"id": c["id"], "workflow": c["workflow"], "ok": True, "resp": resp,
                   "ms": round((time.perf_counter() - t0) * 1000, 1)}
            ok += 1
        except Exception as e:
            rec = {"id": c["id"], "workflow": c["workflow"], "ok": False, "error": str(e),
                   "ms": round((time.perf_counter() - t0) * 1000, 1)}
        fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fo.flush()
        os.fsync(fo.fileno())
        if (i + 1) % 50 == 0 or i == len(cases) - 1:
            print(f"{i + 1}/{len(cases)} cases ok={ok}", flush=True)

os.replace(tmp, args.out)
print(f"done -> {args.out} ({ok} cases)")
bad = 0
with open(args.out, encoding="utf-8") as fr:
    for line in fr:
        if not line.strip():
            continue
        try:
            json.loads(line)
        except Exception:
            bad += 1
print(f"validation: {bad} invalid lines")