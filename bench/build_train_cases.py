"""Build cases-train.jsonl (1,800 noul) from von-labels-train.jsonl and a
deterministic fit/holdout split (seed 0).

  cases-train.jsonl           all 1,800
  cases-train-fit.jsonl       1,200  (calibration fitting only)
  cases-train-holdout.jsonl     600  (frozen for evaluation; never fit on)
"""

import json
import random
from pathlib import Path

SRC = Path("von-labels-train.jsonl")
HOLDOUT_N = 600

rows = []
for i, line in enumerate(open(SRC, encoding="utf-8"), 1):
    r = json.loads(line)
    q = r["question"]
    gold = str(r["gold"]).strip().lower()
    label = "true" if gold in ("yes", "true", "1") else "false"
    rows.append({
        "id": f"train_{i:06d}",
        "workflow": "train",
        "state": r["state"],
        "questions": {"q": {"type": "noul",
                            "instructions": q.get("instructions", ""),
                            "criteria": q.get("criteria") or {}}},
        "gold": {"q": {"type": "noul", "label": label}},
    })

idx = list(range(len(rows)))
random.Random(0).shuffle(idx)
hold = set(idx[:HOLDOUT_N])


def dump(path, items):
    Path(path).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in items) + "\n", encoding="utf-8")


dump("cases-train.jsonl", rows)
dump("cases-train-fit.jsonl", [r for i, r in enumerate(rows) if i not in hold])
dump("cases-train-holdout.jsonl", [r for i, r in enumerate(rows) if i in hold])
print(f"train={len(rows)} fit={len(rows) - len(hold)} holdout={len(hold)}")