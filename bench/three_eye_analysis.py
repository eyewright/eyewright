"""Three-eye gate analysis on the noul decisions of typed-decisions (the loop's gate shape).

Gate semantics (as in loop.py):
  - main (laya-TD) confident done (p >= 0.75)          -> accept
  - main confident not-done (p <= 0.25)                -> continue
  - uncertain (0.25 < p < 0.75)                        -> consult both eyes:
      >=2 consults confident (max(p,1-p) >= 0.9) and same direction:
          direction true  -> accept (consensus)
          direction false -> continue (consensus-reject)
      exactly 1 confident and the other within 0.05 of main -> review-conflict
      exactly 1 confident otherwise                          -> review-weak
      none confident                                         -> review-no-signal
"""
import collections
import json

import ensemble as E

FILES = {
    "laya-typed-decisions": "responses-laya-laya-typed-decisions.jsonl",
    "tev1:4b": "responses-tev1_4b.jsonl",
    "tev1:0.8b": "responses-tev1_0.8b.jsonl",
    "laya-multilingual": "responses-laya-laya-multilingual.jsonl",
    "von": "responses-von.jsonl",
}
MAIN = "laya-typed-decisions"
ACCEPT, HIGH, DELTA = 0.75, 0.9, 0.05

cases = {json.loads(l)["id"]: json.loads(l) for l in open("cases.jsonl", encoding="utf-8")}
tables = {m: E.load_answers(p) for m, p in FILES.items()}


def noul_p(m, cid, q):
    a = tables.get(m, {}).get(cid, {}).get(q)
    if not isinstance(a, dict):
        return None
    if a.get("type") == "noul" and a.get("noul") is not None:
        return float(a["noul"])
    probs = a.get("probabilities") or {}
    if isinstance(probs, dict) and "true" in probs:
        return float(probs["true"])
    return None


def evaluate(pair):
    st = collections.Counter()
    for cid, c in cases.items():
        for q, gold in c["gold"].items():
            if gold.get("type") != "noul":
                continue
            gl = str(gold.get("label")).lower() == "true"
            p1 = noul_p(MAIN, cid, q)
            if p1 is None:
                continue
            st["total"] += 1
            if p1 >= ACCEPT:
                st["main-accept"] += 1
                st["main-accept-ok"] += (gl is True)
                continue
            if p1 <= 1 - ACCEPT:
                st["main-reject"] += 1
                continue
            ps = [(n, noul_p(n, cid, q)) for n in pair]
            confident = [(n, p) for n, p in ps if p is not None and max(p, 1 - p) >= HIGH]
            if len(confident) >= 2:
                dirs = {(p >= 0.5) for _, p in confident}
                if len(dirs) == 1:
                    dir_true = dirs.pop()
                    if dir_true:
                        st["consensus-accept"] += 1
                        st["consensus-accept-ok"] += (gl is True)
                    else:
                        st["consensus-reject"] += 1
                        st["consensus-reject-ok"] += (gl is False)
                else:
                    st["review-conflict"] += 1
                continue
            if len(confident) == 1:
                cn, cp = confident[0]
                others = [p for n, p in ps if n != cn and p is not None]
                if others and any(abs(p - p1) <= DELTA for p in others):
                    st["review-conflict"] += 1
                else:
                    st["review-weak"] += 1
                continue
            st["review-no-signal"] += 1

    acted = st["main-accept"] + st["consensus-accept"] + st["consensus-reject"]
    acted_ok = st["main-accept-ok"] + st["consensus-accept-ok"] + st["consensus-reject-ok"]
    reviewed = st["total"] - acted
    return {
        "pair": " + ".join(pair),
        "n": st["total"],
        "accept_main": st["main-accept"],
        "accept_main_acc": round(st["main-accept-ok"] / st["main-accept"], 4) if st["main-accept"] else None,
        "consensus_accept": st["consensus-accept"],
        "consensus_accept_acc": round(st["consensus-accept-ok"] / st["consensus-accept"], 4) if st["consensus-accept"] else None,
        "consensus_reject": st["consensus-reject"],
        "consensus_reject_acc": round(st["consensus-reject-ok"] / st["consensus-reject"], 4) if st["consensus-reject"] else None,
        "acted": acted,
        "acted_pct": round(acted / st["total"], 3),
        "acted_acc": round(acted_ok / acted, 4) if acted else None,
        "reviewed": reviewed,
        "review_mix": {k: st[k] for k in ("main-reject", "review-conflict", "review-weak", "review-no-signal")},
    }


print(f"main = {MAIN}; noul decisions")
for pair in [("tev1:4b", "von"), ("tev1:4b", "laya-multilingual"), ("tev1:4b", "tev1:0.8b"), ("von", "laya-multilingual")]:
    print(json.dumps(evaluate(pair), ensure_ascii=False))