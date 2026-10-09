# Screening run: Jev / Gemma / Jevify on the 600-noul gate proxy (2026-10-09)

Same rows and policy as the original Oracle-vs-laya comparison (THREE-EYE.md):
main accept >= 0.75, reject <= 0.25, uncertain band consults both; consensus = both
>= 0.9 confident and agreeing; conflict = one confident + other within 0.05 of main.

**Screening, not confirmatory** — see `RIGOR.md`. Generative candidates' confidences
are self-reported (uncalibrated); `typesafe/jev-router` answers are routed to upstream
models (recorded per call).

## Solo stats (600 noul decisions)

| model | n | acc | >=0.9 | Brier | ECE |
|---|---|---|---|---|---|
| laya-typed-decisions | 600 | 0.8567 | 0.0 | 0.1436 | 0.1921 |
| tev1:4b | 600 | 0.7883 | 0.45 | 0.1528 | 0.0495 |
| laya-multilingual | 600 | 0.4967 | 0.598 | 0.4117 | 0.3757 |
| von (retired) | 600 | 0.6133 | 0.0 | 0.2473 | 0.1246 |
| jev-router * | 598 | 0.8194 | 0.554 | 0.1353 | 0.0703 |
| jevify-gemma * | 598 | 0.8177 | 0.908 | 0.1687 | 0.1506 |
| gemma4:12b * | 600 | 0.8233 | 0.858 | 0.1615 | 0.132 |

\* generative candidate: confidence is the model's own estimate, not a calibrated posterior.

## Gate table (same policy)

| config | acted n | acted % (95% CI) | acted acc (95% CI) | consensus n/acc | conflict | review |
|---|---|---|---|---|---|---|
| incumbent: laya / tev1 + laya-ml | 142 | 23.7% [20.3–27.2] | 90.8% [85.7–95.1] | 87/85.1% | 13 | 445 |
| laya / tev1 + jev-router | 142 | 23.7% [20.2–27.2] | 99.3% [97.7–100.0] | 87/98.9% | 3 | 455 |
| laya / tev1 + jevify-gemma | 211 | 35.2% [31.3–39.0] | 93.8% [90.5–97.0] | 156/91.7% | 18 | 371 |
| laya / tev1 + gemma4:12b | 206 | 34.3% [30.3–38.2] | 94.7% [91.4–97.7] | 151/92.7% | 17 | 377 |
| jev-router main / tev1 + laya-ml | 364 | 60.9% [56.9–64.7] | 78.0% [73.8–82.3] | 6/50.0% | 2 | 232 |
| jevify-gemma main / tev1 + laya-ml | 326 | 54.5% [50.5–58.4] | 80.1% [75.8–84.3] | 0/- | 0 | 272 |
| gemma4:12b main / tev1 + laya-ml | 323 | 53.8% [49.7–57.8] | 80.8% [76.4–85.0] | 0/- | 0 | 277 |
| reference: laya / tev1 + von | 55 | 9.2% [7.0–11.7] | 100.0% [100.0–100.0] | 0/- | 19 | 526 |

## jev-router upstream models (what it routed to)

- deepseek/deepseek-v4.1-flash: 520 calls
- google/gemini-3.8-flash: 100 calls
- openai/gpt-6.1-sol: 2 calls

