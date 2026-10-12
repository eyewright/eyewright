# bench

Validation bench for eyewright's gate policy. Scripts run **from this
directory** (they read the saved response files by name).

- `three_eye_analysis.py` — consult-pair selection on the 600-noul gate proxy
  (writes nothing; prints the THREE-EYE table).
- `gate_analysis.py` — committee vs laya-TD-alone at matched coverage
  (2,000-decision replay; GATE-ANALYSIS.md).
- `ensemble.py` / `ensemble_bins.py` — main-vs-trio committee analysis.
- `von_calibration_check.py` — von shipped vs calibrated on the gate proxy
  (reads the calibrated run from `%USERPROFILE%\ai-cache\von-calibrated\` when
  present; gates on `noul_raw`).
- `run_von_noul.py` — re-asks von only the noul questions (writes to the
  ai-cache dir; unique temp + atomic replace).
- `build_von_labels.py` — rebuild `von-labels-train.jsonl` from the
  typed-decisions train parquet (`%EYEWRIGHT_DATASETS%`, default
  `D:/datasets/typed-decisions`).
- `score.py`, `run_laya.py`, `run_systemone.py`, `export_cases.py` — the
  original decision-model bench harness.

Data in repo: `cases.jsonl` (400 test cases), `cases-train*.jsonl`,
`von-labels-train.jsonl`, `von-calibration.json`.

The per-model `responses-*.jsonl` are **not** committed — they are bulky and
regenerable with the runners below. Regenerate them, or restore from a local /
release copy. The derived tables live in the `*.md` files here.

Reproduce (from `bench/`):

```powershell
uv run python three_eye_analysis.py
uv run python gate_analysis.py
uv run python von_calibration_check.py
```

Keys live outside the repo (secrets): `model-lab/decision-bench/.laya-api-key`,
`.von-api-key`. The calibrated von run is written to
`%USERPROFILE%\ai-cache\von-calibrated\` (outside git).