# Rigor notes: where the 600-noul bench stands (2026-10-09)

**Verdict: this is a screening bench, not a confirmatory benchmark.** It is good
for ranking candidates cheaply under a fixed protocol; it should not carry
adoption claims ("X is better") without the upgrades below. Keep using it for
fast comparisons — label results *exploratory*.

## What is already right

- Decision models are called through their **native decision APIs** (`/v1/systemone`),
  not chat-prompted.
- **Raw responses are committed** per candidate (`responses-*.jsonl`) — re-scorable.
- Calibration discipline: refits are fitted on the **train** split, scored on test.
- Local models are versioned by **digest** (model-lab snapshots); protocol written
  down (THREE-EYE.md).
- The bench targets the gate's exact shape (noul confidence), with cost/latency
  considered in GATE-ANALYSIS.

## Known weaknesses

1. **Test-set reuse (selection leakage).** The 600 rows selected the consult pair,
   the thresholds, the von verdict, and now the Jev/Gemma roster. Every round turns
   test into dev. No frozen holdout remains.
2. **No uncertainty reported.** Example bootstrap on the incumbent row
   (`stats_ci.py`): acted coverage 23.7% [20.3, 27.2]; acted accuracy 90.8%
   [85.8, 95.3]; consensus 87 firings [70, 104] at 85.1% [77.2, 92.2]. The
   "+0.5 pt committee vs single gate" (GATE-ANALYSIS) is ~7 decisions out of
   1,478 — noise.
3. **Proxy labels, unaudited.** Gold is teacher-generated (3 samples); no human
   recheck, no inter-rater agreement. The ticket's own "loop-artifact holdout"
   is the missing external-validity piece.
4. **Single operating point.** No coverage-risk curves, no reliability diagrams;
   Brier/ECE reported ad hoc.
5. **Mixed confidence kinds.** Decision models emit posteriors; generative
   candidates (gemma, Jev-over-API, Jevify) emit **self-reported** confidence.
   Thresholding both at 0.75/0.9 compares different objects until the generative
   side is calibrated (tagged `"calibrated": false` in `eyewright.ask`).
6. **Prompt / API drift.** LLM candidates are prompt-sensitive; OpenRouter models
   change under the same id (`typesafe/jev-router` even routes to varying upstream
   models, dynamic pricing). No paraphrase ablation, seeds, or version pinning.
7. **Field/scope traps already hit once.**
   - Gate on `noul_raw` (pre-band), not band `noul` (clamped to [0.80,0.85] /
     [0.15,0.20] — cannot pass 0.9).
   - Scope rows explicitly: the "0.413" von row is the full 2,000-decision average;
     the gate table is noul-only (0.613).

## Upgrade path (ordered by ROI)

1. **Protocol freeze** — `BENCH.md`: field definitions, prompts, decode params,
   thresholds, primary metric, decision rule; roles (screening vs confirmatory).
2. **Role separation** — keep the 600 as screening/dev; iterate on train-derived
   rows; reserve a frozen holdout; build the **loop-artifact holdout** (real
   artifacts, done/not-done + defects).
3. **Stats as standard** — bootstrap CIs; paired McNemar vs incumbent; Holm
   correction across candidates; report n and intervals everywhere.
4. **Label audit** — human re-adjudicate ~100 rows; report agreement; bound
   conclusions by label noise.
5. **Curves, not cells** — coverage-risk (accuracy vs acted %) as the headline;
   reliability diagrams; cost/latency columns; adopt on dominance, not one cell.
6. **Robustness** — 3 prompt paraphrases x 2 seeds for generative candidates;
   option-order shuffle; pin API model versions + dates per run.

## Candidate-specific notes (2026-10-09)

- `clef-flash` is blocked twice: "non-finite logit" on Ollama 0.35.1 **and** 0.40.0,
  and the `9b-mxfp8` tag requires an MLX runtime (unavailable on Windows). Excluded.
- `typesafe/jev-router` (OpenRouter) is a **router**, not a fixed model: it picks
  an upstream model per request (a ping returned `openai/gpt-6-luna`) with dynamic
  pricing. Results measure the router product; upstream hits are tallied in the
  screening output.
- `jevify-gemma4-26b-a4b` is a local Gemma-4 MoE (4B active) fine-tune; via chat,
  JSON-contract prompt, `think=false`.