# DECIDE-SHOOTOUT — gate-engine ranking (2026-10-09)

Outcome of the decide-engine shootout
(`the private research repo/TICKETS/2026-10-06-decide-engine-shootout.md`). Numbers are on the
600-noul gate proxy: the test 600 (`SCREENING-2026-10-09*.md`) and a **frozen
holdout** (600 of the 1,800 train rows; calibration fit on the other 1,200 —
`HOLDOUT-2026-10-09.md`, `CALIBRATION-2026-10-09.md`). Screening, not confirmatory
(`RIGOR.md`).

## Ranked (frozen holdout, main = laya-td)

| engine (path) | acted % | acted acc | notes |
|---|---|---|---|
| local trio incumbent (`tev1 + laya-ml`) | 17.2% | 84.5% | `laya-ml` is the weak eye (~71% consensus) |
| `+ gemma4:12b` raw (D, local) | 30.8% | 83.2% | local System-2 consult |
| `+ gemma-cal` (Platt) | 19.0% | 86.8% | local, calibrated |
| raw triple `tev1 + jev-router + gemma` | **40.2%** | 88.0% | best automation |
| calibrated triple `router-cal + gemma-cal` | 22.5% | **88.9%** | best precision, lower coverage |
| `jev-1.13` as main (A) | 25.8% | 86.5% | native decisions API, ZDR, ~$0.00001/call |
| CLM-8B (B) | — | — | **not tested** |
| home-grown head (C) | — | — | **not tested** |

Test-600 continuity: incumbent 23.7% @ 90.8%; calibrated triple 30.3% @ 90.1%;
raw triple 44.7% @ 88.4%.

## Recommendation

1. **Keep the local-first default** (System-1 main + local consults) — private and free.
2. **Add a System-2 consult** (`gemma4:12b`). Highest-leverage single change is
   replacing `laya-multilingual`; adding a gemma/router consult raises holdout
   coverage 17% → 30–40% at equal-or-better acted accuracy.
3. **Calibrate only where it transfers**: `jev-1.13` yes, `jev-router` modest,
   `gemma4:12b` no. One pre-committed map (Platt); at the 0.9 policy calibration
   buys precision, not coverage.
4. **Cloud stays opt-in**: `typesafe/jev-1.13` (native decisions API, `provider.zdr`)
   is competitive as a main or precision consult — README "local-first, with an
   optional upgrade".
5. **B/C remain untested**; the **loop-artifact holdout** (real artifacts) is still
   the missing external-validity piece — it is the next decision before adoption.

Raw responses per candidate: `responses-*.jsonl` in this directory.