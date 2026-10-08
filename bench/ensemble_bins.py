"""Does the trio help where the main model is least confident? Bin main's confidence."""
import collections
import json
import math

import ensemble as E

cases = {json.loads(l)["id"]: json.loads(l) for l in open("cases.jsonl", encoding="utf-8")}
tables = {m: E.load_answers(p) for m, p in E.DEFAULT_FILES.items()}
members = ["laya-typed-decisions", "tev1:4b", "laya-multilingual"]
MAIN = "laya-typed-decisions"

rows = []
for cid, c in cases.items():
    for q, gold in c["gold"].items():
        gl = gold.get("label")
        if gl is None:
            continue
        a = tables[MAIN].get(cid, {}).get(q)
        if not isinstance(a, dict):
            continue
        conf = a.get("confidence") or a.get("answer_confidence")
        if conf is None:
            probs = E.norm_probs(a)
            conf = max(probs.values()) if probs else 0.0
        ml = E.norm_label(a)
        labels = {m: E.norm_label(tables[m].get(cid, {}).get(q) or {}) for m in members}
        tally = collections.Counter(v for v in labels.values() if v is not None)
        if not tally:
            continue
        top, top_n = tally.most_common(1)[0]
        n = sum(tally.values())
        if top_n == n and len(tally) == 1:
            tier = "unanimous"
        elif top_n >= math.ceil(n * 2 / 3):
            tier = "majority-main" if top == ml else "majority-nonmain"
        else:
            tier = "split"
        policy = top if top_n >= 2 else ml
        rows.append({
            "conf": float(conf or 0.0),
            "main": str(ml) == str(gl),
            "policy": str(policy) == str(gl),
            "tier": tier,
        })

rows.sort(key=lambda r: r["conf"])
qsize = len(rows) // 4
print(f"total decisions: {len(rows)}   main confidence quartiles:")
for i in range(4):
    part = rows[i * qsize:(i + 1) * qsize] if i < 3 else rows[3 * qsize:]
    if not part:
        continue
    main_acc = sum(r["main"] for r in part) / len(part)
    pol_acc = sum(r["policy"] for r in part) / len(part)
    tier_mix = collections.Counter(r["tier"] for r in part)
    lo, hi = part[0]["conf"], part[-1]["conf"]
    print(f"  Q{i + 1} conf {lo:.3f}-{hi:.3f}  n={len(part):<5} main={main_acc:.4f}  trio={pol_acc:.4f}  tiers={dict(tier_mix)}")

print()
print("accuracy by tier (main vs policy):")
by_tier = collections.defaultdict(list)
for r in rows:
    by_tier[r["tier"]].append(r)
for t, part in sorted(by_tier.items()):
    print(f"  {t:<18} n={len(part):<5} main={sum(r['main'] for r in part) / len(part):.4f}  trio={sum(r['policy'] for r in part) / len(part):.4f}")