"""Fit a confidence calibration for a consult on the train split, apply to the
frozen holdout + test, and report ECE/Brier before/after.

Fit split: cases-train-fit.jsonl (1,200 rows). Evaluation: cases-train-holdout.jsonl
(600, never fit on) and cases.jsonl (the original test 600). Two maps are fit and
compared: isotonic (PAV) and a Platt-style scalar on the logit.

    uv run python calibrate_consults.py --name gemma4:12b \
        --raw-train responses-train-gemma12b.jsonl --raw-test responses-gemma12b.jsonl \
        --out-train-cal responses-train-gemma12b-cal.jsonl \
        --out-test-cal responses-gemma12b-cal.jsonl
"""

import argparse
import json
import math

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--map", choices=["iso", "platt"], default="iso")
ap.add_argument("--raw-train", required=True)
ap.add_argument("--raw-test", required=True)
ap.add_argument("--out-train-cal", required=True)
ap.add_argument("--out-test-cal", required=True)
args = ap.parse_args()


def load_gold(path):
    g = {}
    for line in open(path, encoding="utf-8"):
        c = json.loads(line)
        for q, gold in c["gold"].items():
            if gold.get("type") == "noul":
                g[(c["id"], q)] = 1.0 if str(gold.get("label")).lower() == "true" else 0.0
    return g


def load_p(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if not r.get("ok"):
            continue
        for q, a in (r.get("resp") or {}).get("answers", {}).items():
            p = a.get("noul_raw", a.get("noul"))
            if p is not None:
                out[(r["id"], q)] = float(p)
    return out


def fit_isotonic(points):
    blocks = []
    for x, y in sorted(points):
        blocks.append([1.0, y, x])
        while len(blocks) >= 2 and blocks[-2][1] / blocks[-2][0] > blocks[-1][1] / blocks[-1][0]:
            w2, wy2, _ = blocks.pop()
            w1, wy1, _ = blocks.pop()
            blocks.append([w1 + w2, wy1 + wy2, x])
    xs = [b[2] for b in blocks]
    ys = [b[1] / b[0] for b in blocks]
    return xs, ys


def apply_isotonic(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
            return y1 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]


def _logit(p, eps=1e-6):
    p = min(1 - eps, max(eps, p))
    return math.log(p / (1 - p))


def fit_platt(points):
    a, b = 1.0, 0.0
    for _ in range(500):
        ga = gb = 0.0
        for x, y in points:
            z = a * _logit(x) + b
            q = 1 / (1 + math.exp(-z))
            ga += (q - y) * _logit(x)
            gb += (q - y)
        a -= 0.1 * ga / len(points)
        b -= 0.1 * gb / len(points)
    return a, b


def apply_platt(x, a, b):
    return 1 / (1 + math.exp(-(a * _logit(x) + b)))


def ece_brier(points, fn):
    xs = [(fn(x), y) for x, y in points]
    brier = sum((q - y) ** 2 for q, y in xs) / len(xs)
    buckets = {}
    for q, y in xs:
        conf = q if q >= 0.5 else 1 - q
        hit = (q >= 0.5) == (y == 1.0)
        b = min(int(conf * 10), 9)
        d = buckets.setdefault(b, [0.0, 0, 0])
        d[0] += conf
        d[1] += hit
        d[2] += 1
    ece = sum(v[2] / len(xs) * abs(v[0] / v[2] - v[1] / v[2]) for v in buckets.values())
    return round(ece, 4), round(brier, 4)


gold_train = load_gold("cases-train.jsonl")
gold_test = load_gold("cases.jsonl")
fit_ids = {json.loads(l)["id"] for l in open("cases-train-fit.jsonl", encoding="utf-8")}
hold_ids = {json.loads(l)["id"] for l in open("cases-train-holdout.jsonl", encoding="utf-8")}
raw_train = load_p(args.raw_train)
raw_test = load_p(args.raw_test)

fit_pts = [(p, gold_train[k]) for k, p in raw_train.items() if k in gold_train and k[0] in fit_ids]
hold_pts = [(p, gold_train[k]) for k, p in raw_train.items() if k in gold_train and k[0] in hold_ids]
test_pts = [(p, gold_test[k]) for k, p in raw_test.items() if k in gold_test]

xs, ys = fit_isotonic(fit_pts)
a, b = fit_platt(fit_pts)


def m_iso(p):
    return apply_isotonic(p, xs, ys)


def m_platt(p):
    return apply_platt(p, a, b)


print(f"# Calibration for {args.name}")
print(f"fit={len(fit_pts)}  holdout={len(hold_pts)}  test={len(test_pts)}   platt a={a:.3f} b={b:.3f}")
print(f"{'split':<10} {'raw ECE/Brier':<20} {'isotonic':<20} {'platt':<20}")
for label, pts in (("fit", fit_pts), ("holdout", hold_pts), ("test", test_pts)):
    print(f"{label:<10} {str(ece_brier(pts, lambda x: x)):<20} "
          f"{str(ece_brier(pts, m_iso)):<20} {str(ece_brier(pts, m_platt)):<20}")


def write_cal(src, dst, fn, name):
    with open(dst, "w", encoding="utf-8") as fo:
        for line in open(src, encoding="utf-8"):
            r = json.loads(line)
            for q, a in (r.get("resp") or {}).get("answers", {}).items():
                p = a.get("noul_raw", a.get("noul"))
                if p is not None:
                    c = round(fn(float(p)), 4)
                    a["noul"] = c
                    a["noul_raw"] = c
                    a["calibrated_from"] = round(float(p), 4)
                    a["calibration"] = name
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")


chosen = m_iso if args.map == "iso" else m_platt
map_name = "isotonic" if args.map == "iso" else "platt"
write_cal(args.raw_train, args.out_train_cal, chosen, map_name)
write_cal(args.raw_test, args.out_test_cal, chosen, map_name)
print(f"\nwrote {args.out_train_cal} and {args.out_test_cal} ({map_name})")