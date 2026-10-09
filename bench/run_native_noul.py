"""Ask the noul questions of a cases file to a native System One endpoint.

Works for laya-serve / von (HTTP) and Ollama decision models. Records are
compatible with the other responses-*.jsonl files (native `noul` posterior).

    uv run python run_native_noul.py --type http --url http://127.0.0.1:8000/v1/systemone \
        --key-file "C:\\...\\.laya-api-key" --cases cases-train-holdout.jsonl \
        --out responses-holdout-laya-td.jsonl --workers 4
    uv run python run_native_noul.py --type ollama --model tev1:4b \
        --cases cases-train-holdout.jsonl --out responses-holdout-tev1.jsonl
"""

import argparse
import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--type", choices=["http", "ollama"], required=True)
ap.add_argument("--url", default="")
ap.add_argument("--model", default="")
ap.add_argument("--key-file", default="")
ap.add_argument("--cases", default="cases.jsonl")
ap.add_argument("--out", required=True)
ap.add_argument("--workers", type=int, default=4)
args = ap.parse_args()

URL = args.url or "http://localhost:11434/v1/systemone"
KEY = Path(args.key_file).read_text(encoding="utf-8").strip() if args.key_file and Path(args.key_file).exists() else ""
lock = threading.Lock()


def call(state, questions):
    payload = {"state": state, "questions": questions}
    if args.model:
        payload["model"] = args.model
    headers = {"Content-Type": "application/json"}
    if KEY:
        headers["Authorization"] = "Bearer " + KEY
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read().decode())


def main():
    cases = [json.loads(l) for l in open(args.cases, encoding="utf-8")]
    done = set()
    p = Path(args.out)
    if p.exists():
        for line in p.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                if r.get("ok"):
                    done.add(r["id"])
            except Exception:
                pass
    todo = [c for c in cases if c["id"] not in done]
    print(f"{len(cases)} cases, {len(done)} ok, {len(todo)} to run ({args.type}:{args.model or URL})", flush=True)
    fo = p.open("a", encoding="utf-8")
    n = 0
    t0 = time.perf_counter()

    def work(c):
        nonlocal n
        qs = {q: v for q, v in c["questions"].items() if v.get("type") == "noul"}
        tc = time.perf_counter()
        answers, errs = {}, {}
        for qid in qs:
            try:
                resp = call(c["state"], {qid: qs[qid]})
                ans = (resp.get("answers") or {}).get(qid) or {}
                if ans.get("noul") is None:
                    errs[qid] = "no noul in " + str(ans)[:80]
                else:
                    answers[qid] = {"type": "noul", "noul": float(ans["noul"])}
            except Exception as e:
                errs[qid] = str(e)[:160]
        rec = {"id": c["id"], "workflow": c["workflow"], "ok": not errs,
               "resp": {"answers": answers}, "ms": round((time.perf_counter() - tc) * 1000, 1),
               "model": args.model or args.url}
        if errs:
            rec["error"] = errs
        with lock:
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fo.flush()
            n += 1
            if n % 50 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)}  {n / (time.perf_counter() - t0):.2f} cases/s", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, todo))
    fo.close()
    print(f"done -> {args.out}", flush=True)


if __name__ == "__main__":
    main()