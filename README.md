# oracle

**The Oracle** — the decision core of the local-agent stack. A committee of local
decision models behind one callable: used at the *decide* step of
[Orbit](../orbit), and available to any program or AI harness.

- **Third eye (main):** `laya-typed-decisions` — local specialist, 0.766 acc /
  Brier 0.019 on the typed-decisions bench.
- **Two sensory eyes (consults):** `tev1:4b` + `laya-multilingual`. In the
  0.25–0.75 uncertain band both consult; `>= 2` confident (`>= 0.9`) and
  agreeing → consensus; one confident + another within 0.05 of main →
  review-conflict → the caller gathers more evidence.

## Four ways to call it

**Python**
```python
from oracle import ask

result = ask(cfg, "a = 1, b = 2", "Which relation holds?",
             choices={"a_bigger": "a is bigger", "b_bigger": "b is bigger"})
# -> {"kind": "choice", "answer": "b_bigger", "confidence": 0.0038, ...}
```

**CLI**
```powershell
uv run oracle ask  --state "The sky is blue." --question "Is the statement true?"
uv run oracle ask  --state "a = 1, b = 2" --question "Which relation holds?" --choices '{"a_bigger":"a is bigger","b_bigger":"b is bigger"}'
uv run oracle gate --state "..." --question "Is the task complete?"
```

**HTTP** (for any language)
```powershell
uv run oracle serve --port 8090
# GET  /health
# POST /v1/gate  {"state": "...", "question": "..."}                  -> {p_done, decision, trace}
# POST /v1/ask   {"state": "...", "question": "...", "choices"?: {}}  -> {kind, answer, confidence, trace}
```

**MCP** (for any AI harness; needs the `mcp` extra)
```powershell
uv run --extra mcp oracle mcp
# tools: oracle_gate(state, question), oracle_ask(state, question, choices?)
```
Smoke test: `uv run --extra mcp python tests/mcp_smoke.py`.

Config for all four faces: `examples/gate.json` (primary + consults +
thresholds). Pass `--config <path>` elsewhere.

## What "any decision" means here

- **Yes/no** (no `choices`): the full three-eye policy runs — the committee
  decides, and the trace shows every eye.
- **Choose one** (`choices`) and **rate** (`levels`): the primary decision
  model answers; committee policy is defined for yes/no.
- **Open-ended questions** with no typed answer: reserve for the *generative
  adjudicator* engine behind the same `ask` facade (the decide-engine shootout
  ticket). Where a deterministic check exists (`a > b`), call the check — the
  Oracle is for judgment, not arithmetic.

Gate confidence on any von map must read the pre-band posterior (`noul_raw`);
von is retired from the consult roster (2026-10-06). See `docs/THREE-EYE.md`.

## Layout

- `oracle/gate.py` — three-eye policy (`decide_gate`) + systemone clients.
- `oracle/decide.py` — `ask()`: one call, any typed decision.
- `oracle/server.py` — `oracle serve` HTTP service.
- `oracle/mcp_server.py` — `oracle mcp` stdio MCP tools.
- `oracle/cli.py` — `oracle gate|ask|serve|mcp`.
- `bench/` — validation bench + saved responses; `docs/` — THREE-EYE,
  GATE-ANALYSIS, RESULTS, ENSEMBLE.

## Services it talks to

| service | address | notes |
|---|---|---|
| laya-serve | `127.0.0.1:8000` | key file in `the private research repo/decision-bench/`; `"model":"multilingual"` forces that checkpoint |
| Ollama | `127.0.0.1:11434` | `tev1:4b` via `/v1/systemone` |
| von | `127.0.0.1:8001` | `von-sdk`; retired as a consult |

## Roadmap

1. ✅ `oracle ask` (package + CLI) and `oracle serve` (HTTP).
2. ✅ `oracle mcp` (stdio MCP: `oracle_gate`, `oracle_ask`).
3. Next: wire as a verifier provider into an agent control plane's Audit plane / control-plane's
   verifier family (advisory, never the truth); generative engine behind `ask`.