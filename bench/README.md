# bench

Validation bench for the Oracle's gate policy. Scripts run **from this
directory** (they read the saved response files by name).

- `three_eye_analysis.py` — consult-pair selection on the 600-noul gate proxy
  (writes nothing; prints the THREE-EYE table).
- `gate_analysis.py` — committee vs laya-TD-alone at matched coverage
  (2,000-decision replay; GATE-ANALYSIS.md).
- `ensemble.py` / `ensemble_bins.py` — main-vs-trio committee analysis.
- `von_calibration_check.py` — von shipped vs calibrated on the gate proxy
  (reads the calibrated run from `C:\Users\<user>\ai-cache\von-calibrated\` when
  present; gates on `noul_raw`).
- `run_von_noul.py` — re-asks von only the noul questions (writes to the
  ai-cache dir; unique temp + atomic replace).
- `build_von_labels.py` — rebuild `von-labels-train.jsonl` from the
  typed-decisions train parquet (`D:\datasets\typed-decisions`).
- `score.py`, `run_laya.py`, `run_systemone.py`, `export_cases.py` — the
  original decision-model bench harness.

Data: `cases.jsonl` (400 test cases), `responses-*.jsonl` (saved per model),
`von-labels-train.jsonl`, `von-calibration.json`.

Reproduce (from `bench/`):

```powershell
uv run python three_eye_analysis.py
uv run python gate_analysis.py
uv run python von_calibration_check.py
```

Keys live outside the repo (secrets): `the private research repo/decision-bench/.laya-api-key`,
`.von-api-key`. The calibrated von run is written to
`C:\Users\<user>\ai-cache\von-calibrated\` (outside git).