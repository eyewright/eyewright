"""Score decision-bench response files against typed-decisions gold.

Usage: uv run python score.py --files responses-tev1_0.8b.jsonl responses-laya-...jsonl
"""
import argparse
import collections
import json
import math


def pred_and_probs(answer):
    t = answer.get("type")
    if t == "choice":
        return answer.get("choice"), dict(answer.get("probabilities") or {})
    if t == "noul":
        p = answer.get("noul")
        if p is None:
            return None, dict(answer.get("probabilities") or {})
        return ("true" if p >= 0.5 else "false"), {"true": p, "false": 1 - p}
    if t == "score":
        probs = dict(answer.get("probabilities") or {})
        label = max(probs, key=probs.get) if probs else None
        return label, probs
    return None, {}


def gold_label(gold):
    return gold.get("label")


def gold_probs(gold):
    p = gold.get("probabilities")
    if isinstance(p, dict):
        return dict(p)
    if gold.get("type") == "noul" and "noul" in gold:
        v = gold["noul"]
        return {"true": v, "false": 1 - v}
    return {}


def brier(pred, gold):
    keys = set(pred) | set(gold)
    if not keys:
        return None
    return sum((pred.get(k, 0.0) - gold.get(k, 0.0)) ** 2 for k in keys) / len(keys)


def kl(pred, gold, eps=1e-6):
    keys = set(gold)
    if not keys:
        return None
    total = 0.0
    for k in keys:
        g = max(gold.get(k, 0.0), eps)
        p = max(pred.get(k, 0.0), eps)
        total += g * math.log(g / p)
    return total


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x, nd=4):
    return "n/a" if x is None else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--cases", default="cases.jsonl")
    args = ap.parse_args()

    cases = {json.loads(line)["id"]: json.loads(line) for line in open(args.cases, encoding="utf-8")}

    for path in args.files:
        rows = [json.loads(line) for line in open(path, encoding="utf-8")]
        hits, briers, kls, lats = [], [], [], []
        by_type = collections.defaultdict(list)
        by_wf = collections.defaultdict(list)
        errors = 0

        for r in rows:
            c = cases.get(r["id"])
            if c is None:
                continue
            lats.append(r.get("ms"))
            if not r.get("ok"):
                errors += 1
                continue
            resp = r["resp"] or {}
            answers = resp.get("answers") or {}
            for qname, gold in c["gold"].items():
                a = answers.get(qname)
                if not isinstance(a, dict):
                    continue
                pl, pp = pred_and_probs(a)
                gl = gold_label(gold)
                if pl is None or gl is None:
                    continue
                hit = str(pl) == str(gl)
                hits.append(hit)
                qtype = gold.get("type") or a.get("type") or "unknown"
                by_type[qtype].append(hit)
                by_wf[c["workflow"]].append(hit)
                b = brier(pp, gold_probs(gold))
                if b is not None:
                    briers.append(b)
                k = kl(pp, gold_probs(gold))
                if k is not None:
                    kls.append(k)

        print(f"== {path} ==")
        print(f"  decisions scored: {len(hits)}   errors: {errors}   mean latency: {fmt(mean(lats), 1)} ms")
        print(f"  accuracy: {fmt(mean(hits))}   Brier: {fmt(mean(briers))}   KL(gold||pred): {fmt(mean(kls))}")
        print("  by question type:")
        for t, xs in sorted(by_type.items()):
            print(f"    {t:<8} n={len(xs):<5} acc={fmt(mean(xs))}")
        print("  by workflow:")
        for w, xs in sorted(by_wf.items()):
            print(f"    {w:<28} n={len(xs):<5} acc={fmt(mean(xs))}")
        print()


if __name__ == "__main__":
    main()