# Gate on noul_raw, not banded noul

Status: open
Source: mining S1-D0018, shard-1.md.
Repo: C:\Users\kcpat\projects\eyewright.

## Evidence

The band rule clamps the calibrated posterior, which is why von appeared never
to reach 0.9 and its accuracy read as 0.413 instead of 0.613. `noul_raw`, the
calibrated posterior meant for gating, is already present in the shipped
responses. `eyewright/gate.py` reads the banded value at three call sites:
`systemone_ollama` (line 97), `systemone_http` (line 117), and
`openrouter_decisions` (line 150). `README.md:168` already states the rule, so
the code and the doc disagree.

Candidate text: "noul under band mode is clamped (that is why von never reaches
0.9), while noul_raw - the calibrated posterior meant for gating - is already
present in the shipped responses".

## Action

Read `noul_raw` first and fall back to `noul` only when `noul_raw` is absent.
Apply the same change to all three eye adapters. Pin `"model":
"typed-decisions"` in the gate configs and the server descriptor so a config
that omits `model` cannot silently use the base English checkpoint.

## Acceptance

- A test feeds a response where `noul` is clamped and `noul_raw` is 0.95 and
  asserts the gate passes.
- A response with only `noul` still works through the fallback.
- Every shipped gate config names `typed-decisions`.
