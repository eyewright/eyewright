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
# POST /v1/ask   {"state": "...", "question": "...", "choices"?|"levels"?, "engine"?: "generative"|"auto"}  -> {kind, answer, confidence, ...}
```

**MCP** (for any AI harness; needs the `mcp` extra)
```powershell
uv run --extra mcp oracle mcp
# tools: oracle_gate(state, question), oracle_ask(state, question, choices?, engine?)
```
Smoke test: `uv run --extra mcp python tests/mcp_smoke.py`.

Wired into OpenCode + Cursor on this machine. Use the **venv exe directly** so a
harness reload never triggers a `uv sync`/lock cycle:

```jsonc
"oracle": {
  "type": "local",
  "command": ["C:/Users/kcpat/projects/oracle/.venv/Scripts/oracle.exe", "mcp",
              "--config", "C:/Users/kcpat/projects/oracle/examples/gate.json"],
  "cwd": "C:/Users/kcpat/projects/oracle"
}
```

Setup: `uv sync --extra mcp` once so the venv has the `mcp` extra.

Config for all four faces: `examples/gate.json` (primary + consults +
thresholds). Pass `--config <path>` elsewhere.

## Engines behind `ask`

| engine | what runs | notes |
|---|---|---|
| `typed` (default) | yes/no: the three-eye committee; choose/rate: the primary decision model | specialist domain; committee trace |
| `generative` | a local LLM (`gemma4:12b` via the config's `generative` block) with a strict JSON contract | returns answer + reason; confidence is the model's own estimate — **not calibrated yet** (`"calibrated": false`) |
| `auto` | typed first; generative fallback when the typed path errors or has no signal | needs a `generative` block |

```powershell
uv run oracle ask --engine generative --state "a = 1, b = 2" --question "Is b greater than a?"
# -> {"kind": "noul", "answer": "yes", "confidence": 1.0, "reason": "...", "calibrated": false}
uv run oracle ask --engine auto --state "..." --question "..."
```

Where a deterministic check exists (`a > b`), call the check — the Oracle is for
judgment, not arithmetic.

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
| laya-serve | `127.0.0.1:8000` | key file in `model-lab/decision-bench/`; `"model":"multilingual"` forces that checkpoint |
| Ollama | `127.0.0.1:11434` | `tev1:4b` via `/v1/systemone` |
| von | `127.0.0.1:8001` | `von-sdk`; retired as a consult |

## Roadmap

1. ✅ `oracle ask` (package + CLI) and `oracle serve` (HTTP).
2. ✅ `oracle mcp` (stdio MCP: `oracle_gate`, `oracle_ask`) — wired into the
   OpenCode and Cursor configs.
3. ✅ Generative engine behind `ask` (`--engine generative` / `auto`).
4. Next: post-hoc calibration of the generative engine (ticket path D); wire as
   a verifier provider into ctxd's Audit plane / control-plane's verifier
   family (advisory, never the truth).