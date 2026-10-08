"""Decision-committee ("Total Recall") policy + offline replay on typed-decisions.

Policy per question:
  - each member returns a label (argmax) and a probability distribution
  - if all members agree            -> tier unanimous
  - if >=2/3 agree including main   -> tier majority-main
  - if >=2/3 agree without main     -> tier majority-nonmain (main dissents)
  - otherwise (all different)       -> tier split, fall back to main's label
Reliability order: unanimous > majority-main > majority-nonmain > split.
Variants compared: main alone, trio policy, soft fusion (mean probs), accuracy-weighted soft.
"""
import argparse
import collections
import json
import math

DEFAULT_FILES = {
    "laya-typed-decisions": "responses-laya-laya-typed-decisions.jsonl",
    "tev1:4b": "responses-tev1_4b.jsonl",
    "tev1:0.8b": "responses-tev1_0.8b.jsonl",
    "laya-multilingual": "responses-laya-laya-multilingual.jsonl",
    "laya-english": "responses-laya-laya-english.jsonl",
}


def load_answers(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("ok"):
            out[r["id"]] = (r.get("resp") or {}).get("answers") or {}
    return out


def norm_label(a):
    t = a.get("type")
    if t == "choice":
        return a.get("choice")
    if t == "noul":
        p = a.get("noul")
        return None if p is None else ("true" if p >= 0.5 else "false")
    if t == "score":
        probs = a.get("probabilities") or {}
        return max(probs, key=probs.get) if probs else None
    return None


def norm_probs(a):
    t = a.get("type")
    if t == "choice" or t == "score":
        return dict(a.get("probabilities") or {})
    if t == "noul":
        p = a.get("noul")
        return {"true": p, "false": 1 - p} if p is not None else {}
    return {}


def fuse(prob_list):
    fused = collections.defaultdict(float)
    n = 0
    for p in prob_list:
        if p:
            n += 1
            for k, v in p.items():
                fused[k] += v
    if not n:
        return {}
    return {k: v / n for k, v in fused.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="cases.jsonl")
    ap.add_argument("--main", default="laya-typed-decisions")
    ap.add_argument("--members", nargs="+", default=["laya-typed-decisions", "tev1:4b", "laya-multilingual"])
    ap.add_argument("--extra", nargs="*", default=[], help="additional members to report separately")
    args = ap.parse_args()

    cases = {json.loads(l)["id"]: json.loads(l) for l in open(args.cases, encoding="utf-8")}
    tables = {m: load_answers(p) for m, p in DEFAULT_FILES.items()}

    # member accuracies (sanity)
    def member_acc(m):
        hit = tot = 0
        for cid, c in cases.items():
            ans = tables[m].get(cid) or {}
            for q, gold in c["gold"].items():
                a = ans.get(q)
                if not isinstance(a, dict):
                    continue
                pl = norm_label(a)
                if pl is None or gold.get("label") is None:
                    continue
                tot += 1
                hit += str(pl) == str(gold["label"])
        return hit / tot if tot else 0.0

    accs = {m: member_acc(m) for m in args.members}
    print("member accuracies:", {m: round(a, 4) for m, a in accs.items()})
    weights = {m: (a ** 2) for m, a in accs.items()}  # sharper weighting

    tiers = collections.Counter()
    policy_hit = policy_tot = 0
    soft_hit = soft_tot = 0
    wsoft_hit = wsoft_tot = 0
    main_hit = main_tot = 0
    tier_hits = collections.Counter()
    tier_stats = collections.Counter()
    tier_main_hits = collections.Counter()
    veto_hit = veto_tot = 0
    unan_hit = unan_tot = 0
    qtype_stats = collections.defaultdict(lambda: [0, 0])  # [hit, tot] for policy

    for cid, c in cases.items():
        for q, gold in c["gold"].items():
            gl = gold.get("label")
            if gl is None:
                continue
            labels = {}
            probs = {}
            for m in args.members:
                a = (tables[m].get(cid) or {}).get(q)
                if not isinstance(a, dict):
                    continue
                labels[m] = norm_label(a)
                probs[m] = norm_probs(a)
            if args.main not in labels:
                continue
            main_label = labels[args.main]
            main_tot += 1
            main_hit += str(main_label) == str(gl)

            tally = collections.Counter(v for v in labels.values() if v is not None)
            if not tally:
                continue
            top_label, top_n = tally.most_common(1)[0]
            n = sum(tally.values())
            if top_n == n and len(tally) == 1:
                tier = "unanimous"
            elif top_n >= math.ceil(n * 2 / 3):
                tier = "majority-main" if top_label == main_label else "majority-nonmain"
            else:
                tier = "split"
            decision = top_label if tier != "split" else main_label
            tiers[tier] += 1
            hit = str(decision) == str(gl)
            tier_hits[tier] += hit
            tier_stats[tier] += 1
            tier_main_hits[tier] += str(main_label) == str(gl)
            veto = main_label if tier in ("majority-nonmain", "split") else top_label
            veto_hit += str(veto) == str(gl)
            veto_tot += 1
            unan = top_label if tier == "unanimous" else main_label
            unan_hit += str(unan) == str(gl)
            unan_tot += 1
            policy_tot += 1
            policy_hit += hit
            qtype = gold.get("type") or "unknown"
            qtype_stats[qtype][0] += hit
            qtype_stats[qtype][1] += 1

            fp = fuse([probs.get(m) or {} for m in args.members])
            if fp:
                soft_tot += 1
                soft_hit += str(max(fp, key=fp.get)) == str(gl)
            wf = collections.defaultdict(float)
            for m in args.members:
                for k, v in (probs.get(m) or {}).items():
                    wf[k] += v * weights.get(m, 1.0)
            if wf:
                wsoft_tot += 1
                wsoft_hit += str(max(wf, key=wf.get)) == str(gl)

    print()
    print(f"decisions scored: main={main_tot}")
    print(f"main alone            : {main_hit / main_tot:.4f}")
    print(f"trio policy (majority): {policy_hit / policy_tot:.4f}")
    print(f"main-veto policy      : {veto_hit / veto_tot:.4f}")
    print(f"unanimous-or-main     : {unan_hit / unan_tot:.4f}")
    print(f"soft fusion (mean)    : {soft_hit / soft_tot:.4f}")
    print(f"soft fusion (acc^2)   : {wsoft_hit / wsoft_tot:.4f}")
    print()
    print("tier coverage / policy acc / main acc:")
    for t in ("unanimous", "majority-main", "majority-nonmain", "split"):
        if tiers[t]:
            print(f"  {t:<18} n={tier_stats[t]:<5} policy={tier_hits[t] / tier_stats[t]:.4f}  main={tier_main_hits[t] / tier_stats[t]:.4f}")
    print("policy accuracy by question type:")
    for t, (hit, tot) in sorted(qtype_stats.items()):
        print(f"  {t:<8} n={tot:<5} acc={hit / tot:.4f}")


if __name__ == "__main__":
    main()