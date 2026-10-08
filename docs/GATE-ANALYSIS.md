# Gate analysis: committee vs laya-TD alone (2026-10-06)

Question: in the loop's **decide** stage (auto-accept / keep iterating / flag for review), does
the trio (laya-TD + tev1:4b + laya-multilingual) beat **laya-TD alone** enough to justify the
hardware and latency? Measured on the 2,000-decision typed-decisions replay (no new inference).

## Accuracy at matched coverage

The committee auto-accepts on `unanimous` + `majority-main` tiers (73.9% of decisions). At the
*same* 73.9% coverage, thresholding a single model's confidence:

| gate | coverage | accuracy among accepted |
|---|---|---|
| **committee tiers** | 73.9% | **0.8213** |
| laya-TD alone (confidence) | 73.9% | 0.8165 |
| tev1:4b alone (confidence) | 73.9% | 0.7468 |

**Gain over laya-TD alone: +0.5 points.** At 50% coverage, laya-TD's own confidence gate already
reaches 0.882, better than the committee at its fixed 73.9%.

## Where the tiers actually help

| tier | share | main's accuracy in tier |
|---|---|---|
| unanimous | 27.2% | 0.873 |
| majority-main | 46.7% | 0.791 |
| split | 13.9% | 0.572 |
| majority-nonmain | 12.2% | 0.653 (majority itself: 0.245) |

- Decline set (26.2%) has main accuracy 0.61 - a useful review queue.
- `majority-nonmain` is a **red flag, not a vote**: when the two weak members agree against main,
  the majority is right only 24.5% of the time; main is right 65.3%. Never follow it; use it to
  route to review.

## Cost

| option | compute | latency per decision | footprint |
|---|---|---|---|
| laya-TD alone | CPU, 421M encoder | ~30-40 ms (batched) | ~1.5-2 GB RAM, no GPU |
| + tev1:4b | GPU via Ollama | +0.3-3 s + model swap/unload churn | +4.5 GB model, competes with gemma4/coderx for 16 GB VRAM |
| + laya-multilingual | CPU, 322M encoder | +~30-50 ms | +~1 GB RAM; near-zero value on English (0.35 zero-shot) |

In the loop, decide runs once per iteration; the act stage is 30-90 s, so raw latency matters less
than **model-swap churn**: every additional Ollama model in the rotation can force load/unload
between gemma4 and coderx.

## Recommendation

1. **Default gate: laya-TD alone**, accept on confidence, review below threshold.
2. **Cascade, not always-trio**: when laya's confidence is low, *then* ask tev1:4b; agree = accept,
   disagree = review. That recovers the committee's review-queue value at a fraction of the cost -
   and it is exactly the routing-cascade pattern an agent control plane's M3 Router is specified for.
3. **Drop laya-multilingual from English loops**; keep it configured for multilingual states only.
4. Keep the full-trio policy available as a config switch for comparison runs.

## Caveats

- The typed-decisions benchmark is a proxy for "is this loop artifact done?"; the loop's observe
  stage (gemma4) already does semantic checking, so the gate's marginal job is calibrated
  confidence about stopping - which is where laya-TD is strongest.
- CLM-8B (best-of-N ranking) is the real upgrade for the decide stage: it ranks candidate
  artifacts/next-actions, which is richer than a yes/no gate.

Files: `gate_analysis.py` (this analysis), `ensemble.py` (committee policy), `ENSEMBLE.md` (the
2,000-decision replay).