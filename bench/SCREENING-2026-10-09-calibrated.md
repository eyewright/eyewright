# Screening run: Jev / Gemma / Jevify vs eyewright on the 600-noul gate proxy (2026-10-09)

Same rows and policy as the original eyewright-vs-laya comparison (THREE-EYE.md):
main accept >= 0.75, reject <= 0.25, uncertain band consults; consensus = >= 2
confident consults (>= 0.9) agreeing (majority for triples); conflict = one confident
+ another consult within 0.05 of main.

**Screening, not confirmatory** — see `RIGOR.md`. Generative candidates' confidences
are self-reported (uncalibrated); `jev-router` answers are routed to upstream models;
`jev-1.13` is called through the native OpenRouter decisions API (`--zdr`).

## Solo stats (600 noul decisions)

| model | n | acc | >=0.9 | Brier | ECE |
|---|---|---|---|---|---|
| laya-typed-decisions | 600 | 0.8567 | 0.0 | 0.1436 | 0.1921 |
| tev1:4b | 600 | 0.7883 | 0.45 | 0.1528 | 0.0495 |
| laya-multilingual | 600 | 0.4967 | 0.598 | 0.4117 | 0.3757 |
| von (retired) | 600 | 0.6133 | 0.0 | 0.2473 | 0.1246 |
| gemma-raw * | 600 | 0.8233 | 0.858 | 0.1615 | 0.132 |
| gemma-cal * | 600 | 0.8233 | 0.423 | 0.1618 | 0.1167 |
| router-raw * | 598 | 0.8194 | 0.554 | 0.1353 | 0.0703 |
| router-cal * | 598 | 0.8194 | 0.333 | 0.1228 | 0.0407 |
| jev113-raw * | 600 | 0.7833 | 0.122 | 0.139 | 0.0805 |
| jev113-cal * | 600 | 0.815 | 0.375 | 0.1293 | 0.0473 |

\* generative candidate (or native decisions API): confidence is the model's own, not a calibrated posterior.

## Gate table (same policy)

| config | acted n | acted % (95% CI) | acted acc (95% CI) | consensus n/acc | conflict | not-acted\* |
|---|---|---|---|---|---|---|
| incumbent: laya-typed-decisions / tev1:4b + laya-multilingual | 142 | 23.7% [20.3–27.2] | 90.8% [85.7–95.1] | 87/85.1% | 24 | 434 |
| laya-typed-decisions / tev1:4b + laya-multilingual + gemma-raw | 250 | 41.7% [37.5–45.7] | 87.6% [83.3–91.7] | 195/84.1% | 81 | 269 |
| laya-typed-decisions / tev1:4b + laya-multilingual + gemma-cal | 173 | 28.8% [25.2–32.5] | 90.8% [86.2–94.8] | 118/86.4% | 99 | 328 |
| laya-typed-decisions / tev1:4b + laya-multilingual + router-raw | 216 | 36.0% [32.0–39.8] | 90.3% [86.3–94.1] | 161/87.0% | 39 | 345 |
| laya-typed-decisions / tev1:4b + laya-multilingual + router-cal | 156 | 26.0% [22.5–29.5] | 89.7% [84.6–94.1] | 101/84.2% | 44 | 400 |
| laya-typed-decisions / tev1:4b + laya-multilingual + jev113-raw | 145 | 24.2% [20.8–27.7] | 91.0% [85.9–95.2] | 90/85.6% | 65 | 390 |
| laya-typed-decisions / tev1:4b + laya-multilingual + jev113-cal | 151 | 25.2% [21.7–28.7] | 91.4% [86.5–95.5] | 96/86.5% | 84 | 365 |
| laya-typed-decisions / tev1:4b + laya-multilingual + router-cal + gemma-cal | 182 | 30.3% [26.7–34.2] | 90.1% [85.6–94.1] | 127/85.8% | 104 | 314 |
| laya-typed-decisions / tev1:4b + laya-multilingual + router-raw + gemma-raw | 268 | 44.7% [40.5–48.7] | 88.4% [84.6–92.2] | 213/85.4% | 80 | 252 |
| gemma-raw main / tev1:4b + laya-multilingual | 323 | 53.8% [49.7–57.8] | 80.8% [76.4–85.0] | 0/- | 0 | 277 |
| gemma-cal main / tev1:4b + laya-multilingual | 177 | 29.5% [26.0–33.2] | 85.9% [80.4–90.7] | 77/83.1% | 36 | 387 |
| router-raw main / tev1:4b + laya-multilingual | 364 | 60.9% [56.9–64.7] | 78.0% [73.8–82.3] | 6/50.0% | 2 | 232 |
| router-cal main / tev1:4b + laya-multilingual | 240 | 40.1% [36.5–44.0] | 89.2% [85.0–92.7] | 39/71.8% | 5 | 353 |
| jev113-raw main / tev1:4b + laya-multilingual | 195 | 32.5% [28.7–36.2] | 91.3% [87.1–94.9] | 61/78.7% | 15 | 390 |
| jev113-cal main / tev1:4b + laya-multilingual | 216 | 36.0% [32.2–39.8] | 88.9% [84.4–92.9] | 47/74.5% | 11 | 373 |
| reference: laya-typed-decisions / tev1:4b + laya-multilingual + von | 142 | 23.7% [20.3–27.2] | 90.8% [85.7–95.1] | 87/85.1% | 36 | 422 |

\* not-acted = main-rejects (p <= 0.25) + review paths (conflicts counted separately).

