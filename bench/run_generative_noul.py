"""Screening runner: ask the 600-noul prompt set to a candidate.

Same protocol as the three-eye gate proxy (same rows, same later policy), so the
results are directly comparable.

Engines:
  ollama               local chat model, JSON-contract prompt (self-reported conf)
  openrouter           OpenRouter chat model, JSON-contract prompt (self-reported conf)
  openrouter-decisions OpenRouter /api/alpha/decisions -- NATIVE decision API
                       (TypeSafe Jev et al.); same state/questions shape as
                       /v1/systemone, returns real `noul` posteriors

    uv run python run_generative_noul.py --engine openrouter-decisions \
        --model typesafe/jev-1.13 --out responses-jev-113.jsonl --zdr --workers 8
    uv run python run_generative_noul.py --engine ollama --model gemma4:12b \
        --out responses-gemma12b.jsonl

Resume: cases already marked ok in the out file are skipped.
"""

import argparse
import json
import os
import random
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from oracle.generative import _extract_json

ap = argparse.ArgumentParser()
ap.add_argument("--engine", choices=["ollama", "openrouter", "openrouter-decisions"], required=True)
ap.add_argument("--model", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--cases", default="cases.jsonl")
ap.add_argument("--workers", type=int, default=0)
ap.add_argument("--limit", type=int, default=0, help="only the first N cases (smoke)")
ap.add_argument("--zdr", action="store_true", help="OpenRouter: route only to zero-data-retention providers")
args = ap.parse_args()

WORKERS = args.workers or (8 if args.engine.startswith("openrouter") else 1)
KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + KEY,
    "HTTP-Referer": "http://localhost",
    "X-Title": "oracle-screening",
}
PROVIDER = {"zdr": True} if args.zdr else None

lock = threading.Lock()
cost = {"usd": 0.0}


def _post(url, payload, headers, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def build_prompt(state_json, q):
    crit = q.get("criteria") or {}
    t, f = crit.get("true"), crit.get("false")
    extra = ""
    if t or f:
        extra = f"\n\nTRUE MEANS: {t or '(not given)'}\nFALSE MEANS: {f or '(not given)'}"
    return (
        "You are a decision engine. Answer with a single JSON object and nothing else:\n"
        '{"answer": <"yes" or "no">, "confidence": <0.0-1.0>, "reason": "<one short sentence>"}\n\n'
        'Rules: "answer" must be "yes" or "no". "confidence" is your estimated probability that\n'
        "the answer is correct. Base the answer only on the state and criteria."
        f"\n\nSTATE:\n{state_json}{extra}\n\nQUESTION:\n{q.get('instructions', '')}"
    )


def ask_ollama(model, prompt, timeout=600):
    resp = _post(
        "http://localhost:11434/api/chat",
        {"model": model, "messages": [{"role": "user", "content": prompt}],
         "stream": False, "format": "json",
         "options": {"temperature": 0, "num_predict": 200}, "think": False},
        {"Content-Type": "application/json"}, timeout,
    )
    return (resp.get("message") or {}).get("content", "") or ""


def ask_openrouter(model, prompt, timeout=180):
    # 2000 tokens of headroom: the router sometimes routes to reasoning models
    # that burn hundreds of tokens of hidden reasoning before the JSON answer.
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "max_tokens": 2000}
    if PROVIDER:
        payload["provider"] = PROVIDER
    resp = _post("https://openrouter.ai/api/v1/chat/completions", payload, OPENROUTER_HEADERS, timeout)
    choices = resp.get("choices") or [{}]
    content = ((choices[0].get("message") or {}).get("content")) or ""
    usage = resp.get("usage") or {}
    if not content:
        raise ValueError(
            f"empty content (finish={choices[0].get('finish_reason')}, "
            f"completion_tokens={usage.get('completion_tokens')})"
        )
    return content, resp.get("model"), resp.get("provider"), usage.get("cost")


def parse_noul(content):
    obj = _extract_json(content) or {}
    ans = str(obj.get("answer", "")).strip().lower()
    if ans.startswith("y"):
        ans = "yes"
    elif ans.startswith("n"):
        ans = "no"
    else:
        return None
    conf = obj.get("confidence")
    try:
        conf = float(conf)
        if not 0 <= conf <= 1:
            conf = None
    except (TypeError, ValueError):
        conf = None
    p = (conf if ans == "yes" else 1 - conf) if conf is not None else 0.5
    return {"answer": ans, "confidence": conf, "p_true": round(p, 4),
            "reason": obj.get("reason"), "raw": content[:300]}


def attempt(state_obj, qid, q):
    """One call -> (answer_record|None, cost_usd, error|None)."""
    if args.engine == "openrouter-decisions":
        payload = {"model": args.model, "state": state_obj, "questions": {qid: q}}
        if PROVIDER:
            payload["provider"] = PROVIDER
        resp = _post("https://openrouter.ai/api/alpha/decisions", payload, OPENROUTER_HEADERS, 180)
        ans = (resp.get("answers") or {}).get(qid) or {}
        if ans.get("noul") is None:
            return None, 0.0, "no noul in " + str(ans)[:80]
        rec = {"type": "noul", "noul": float(ans["noul"]),
               "upstream_model": resp.get("model"), "provider": resp.get("provider")}
        return rec, float((resp.get("usage") or {}).get("cost") or 0.0), None

    prompt = build_prompt(json.dumps(state_obj, ensure_ascii=False), q)
    if args.engine == "ollama":
        content = ask_ollama(args.model, prompt)
        upstream, c = args.model, 0.0
    else:
        content, upstream, _prov, c = ask_openrouter(args.model, prompt)
    parsed = parse_noul(content)
    if not parsed:
        return None, float(c or 0.0), "unparseable: " + content[:120]
    rec = {"type": "noul", "noul": parsed["p_true"], "noul_raw": parsed["p_true"],
           "answer": parsed["answer"], "confidence": parsed["confidence"],
           "reason": parsed.get("reason"), "upstream_model": upstream}
    return rec, float(c or 0.0), None


def attempt_with_retries(state_obj, qid, q):
    attempts = 3 if args.engine.startswith("openrouter") else 2
    last = None
    for i in range(attempts):
        try:
            rec, c, err = attempt(state_obj, qid, q)
            if c:
                with lock:
                    cost["usd"] += c
            if rec:
                return rec, None
            last = err
        except Exception as e:
            last = str(e)[:200]
        time.sleep((2 ** i) + random.random())
    return None, last


def main():
    cases = [json.loads(l) for l in open(args.cases, encoding="utf-8")]
    if args.limit:
        cases = cases[: args.limit]

    done = set()
    out_path = Path(args.out)
    if out_path.exists():
        for line in out_path.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                if r.get("ok"):
                    done.add(r["id"])
            except Exception:
                pass

    todo = [c for c in cases if c["id"] not in done]
    print(f"{len(cases)} cases, {len(done)} already ok, {len(todo)} to run "
          f"({args.engine}:{args.model}, workers={WORKERS}, zdr={bool(PROVIDER)})", flush=True)

    fo = out_path.open("a", encoding="utf-8")
    n_done = 0
    t0 = time.perf_counter()

    def work(c):
        nonlocal n_done
        qs = {q: v for q, v in c["questions"].items() if v.get("type") == "noul"}
        if not qs:
            return None
        tc = time.perf_counter()
        answers, errs = {}, {}
        for qid, q in qs.items():
            rec, err = attempt_with_retries(c["state"], qid, q)
            if rec:
                answers[qid] = rec
            else:
                errs[qid] = err
        record = {"id": c["id"], "workflow": c["workflow"], "ok": not errs,
                  "resp": {"answers": answers},
                  "ms": round((time.perf_counter() - tc) * 1000, 1),
                  "model": args.model, "engine": args.engine}
        if errs:
            record["error"] = errs
        with lock:
            fo.write(json.dumps(record, ensure_ascii=False) + "\n")
            fo.flush()
            n_done += 1
            if n_done % 25 == 0 or n_done == len(todo):
                rate = n_done / (time.perf_counter() - t0)
                print(f"  {n_done}/{len(todo)}  {rate:.2f} cases/s  cost=${cost['usd']:.4f}", flush=True)
        return record

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(work, todo))

    fo.close()
    print(f"done -> {args.out}  cost=${cost['usd']:.4f}", flush=True)


if __name__ == "__main__":
    main()