"""Bootstrap CIs for the incumbent eyewright gate on the 600-noul proxy.

Read-only: quantifies how much of the headline THREE-EYE table is signal vs noise.
No new inference. Run from bench/:

    uv run python stats_ci.py
"""

import json
import random

ACCEPT, HIGH, DELTA = 0.75, 0.9, 0.05
MAIN = "responses-laya-laya-typed-decisions.jsonl"
TEV1 = "responses-tev1_4b.jsonl"
LML = "responses-laya-laya-multilingual.jsonl"


def load(p):
    out = {}
    for line in open(p, encoding="utf-8"):
        r = json.loads(line)
        if r.get("ok"):
            out[r["id"]] = (r.get("resp") or {}).get("answers") or {}
    return out


def noul_p(t, cid, q):
    a = t.get(cid, {}).get(q)
    if not isinstance(a, dict):
        return None
    if a.get("noul_raw") is not None:
        return float(a["noul_raw"])
    if a.get("type") == "noul" and a.get("noul") is not None:
        return float(a["noul"])
    p = (a.get("probabilities") or {}).get("true")
    return float(p) if p is not None else None


cases = {json.loads(l)["id"]: json.loads(l) for l in open("cases.jsonl", encoding="utf-8")}
tables = {"main": load(MAIN), "tev1": load(TEV1), "lml": load(LML)}
rows = [
    (cid, q, str(gold.get("label")).lower() == "true")
    for cid, c in cases.items()
    for q, gold in c["gold"].items()
    if gold.get("type") == "noul"
]

# per-row outcome under the incumbent policy (loop/config.json v0.3)
out = []
for cid, q, gl in rows:
    p1 = noul_p(tables["main"], cid, q)
    if p1 is None:
        continue
    rec = {"acted": False, "correct": None, "cons": False, "path": "review"}
    if p1 >= ACCEPT:
        rec.update(acted=True, correct=gl, path="main")
    elif p1 > 1 - ACCEPT:
        p2 = noul_p(tables["tev1"], cid, q)
        p3 = noul_p(tables["lml"], cid, q)
        conf = [p for p in (p2, p3) if p is not None and max(p, 1 - p) >= HIGH]
        if len(conf) >= 2 and len({p >= 0.5 for p in conf}) == 1:
            dir_true = conf[0] >= 0.5
            rec.update(acted=True, correct=(gl if dir_true else not gl), cons=True, path="cons")
        elif len(conf) == 1 and p2 is not None and p3 is not None:
            other = p3 if conf[0] == p2 else p2
            rec["path"] = "conflict" if abs(other - p1) <= DELTA else "review"
    else:
        rec["path"] = "reject"
    out.append(rec)

n = len(out)
assert n == 600, n


def stats(rows_):
    acted = [r for r in rows_ if r["acted"]]
    cons = [r for r in rows_ if r["cons"]]
    main = [r for r in rows_ if r["path"] == "main"]
    return {
        "acted_pct": len(acted) / len(rows_),
        "acted_acc": sum(r["correct"] for r in acted) / len(acted) if acted else None,
        "cons_n": len(cons),
        "cons_acc": sum(r["correct"] for r in cons) / len(cons) if cons else None,
        "main_n": len(main),
        "main_acc": sum(r["correct"] for r in main) / len(main) if main else None,
    }


pt = stats(out)
rng = random.Random(0)
B = 10000
boot = []
for _ in range(B):
    sample = [out[rng.randrange(n)] for _ in range(n)]
    boot.append(stats(sample))


def ci(key):
    vals = sorted(b[key] for b in boot if b[key] is not None)
    lo = vals[int(0.025 * len(vals))]
    hi = vals[int(0.975 * len(vals)) - 1]
    return lo, hi


print(f"n = {n}")
print(f"acted coverage : {pt['acted_pct']*100:.1f}%  95% CI [{ci('acted_pct')[0]*100:.1f}, {ci('acted_pct')[1]*100:.1f}]")
print(f"acted accuracy : {pt['acted_acc']*100:.1f}%  95% CI [{ci('acted_acc')[0]*100:.1f}, {ci('acted_acc')[1]*100:.1f}]")
print(f"consensus n    : {pt['cons_n']}  (point)  95% CI [{ci('cons_n')[0]}, {ci('cons_n')[1]}]")
print(f"consensus acc  : {pt['cons_acc']*100:.1f}%  95% CI [{ci('cons_acc')[0]*100:.1f}, {ci('cons_acc')[1]*100:.1f}]")
print(f"main accepts   : {pt['main_n']} at {pt['main_acc']*100:.1f}%  (0.9-ish upper bound ~{pt['main_n'] and (1 - 3/pt['main_n'])*100:.1f}% by rule of three)")