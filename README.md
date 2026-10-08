# oracle

**The Oracle** — the decision core of the local-agent stack. A committee of local
decision models behind one typed gate, used at the *decide* step of
[Orbit](../orbit) and by any gate that needs a judgment where a deterministic
check cannot decide.

- **Third eye (main):** `laya-typed-decisions` — local specialist, 0.766 acc /
  Brier 0.019 on the typed-decisions bench.
- **Two sensory eyes (consults):** `tev1:4b` + `laya-multilingual`. In the
  0.25–0.75 uncertain band both consult; `>= 2` confident (`>= 0.9`) and
  agreeing → consensus; one confident + another within 0.05 of main →
  review-conflict → the caller gathers more evidence.

Policy details and evidence: `docs/THREE-EYE.md`, `docs/GATE-ANALYSIS.md`,
`docs/RESULTS.md`, `docs/ENSEMBLE.md`.

## Layout

- `oracle/gate.py` — canonical gate policy (`decide_gate`) + systemone clients.
- `bench/` — the validation bench and saved responses (600-noul gate proxy,
  2,000-decision committee replay, von calibration check).
- `docs/` — THREE-EYE, GATE-ANALYSIS, RESULTS, ENSEMBLE.

## Use from Python

```python
from oracle.gate import decide_gate

cfg = {  # or take stages.decide from the orbit repo's config.json
    "accept_threshold": 0.75,
    "consult_threshold": 0.55,
    "high_confidence": 0.9,
    "match_delta": 0.05,
    "primary": {
        "name": "laya-td", "type": "systemone-http",
        "url": "http://127.0.0.1:8000/v1/systemone",
        "key_file": r"C:\Users\kcpat\OneDrive\Documents\Default Project\model-lab\decision-bench\.laya-api-key",
    },
    "consults": [
        {"name": "tev1:4b", "type": "systemone-ollama", "model": "tev1:4b"},
        {"name": "laya-multilingual", "type": "systemone-http",
         "url": "http://127.0.0.1:8000/v1/systemone", "model": "multilingual",
         "key_file": r"C:\Users\kcpat\OneDrive\Documents\Default Project\model-lab\decision-bench\.laya-api-key"},
    ],
}
p_done, trace = decide_gate(cfg, state_text, "Is the task complete and correct so far, with no remaining blockers?")
```

Note: when a von map is used, gate confidence must read the pre-band posterior
(`noul_raw`) — the band rule compresses `noul` into `[0.80, 0.85]` /
`[0.15, 0.20]`. Von is retired from the consult roster (2026-10-06); see
`docs/THREE-EYE.md`.

## Services it talks to

| service | address | notes |
|---|---|---|
| laya-serve | `127.0.0.1:8000` | key file in `model-lab/decision-bench/`; `"model":"multilingual"` forces the multilingual checkpoint |
| Ollama | `127.0.0.1:11434` | `tev1:4b` via `/v1/systemone` |
| von | `127.0.0.1:8001` | `von-sdk`; retired as a consult |

## Roadmap

1. `oracle serve` — one local HTTP endpoint (`/v1/gate`) wrapping the policy, so
   orbit/ctxd/control-plane call it deterministically.
2. MCP adapter (`oracle.gate` tool) — any harness can ask for a gate call.
3. Wire as a verifier provider into ctxd's Audit plane / control-plane's
   verifier family (advisory, never the truth; external checks decide "done").