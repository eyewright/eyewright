"""Score the screening roster on the 600-noul gate proxy (same policy as THREE-EYE).

Solo stats + gate table (main / N consults), plus bootstrap CIs, exactly like the
original Oracle-vs-laya comparison. Generative candidates are labelled: their
confidences are SELF-REPORTED (uncalibrated).

    uv run python compare_consults.py \
        --extra "jev-1.13=responses-jev-113.jsonl" \
        --extra "jev-router=responses-jev-router.jsonl" \
        --extra "gemma4:12b=responses-gemma12b.jsonl" \
        --out SCREENING-2026-10-09.md
"""

import argparse
import json
import random

ACCEPT, HIGH, DELTA = 0.75, 0.9, 0.05
MAIN = "laya-typed-decisions"
DEFAULTS = {
    "laya-typed-decisions": "responses-laya-laya-typed-decisions.jsonl",
    "tev1:4b": "responses-tev1_4b.jsonl",
    "laya-multilingual": "responses-laya-laya-multilingual.jsonl",
    "von (retired)": "responses-von.jsonl",
}

ap = argparse.ArgumentParser()
ap.add_argument("--extra", action="append", default=[], metavar="name=path")
ap.add_argument("--cases", default="cases.jsonl")
ap.add_argument("--out", default=None)
args = ap.parse_args()

FILES = dict(DEFAULTS)
EXTRA = []
for item in args.extra:
    name, _, path = item.partition("=")
    FILES[name] = path
    EXTRA.append(name)

cases = {json.loads(l)["id"]: json.loads(l) for l in open(args.cases, encoding="utf-8")}
rows = [(cid, q, str(gold.get("label")).lower() == "true")
        for cid, c in cases.items() for q, gold in c["gold"].items()
        if gold.get("type") == "noul"]


def load_answers(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("ok"):
            out[r["id"]] = (r.get("resp") or {}).get("answers") or {}
    return out


tables = {}
for name, path in FILES.items():
    try:
        tables[name] = load_answers(path)
    except FileNotFoundError:
        pass


def noul_p(m, cid, q):
    a = tables.get(m, {}).get(cid, {}).get(q)
    if not isinstance(a, dict):
        return None
    if a.get("noul_raw") is not None:
        return float(a["noul_raw"])
    if a.get("type") == "noul" and a.get("noul") is not None:
        return float(a["noul"])
    p = (a.get("probabilities") or {}).get("true")
    return float(p) if p is not None else None


def solo(m):
    n = hit = high = 0
    brier = 0.0
    buckets = {}
    for cid, q, gl in rows:
        p = noul_p(m, cid, q)
        if p is None:
            continue
        n += 1
        hit += (p >= 0.5) == gl
        high += max(p, 1 - p) >= HIGH
        y = 1.0 if gl else 0.0
        brier += (p - y) ** 2
        conf = p if p >= 0.5 else 1 - p
        b = min(int(conf * 10), 9)
        d = buckets.setdefault(b, [0.0, 0, 0])
        d[0] += conf
        d[1] += (p >= 0.5) == gl
        d[2] += 1
    ece = sum(v[2] / n * abs(v[0] / v[2] - v[1] / v[2]) for v in buckets.values()) if n else None
    return {"n": n, "acc": round(hit / n, 4) if n else None,
            "pct090": round(high / n, 3) if n else None,
            "brier": round(brier / n, 4) if n else None,
            "ece": round(ece, 4) if ece is not None else None}


def classify(main, consults):
    """Per-row outcome of the gate policy for (main, [consults...])."""
    out = []
    for cid, q, gl in rows:
        p1 = noul_p(main, cid, q)
        if p1 is None:
            continue
        rec = {"acted": False, "correct": None, "cons": False, "conflict": False}
        if p1 >= ACCEPT:
            rec.update(acted=True, correct=gl)
        elif p1 > 1 - ACCEPT:
            ps = [(n, noul_p(n, cid, q)) for n in consults]
            conf = [(n, p) for n, p in ps if p is not None and max(p, 1 - p) >= HIGH]
            if len(conf) >= 2:
                dirs = {p >= 0.5 for _, p in conf}
                if len(dirs) == 1:
                    avg = sum(p for _, p in conf) / len(conf)
                    rec.update(acted=True, correct=(gl if avg >= 0.5 else not gl), cons=True)
                else:
                    rec["conflict"] = True
            elif len(conf) == 1:
                others = [p for n, p in ps if n != conf[0][0] and p is not None]
                rec["conflict"] = any(abs(p - p1) <= DELTA for p in others)
        out.append(rec)
    return out


def summarize(outcomes):
    acted = [r for r in outcomes if r["acted"]]
    cons = [r for r in outcomes if r["cons"]]
    return {
        "acted_n": len(acted),
        "acted_pct": len(acted) / len(outcomes),
        "acted_acc": sum(r["correct"] for r in acted) / len(acted) if acted else None,
        "cons_n": len(cons),
        "cons_acc": sum(r["correct"] for r in cons) / len(cons) if cons else None,
        "conflict": sum(r["conflict"] for r in outcomes),
        "review": sum(1 for r in outcomes if not r["acted"] and not r["conflict"]),
    }


def ci(outcomes, key, iters=2000, seed=0):
    rng = random.Random(seed)
    n = len(outcomes)
    vals = []
    for _ in range(iters):
        s = summarize([outcomes[rng.randrange(n)] for _ in range(n)])
        v = s[key]
        if v is not None:
            vals.append(v)
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def fmt_pct(x):
    return "-" if x is None else f"{x*100:.1f}%"


def build_configs():
    configs = [("incumbent: laya / tev1 + laya-ml", MAIN, ["tev1:4b", "laya-multilingual"])]
    for x in EXTRA:
        configs.append((f"laya / tev1 + {x}", MAIN, ["tev1:4b", x]))
    configs += [
        ("TRIPLE laya / tev1 + jev-1.13 + gemma4:12b", MAIN, ["tev1:4b", "jev-1.13", "gemma4:12b"]),
        ("TRIPLE laya / tev1 + jev-router + gemma4:12b", MAIN, ["tev1:4b", "jev-router", "gemma4:12b"]),
        ("laya / jev-1.13 + gemma4:12b (no tev1)", MAIN, ["jev-1.13", "gemma4:12b"]),
    ]
    for x in EXTRA:
        configs.append((f"{x} main / tev1 + laya-ml", x, ["tev1:4b", "laya-multilingual"]))
    configs.append(("reference: laya / tev1 + von", MAIN, ["tev1:4b", "von (retired)"]))
    return configs


def main():
    lines = []
    lines.append("# Screening run: Jev / Gemma / Jevify vs the Oracle on the 600-noul gate proxy (2026-10-09)")
    lines.append("")
    lines.append("Same rows and policy as the original Oracle-vs-laya comparison (THREE-EYE.md):")
    lines.append("main accept >= 0.75, reject <= 0.25, uncertain band consults; consensus = >= 2")
    lines.append("confident consults (>= 0.9) agreeing (majority for triples); conflict = one confident")
    lines.append("+ another consult within 0.05 of main.")
    lines.append("")
    lines.append("**Screening, not confirmatory** — see `RIGOR.md`. Generative candidates' confidences")
    lines.append("are self-reported (uncalibrated); `jev-router` answers are routed to upstream models;")
    lines.append("`jev-1.13` is called through the native OpenRouter decisions API (`--zdr`).")
    lines.append("")

    lines.append("## Solo stats (600 noul decisions)")
    lines.append("")
    lines.append("| model | n | acc | >=0.9 | Brier | ECE |")
    lines.append("|---|---|---|---|---|---|")
    for name in FILES:
        if name not in tables:
            continue
        s = solo(name)
        tag = "" if name in DEFAULTS else " *"
        lines.append(f"| {name}{tag} | {s['n']} | {s['acc']} | {s['pct090']} | {s['brier']} | {s['ece']} |")
    lines.append("")
    lines.append("\\* generative candidate (or native decisions API): confidence is the model's own, not a calibrated posterior.")
    lines.append("")

    lines.append("## Gate table (same policy)")
    lines.append("")
    lines.append("| config | acted n | acted % (95% CI) | acted acc (95% CI) | consensus n/acc | conflict | not-acted\\* |")
    lines.append("|---|---|---|---|---|---|---|")
    for label, m, consults in build_configs():
        if m not in tables or any(c not in tables for c in consults):
            continue
        o = classify(m, consults)
        s = summarize(o)
        pct_ci = ci(o, "acted_pct")
        acc_ci = ci(o, "acted_acc")
        lines.append(
            f"| {label} | {s['acted_n']} | {fmt_pct(s['acted_pct'])} "
            f"[{pct_ci[0]*100:.1f}–{pct_ci[1]*100:.1f}] | {fmt_pct(s['acted_acc'])} "
            f"[{acc_ci[0]*100:.1f}–{acc_ci[1]*100:.1f}] | {s['cons_n']}/{fmt_pct(s['cons_acc'])} "
            f"| {s['conflict']} | {s['review']} |"
        )
    lines.append("")
    lines.append("\\* not-acted = main-rejects (p <= 0.25) + review paths (conflicts counted separately).")
    lines.append("")

    if "jev-router" in tables:
        seen = {}
        for line in open("responses-jev-router.jsonl", encoding="utf-8"):
            r = json.loads(line)
            for a in (r.get("resp") or {}).get("answers", {}).values():
                um = a.get("upstream_model")
                if um:
                    seen[um] = seen.get(um, 0) + 1
        lines.append("## jev-router upstream models (what it routed to)")
        lines.append("")
        for k, v in sorted(seen.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {k}: {v} calls")
        lines.append("")

    text = "\n".join(lines)
    print(text)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()