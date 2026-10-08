"""Export typed-decisions test split to cases.jsonl with parsed state/questions/gold."""
import pandas as pd
import json

SRC = r"D:\datasets\typed-decisions\all\test-00000-of-00001.parquet"
OUT = "cases.jsonl"

df = pd.read_parquet(SRC)
with open(OUT, "w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        rec = {
            "id": row["id"],
            "workflow": row["workflow"],
            "state": json.loads(row["state"]),
            "questions": json.loads(row["questions"]),
            "gold": json.loads(row["gold"]),
            "n_questions": int(row["n_questions"]),
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"wrote {len(df)} cases -> {OUT}")