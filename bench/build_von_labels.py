"""Build von calibration labels from the typed-decisions TRAIN split (noul questions only).

Output: von-labels-train.jsonl, one wire question per line:
  {"state": <state>, "instructions": <noul instructions>, "choices": {"true":..., "false":...}, "gold": "true"|"false"}
"""
import json
import os
from pathlib import Path

import pandas as pd

SRC = Path(
    os.environ.get(
        "EYEWRIGHT_DATASETS",
        os.path.expanduser("~/ai-cache/datasets/typed-decisions"),
    )
) / "all" / "train-00000-of-00001.parquet"
OUT = Path(__file__).parent / "von-labels-train.jsonl"

df = pd.read_parquet(SRC)
n = 0
with OUT.open("w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        state = json.loads(row["state"])
        questions = json.loads(row["questions"])
        gold = json.loads(row["gold"])
        for qname, q in questions.items():
            if q.get("type") != "noul":
                continue
            g = gold.get(qname) or {}
            label = g.get("label")
            if label is None:
                continue
            choices = q.get("criteria") or {
                "true": "The statement holds.",
                "false": "The statement is false.",
            }
            f.write(json.dumps({
                "state": state,
                "question": {
                    "type": "noul",
                    "instructions": q.get("instructions", ""),
                    "criteria": choices,
                },
                "gold": "yes" if str(label).lower() == "true" else "no",
            }, ensure_ascii=False) + "\n")
            n += 1

print(f"wrote {n} noul calibration rows -> {OUT}")