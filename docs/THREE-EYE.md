# Three-eye gate: consult-pair selection (2026-10-06)

Measured on the 600 **noul** decisions of typed-decisions (the loop gate's shape), with the loop
policy: main accept at p >= 0.75 / reject at p <= 0.25 / consult in between; consult consensus =
both consults >= 0.9 confident in the same direction; "conflict" = one confident while the other
sits within 0.05 of main.

| consults | main accepts (acc) | consensus accepts | consensus acc | acted % | acted acc |
|---|---|---|---|---|---|
| **tev1:4b + laya-multilingual** | 55 (100%) | **85** | **84.7%** | **23.7%** | **90.9%** |
| tev1:4b + tev1:0.8b | 55 (100%) | 25 | 84.0% | 13.3% | 95.0% |
| tev1:4b + von | 55 (100%) | 0 | - | 9.2% | 100% |
| von + laya-multilingual | 55 (100%) | 0 | - | 9.2% | 100% |

**Decision: consults = tev1:4b + laya-multilingual.** It is the only pair that produces the
"lessers strongly agree -> trust" signal on this proxy (85 firings at 84.7%, lifting acted coverage
from 9% to 24% while keeping acted accuracy at 90.9%).

## Von bench (why it is not a consult yet)

`wfzyx/von` 1.3 (395M ModernBERT + option-marker head, CPU, Jev API):

| model | acc | Brier | KL | notes |
|---|---|---|---|---|
| laya-typed-decisions (main) | 0.766 | 0.019 | 0.117 | specialist |
| tev1:4b | 0.657 | 0.049 | 0.354 | |
| tev1:0.8b | 0.461 | 0.083 | 0.626 | |
| **von 1.3** | **0.413** | **0.082** | **0.444** | full-bench avg; noul-only acc 0.613 (the gate shape) |
| laya-multilingual | 0.352 | 0.155 | 1.089 | consult value comes from *agreement*, not solo accuracy |

Von's own card warns that out-of-domain ranking degrades and that only labels/a refit rescue it.
Keep it as: (a) a candidate after calibration/refit on our labels (`von calibrate`), (b) a
decide-engine for agent/tool domains closer to its training, (c) a base for a home-grown head.

### Von calibrate result (2026-10-06)

`von calibrate` on 1,800 labeled noul rows from the typed-decisions **train** split (frozen
weights, CPU, 5-fold CV; ~10 min). Calibration changes confidence only, never answers:

| confidence map | ECE | NLL (in-sample) |
|---|---|---|
| raw (temperature 1) | 0.266 | 1.865 |
| shipped map | 0.085 | 0.665 |
| scalar refit | 0.098 | 0.659 |
| **feature map refit** | **0.069** | **0.638** |

Winner: the feature map (CV-NLL 0.6428 vs scalar 0.6591). Map: bias 185.83, entropy -27.47,
log_tokens -296.38, n_options 48.52, clamped to [0.3, 12]. Saved to `von-calibration.json`;
serve picks it up via `VON_CALIBRATION`. Gate-level effect (consensus firings / acted accuracy as a consult) is measured by
`run_von_noul.py` + `von_calibration_check.py`:

### Calibrated gate check (result)

Von solo on the 600 noul decisions: **accuracy unchanged** (0.613 both - calibration cannot
change answers); decisions at >= 0.9 confidence: 0.0% shipped -> 0.7% calibrated.

Confidences above are read from `noul_raw` (the pre-band posterior). The band rule keeps argmax
but compresses every posterior into [0.80, 0.85] / [0.15, 0.20], so band `noul` can never pass a
0.9 gate - the earlier "never reaches the 0.9 bar" note was that mechanic, not von's confidence.

The refit's train-side win does **not** transfer to the held-out decisions: top-label Brier
0.2473 -> 0.2548 and ECE 0.1246 -> 0.1252 on the 600 noul test decisions (`calib` lines of
`von_calibration_check.py`). Sharpening long states to T~0.3 bought in-sample ECE, not test
calibration.

As a consult eye with tev1:4b:

| von map | consensus-accept | consensus acc | acted % | acted acc | conflict |
|---|---|---|---|---|---|
| shipped | 0 | - | 9.2% | 100% | 19 |
| calibrated | 1 | **0.0%** | 9.3% | 98.2% | 31 |

Verdict: **retired from eyewright.** The refit improved in-sample ECE (0.085 -> 0.069) but that
does not transfer (test Brier 0.2473 -> 0.2548, ECE 0.1246 -> 0.1252); it made von only slightly
more willing to speak, its one consensus call was wrong, and its new confidence mostly surfaced
as *conflict* (19 -> 31) rather than agreement. Von remains: an agent/tool-domain
candidate, a calibration case study, and a base for the home-grown head
(`TICKETS/2026-10-06-decide-engine-shootout.md`).

Operational note: the first calibrated replay was corrupted by two concurrent replays
(duplicate watchers) interleaving appends into the same file. Calibrated outputs now write to
`C:\Users\kcpat\ai-cache\von-calibrated\`, fsync each line, validate line-by-line after the run,
and land via unique-temp + atomic replace.

## Pickle note (`option_marker.pt`)

`.pt` is a pickle container: the format is a code-execution vector *by type*. Von's SDK loads it
with `torch.load(..., weights_only=True)` (`option_marker_backend.py:549`), which restricts
unpickling to tensors and is the accepted mitigation; the backbone ships as safetensors. General
practice: trust the source, require `weights_only=True`, optionally scan with picklescan, or
convert to safetensors once. Same rule applies to any `.bin`/`.pt`/`.pth` in D:\ai-models.

## Operational notes

- laya-serve serves the multilingual checkpoint on demand: pass `"model": "multilingual"` in the
  Jev request (routing.reason = "explicit model='multilingual'"); no second server needed.
- Both servers are keyed: `decision-bench/.laya-api-key`, `decision-bench/.von-api-key`.
- clef-flash is deferred: "non-finite logit" server error on Ollama 0.35.1 (latest); retry the
  `9b-mxfp8` tag or a future Ollama version.

Reproduce: `uv run python three_eye_analysis.py` (uses saved responses; no inference).
Calibrated-von repro: `uv run python run_von_noul.py` (writes to `%USERPROFILE%\ai-cache\von-calibrated\`)
then `uv run python von_calibration_check.py`.