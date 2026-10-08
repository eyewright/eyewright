"""Gate analysis: committee tiers vs single-model confidence gating.

Question: as a verifier/gate, does the trio buy anything over laya-TD alone, and at what
coverage? Uses the saved typed-decisions responses (no new inference).

Metrics:
- All tiers: coverage (fraction auto-accepted) and accuracy among accepted.
- Confidence gating: sort by model confidence, measure accuracy at fixed coverage points.
- Matched-coverage comparison: single-model accuracy at the same coverage the committee gives.
"""
import collections
import json
import math

import ensemble as E

cases = {json.loads(l)["id"]: json.loads(l) for l in open("cases.jsonl", encoding="utf-8")}
tables = {m: E.load_answers(p) for m, p in E.DEFAULT_FILES.items()}
MEMBERS = ["laya-typed-decisions", "tev1:4b", "laya-multilingual"]
MAIN = "laya-typed-decisions"


def conf_of(a):
    if not isinstance(a, dict):
        return 0.0
    c = a.get("confidence") or a.get("answer_confidence")
    if c is not None:
        return float(c)
    probs = E.norm_probs(a)
    return max(probs.values()) if probs else 0.0


rows = []
for cid, c in cases.items():
    for q, gold in c["gold"].items():
        gl = gold.get("label")
        if gl is None:
            continue
        a = tables[MAIN].get(cid, {}).get(q)
        if not isinstance(a, dict):
            continue
        ml = E.norm_label(a)
        labels = {}
        for m in MEMBERS:
            x = tables[m].get(cid, {}).get(q)
            labels[m] = E.norm_label(x) if isinstance(x, dict) else None
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
        t = tables["tev1:4b"].get(cid, {}).get(q)
        rows.append({
            "tier": tier,
            "main_ok": str(ml) == str(gl),
            "tev_ok": str(E.norm_label(t)) == str(gl) if isinstance(t, dict) else None,
            "main_conf": conf_of(a),
            "tev_conf": conf_of(t),
            "accept": tier in ("unanimous", "majority-main"),
            "accept_ok": str(top) == str(gl),
        })

total = len(rows)
print(f"decisions: {total}")

print("\n== committee auto-accept tiers ==")
acc_rows = [r for r in rows if r["accept"]]
print(f"  accept coverage: {len(acc_rows) / total:.3f}   accuracy among accepted: {sum(r['accept_ok'] for r in acc_rows) / len(acc_rows):.4f}")
for t in ("unanimous", "majority-main", "split", "majority-nonmain"):
    part = [r for r in rows if r["tier"] == t]
    if part:
        print(f"    {t:<18} n={len(part):<5} ({len(part) / total:.1%})  acc={sum(r['main_ok'] for r in part) / len(part):.4f} (main's own acc in tier)")

print("\n== single-model confidence gating ==")
for name, key in (("laya-TD", "main_conf"), ("tev1:4b", "tev_conf")):
    ordered = sorted(rows, key=lambda r: r[key], reverse=True)
    ok_key = "main_ok" if name == "laya-TD" else "tev_ok"
    line = [f"  {name}:"]
    for cov in (0.5, 0.739, 0.8, 0.9):
        k = int(total * cov)
        part = [r for r in ordered[:k] if r[ok_key] is not None]
        line.append(f"@{cov:.0%} acc={sum(r[ok_key] for r in part) / len(part):.4f}")
    print("   ".join(line))

print("\n== matched coverage: committee (73.9%) vs single models at the same coverage ==")
target = len(acc_rows) / total
for name, key, ok_key in (("laya-TD", "main_conf", "main_ok"), ("tev1:4b", "tev_conf", "tev_ok")):
    ordered = sorted(rows, key=lambda r: r[key], reverse=True)
    k = int(total * target)
    part = [r for r in ordered[:k] if r[ok_key] is not None]
    print(f"  {name:<8} @{target:.1%}: {sum(r[ok_key] for r in part) / len(part):.4f}")
print(f"  committee @{target:.1%}: {sum(r['accept_ok'] for r in acc_rows) / len(acc_rows):.4f}")

print("\n== what the vote would do on committee-declined rows ==")
declined = [r for r in rows if not r["accept"]]
print(f"  declined: {len(declined)} ({len(declined) / total:.1%}); main's accuracy there: {sum(r['main_ok'] for r in declined) / len(declined):.4f}")
nonmain = [r for r in declined if r["tier"] == "majority-nonmain"]
if nonmain:
    print(f"  majority-nonmain: n={len(nonmain)}; majority right {sum(r['accept_ok'] for r in nonmain) / len(nonmain):.4f}, main right {sum(r['main_ok'] for r in nonmain) / len(nonmain):.4f}")
split = [r for r in declined if r["tier"] == "split"]
if split:
    print(f"  split:            n={len(split)}; main right {sum(r['main_ok'] for r in split) / len(split):.4f}")