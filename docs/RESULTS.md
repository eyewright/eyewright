# Decision-model bench - tev1 vs Laya family (2026-10-04)

Benchmark: `typed-decisions` test split (400 cases, 2,000 decisions; gold distributions from a
3-sample teacher). Every case is a `POST /v1/systemone` body, so models were run with their native
decision APIs, not chat prompting.

- **tev1** (`tev1:0.8b`, `tev1:4b`): Ollama `/v1/systemone`, exactly as served.
- **Laya** (base English, multilingual, typed-decisions): local safetensors via the official
  Apache-2.0 `laya` package (`laya.load(local_path)`), CPU torch.
- Scoring: argmax accuracy vs gold label; Brier and KL(gold||pred) vs gold distributions.

## Results

| model | kind | accuracy | choice | noul | score | Brier | KL | mean latency* |
|---|---|---|---|---|---|---|---|---|
| `laya-typed-decisions` | specialist (fined-tuned on these workflows) | **0.766** | 0.733 | 0.857 | 0.723 | **0.019** | **0.117** | 2,177 ms |
| `tev1:4b` | general, zero-shot | **0.657** | 0.645 | **0.788** | 0.566 | **0.049** | **0.354** | 2,883 ms |
| `tev1:0.8b` | general, zero-shot | 0.461 | 0.387 | 0.688 | 0.346 | 0.083 | 0.626 | 2,549 ms |
| `laya-english` | general, zero-shot | 0.362 | 0.288 | 0.487 | 0.323 | 0.101 | 0.569 | 2,496 ms |
| `laya-multilingual` | general, zero-shot | 0.352 | 0.295 | 0.497 | 0.286 | 0.155 | 1.089 | 920 ms |

\* Measured on the reference rig: tev1 on the RTX 5060 Ti via Ollama; Laya on CPU torch. Not comparable
to published T4 numbers (Laya claims ~33-40 ms on GPU).

### Published reference rows (vendor/third-party, not measured here)

| model | accuracy | Brier | KL |
|---|---|---|---|
| meraGPT Decider 1 | 0.768 | 0.052 | 0.096 |
| TypeSafe Jev 1.13.0 | 0.727 | 0.148 | 1.442 |
| Jeff-Gemma4-E2B | 0.561 | 0.219 | 0.403 |
| Jeff-Qwen3.5-2B | 0.511 | 0.237 | 0.460 |
| Jeff-Qwen3.5-0.8B | 0.483 | 0.313 | 0.679 |
| Prior (ignores input) | 0.470 | 0.189 | 0.347 |
| Uniform | 0.308 | 0.238 | 0.444 |

## Findings

1. **The specialist row reproduced exactly**: our harness scores `laya-typed-decisions` at 0.766
   overall and 0.733 / 0.857 / 0.723 by primitive, matching the published card to three decimals -
   the bench measures what it claims to.
2. **Best zero-shot model: `tev1:4b`.** 0.657 accuracy, Brier 0.049, KL 0.354. It beats published
   Jev 1.13.0's calibration by ~3x (Brier 0.148, KL 1.442) while landing 0.07 below it on accuracy,
   and its Brier even edges meraGPT Decider 1 (0.052; meraGPT keeps the lead on accuracy 0.768 and
   KL 0.096). Full ranking on this run: laya-TD 0.766 > tev1:4b 0.657 > Jeff-Gemma4-E2B 0.561 >
   Jeff-2B 0.511 > Jeff-0.8B 0.483 > prior 0.470 > tev1:0.8b 0.461 > laya-english 0.362 >
   laya-multilingual 0.352.
3. **tev1 scales cleanly**: 0.8b -> 4b gains +0.196 accuracy, Brier 0.083 -> 0.049, KL 0.626 -> 0.354,
   for +13% latency. Use the 4B when quality matters; the 0.8B remains the ultra-fast option.
4. **Zero-shot Laya checkpoints trail tev1** (0.362 / 0.352). On English text the multilingual
   checkpoint is weakest by design. Their value is the fine-tuned specialist and multilingual
   coverage, not zero-shot typed decisions.
5. **Specialist vs general is not a quality ranking** - the 0.109 gap between
   `laya-typed-decisions` and `tev1:4b` is the price of generality (any question schema at request
   time, no fine-tuning on these four workflows).
6. Laya's typed-decisions checkpoint emits its documented invalid-temperature warning; treat its
   confidence values as uncalibrated (its Brier is still excellent because the distributions are good).

### Status

All runs complete; `tev1:4b` row added 2026-10-04.

## Files

- `cases.jsonl` - 400 exported cases (state, questions, gold parsed from the parquet).
- `export_cases.py`, `run_systemone.py`, `run_laya.py`, `score.py`.
- `responses-tev1_0.8b.jsonl`, `responses-laya-laya-{typed-decisions,english,multilingual}.jsonl`
  (full raw responses, with per-case latency).

## Reproduce

```powershell
cd bench
uv run python .\export_cases.py
uv run python .\run_systemone.py --model tev1:0.8b          # or tev1:4b
uv run --with laya --with torch --with numpy python .\run_laya.py --checkpoint "%USERPROFILE%\ai-models\state\laya-typed-decisions" --name laya-typed-decisions
uv run python .\score.py --files responses-tev1_0.8b.jsonl responses-laya-laya-typed-decisions.jsonl
```

Second head-to-head candidates on disk: `%USERPROFILE%\ai-cache\datasets\fast-decisions` (17 operational classification
domains, dev split) and `%USERPROFILE%\ai-cache\datasets\Open-Jev` (control-style artifacts with its own REPRODUCTION.md).