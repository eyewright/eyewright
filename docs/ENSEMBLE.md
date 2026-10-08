# Decision committee ("Total Recall") - main vs trio (2026-10-04/05)

Question: should decisions be made by the best single model, or by a trio with 2/3 agreement
(policy: main = highest scorer; agreements containing main = highest reliability)?

Setup: 2,000 decisions from the typed-decisions test split, all four models' saved responses
(no new inference). Members: `laya-typed-decisions` (**main**, 0.766), `tev1:4b` (0.657),
`laya-multilingual` (0.352).

## Policy results

| policy | accuracy |
|---|---|
| **main alone** | **0.7660** |
| trio majority (2/3, fallback main) | 0.7160 |
| main-veto (follow majority only when it includes main) | 0.7660 |
| unanimous-or-main | 0.7660 |
| soft fusion, mean probabilities | 0.6650 |
| soft fusion, accuracy-weighted (acc^2) | 0.7435 |

Why main-veto equals main alone: in the tiers where the majority includes main
(`majority-main`, `unanimous`), the majority label **is** main's label - the vote copies main.
The only tier where the vote differs is `majority-nonmain`, and there the vote is much worse.

## Agreement tiers as a reliability signal (this is the useful part)

| tier | n | policy acc | main acc |
|---|---|---|---|
| unanimous | 544 (27.2%) | 0.8732 | 0.8732 |
| majority-main | 933 (46.7%) | 0.7910 | 0.7910 |
| split (1/1/1) | 278 (13.9%) | 0.5719 | 0.5719 |
| majority-nonmain | 245 (12.3%) | **0.2449** | **0.6531** |

- Unanimous decisions are 11 points more accurate than main's baseline - a genuinely strong
  auto-accept signal.
- majority-main is above baseline too.
- When the two weak members agree *against* main, they are wrong ~75% of the time - main is right
  2.7x more often. The defensible action is main-veto, not majority.

## Main-confidence quartiles: can the trio rescue low-confidence cases?

| quartile | main conf | main acc | trio acc |
|---|---|---|---|
| Q1 | 0.001-0.150 | 0.6140 | 0.5780 |
| Q2 | 0.150-0.240 | 0.6860 | 0.6600 |
| Q3 | 0.241-0.556 | 0.8200 | 0.7500 |
| Q4 | 0.557-0.893 | 0.9440 | 0.8760 |

No: the trio is worse in every confidence band. Routing low-confidence decisions to the committee
does not help here.

## Conclusions

1. **Use the best model alone as the decider.** On this benchmark the trio adds no decision value,
   and strict majority is actively harmful (-5 points vs main).
2. **Use the tiers as confidence labels**, not as decision rules:
   - `unanimous` / `majority-main` -> auto-accept (79-87% expected accuracy)
   - `split` -> accept but queue for review (57%)
   - `majority-nonmain` -> main-veto + review queue (main is right 65% of the time there)
3. **For an ensemble to beat the best member, the members must be close in accuracy with
   decorrelated errors.** Here the accuracy gap (0.77 / 0.66 / 0.35) is too wide; even
   accuracy-weighted soft fusion (0.7435) loses to main alone.
4. The `tev1:0.8b` member was excluded from the core trio; adding it would weaken the vote further
   on this benchmark (0.461 accuracy). It remains useful as a cheap first pass, not a voter.

Reproduce:

```powershell
cd model-lab\decision-bench
uv run python .\ensemble.py --members laya-typed-decisions tev1:4b laya-multilingual
uv run python .\ensemble_bins.py
```

Companion long-context check ("Total Recall" recall case on the history of hand planes):
`recall/RESULTS.md` - tev1:4b scored 10/10 vs main 7/10, trio 8/10 on a single 10-question
prose-recall case; see that file for the endpoint input-cap caveat.