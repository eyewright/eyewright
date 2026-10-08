"""Compare von shipped vs calibrated as a consult eye on the 600-noul gate proxy."""
import collections
import json
import os

import ensemble as E

VON_CAL = r"C:\Users\kcpat\ai-cache\von-calibrated\responses-von-calibrated.jsonl"
FILES = {
    "laya-typed-decisions": "responses-laya-laya-typed-decisions.jsonl",
    "tev1:4b": "responses-tev1_4b.jsonl",
    "laya-multilingual": "responses-laya-laya-multilingual.jsonl",
    "von shipped": "responses-von.jsonl",
    "von calibrated": VON_CAL if os.path.exists(VON_CAL) else "responses-von-calibrated.jsonl",
}
MAIN = "laya-typed-decisions"
ACCEPT, HIGH, DELTA = 0.75, 0.9, 0.05

cases = {json.loads(l)["id"]: json.loads(l) for l in open("cases.jsonl", encoding="utf-8")}
tables = {m: E.load_answers(p) for m, p in FILES.items()}
noul_rows = [(cid, q, gold) for cid, c in cases.items() for q, gold in c["gold"].items() if gold.get("type") == "noul"]


def noul_p(m, cid, q):
    a = tables.get(m, {}).get(cid, {}).get(q)
    if not isinstance(a, dict):
        return None
    # Gate on the pre-band calibrated posterior: von types.py says committed `noul` is
    # clamped to [0.15,0.2]/[0.8,0.85], and patterns.confidence_gate uses noul_raw for
    # exactly this reason ("its distance from 0.5 is ~constant and useless").
    if a.get("noul_raw") is not None:
        return float(a["noul_raw"])
    if a.get("type") == "noul" and a.get("noul") is not None:
        return float(a["noul"])
    probs = a.get("probabilities") or {}
    if isinstance(probs, dict) and "true" in probs:
        return float(probs["true"])
    return None


def solo_stats(m):
    n = hit = high = 0
    for cid, q, gold in noul_rows:
        p = noul_p(m, cid, q)
        if p is None:
            continue
        gl = str(gold.get("label")).lower() == "true"
        n += 1
        hit += (p >= 0.5) == gl
        high += max(p, 1 - p) >= HIGH
    return {"n": n, "acc": round(hit / n, 4) if n else None, "pct_conf_090": round(high / n, 3) if n else None}


def calib_stats(m):
    """Brier + top-label ECE of the gate field on the test split.

    The refit won 5-fold CV on the train labels; this checks whether that win
    transfers to held-out decisions rather than just re-reading in-sample fit.
    """
    n = brier = 0
    buckets = collections.defaultdict(lambda: [0.0, 0, 0])
    for cid, q, gold in noul_rows:
        p = noul_p(m, cid, q)
        if p is None:
            continue
        y = 1.0 if str(gold.get("label")).lower() == "true" else 0.0
        n += 1
        brier += (p - y) ** 2
        conf = p if p >= 0.5 else 1 - p
        b = min(int(conf * 10), 9)
        buckets[b][0] += conf
        buckets[b][1] += (p >= 0.5) == (y == 1.0)
        buckets[b][2] += 1
    ece = sum(v[2] / n * abs(v[0] / v[2] - v[1] / v[2]) for v in buckets.values()) if n else None
    return {"n": n, "brier": round(brier / n, 4) if n else None, "ece": round(ece, 4) if ece is not None else None}


def gate_stats(consult_m):
    st = collections.Counter()
    for cid, q, gold in noul_rows:
        gl = str(gold.get("label")).lower() == "true"
        p1 = noul_p(MAIN, cid, q)
        if p1 is None:
            continue
        if p1 >= ACCEPT:
            st["accept_main"] += 1
            st["accept_main_ok"] += (gl is True)
            continue
        if p1 <= 1 - ACCEPT:
            st["main_reject"] += 1
            continue
        p2 = noul_p("tev1:4b", cid, q)
        p3 = noul_p(consult_m, cid, q)
        conf = [(p) for p in (p2, p3) if p is not None and max(p, 1 - p) >= HIGH]
        if len(conf) >= 2 and len({p >= 0.5 for p in conf}) == 1:
            dir_true = conf[0] >= 0.5
            if dir_true:
                st["cons_accept"] += 1
                st["cons_accept_ok"] += (gl is True)
            else:
                st["cons_reject"] += 1
                st["cons_reject_ok"] += (gl is False)
            continue
        if len(conf) == 1 and p3 is not None and p2 is not None:
            # conflict check: the non-confident eye matches main within delta
            other = p3 if conf[0] == p2 else p2
            if abs(other - p1) <= DELTA:
                st["conflict"] += 1
                continue
        st["review"] += 1
    acted = st["accept_main"] + st["cons_accept"] + st["cons_reject"]
    acted_ok = st["accept_main_ok"] + st["cons_accept_ok"] + st["cons_reject_ok"]
    return {
        "consult": consult_m,
        "consensus_accept": st["cons_accept"],
        "consensus_accept_acc": round(st["cons_accept_ok"] / st["cons_accept"], 4) if st["cons_accept"] else None,
        "consensus_reject": st["cons_reject"],
        "acted": acted,
        "acted_pct": round(acted / len(noul_rows), 3),
        "acted_acc": round(acted_ok / acted, 4) if acted else None,
        "conflict": st["conflict"],
        "review": st["review"],
    }


print(f"noul decisions: {len(noul_rows)}")
for m in ("von shipped", "von calibrated"):
    print(f"solo {m}: {json.dumps(solo_stats(m))}")
    print(f"calib {m}: {json.dumps(calib_stats(m))}")
print(json.dumps(gate_stats("von shipped")))
print(json.dumps(gate_stats("von calibrated")))