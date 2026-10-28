# eyewright - Python to Rust core port

Branch: feat/rust-core. Python is still the default implementation.
Only the decision core is ported: server, MCP, generative engine and
supervisor are not.

## Port card

Source:       eyewright/gate.py + eyewright/decide.py (423 LOC)
Target:       Rust 1.99, crate rust/, binary eyewright.exe
Entry points: gate --state S --question Q --config P
              ask --state S --question Q [--choices J | --levels J]
                  [--engine typed] --config P
Oracle:       parity/run.py, 22 cases against a stub engine over real HTTP

## Build and parity

    cd rust; cargo build --release
    .venv/Scripts/python.exe parity/run.py

The harness starts a fresh stub engine per case, writes a temp config, and
runs each CLI as a subprocess. Compared: exit code, canonical JSON stdout,
and required substrings in the raw stdout. Error text is normalized to <ERR>
because wording is not behavior; presence and the resulting decision are.

## Oracle design

- stub_engine.py is a real HTTP server. Its script maps a model name to a
  list of steps: a probability, an error status, a sleep, or a raw body.
  Both implementations call it, so request shape, timeouts and error
  handling are part of the comparison.
- cases.json covers every decision branch: accept, review-low, both
  consensus directions, review-conflict (two confident and one confident
  plus a close other), review-weak, review-no-signal, consult error,
  retry, fallback, review-policy, error-policy, none, timeout, threshold
  overrides, both config guards, and all three ask kinds plus an engine
  error.
- Goldens are captured from Python only (parity/run.py --capture).
  Python run twice is byte-identical (parity/run.py --side py).

## Slice plan

1. DONE  config + guards + HTTP eyes + decide_gate + ask (typed path)
2.       generative engine + engine=auto fallback
3.       serve: /health, /health/deep, /v1/gate, /v1/ask, token,
         body cap, TLS
4.       mcp stdio
5.       supervisor/tray - not planned; platform UI with no cheap oracle

## Deviations

D1  serve, mcp, the generative engine and the supervisor are absent.
D2  Uncaught errors: Python prints a traceback, Rust prints
    "eyewright: <msg>". Exit code 1 in both.
D3  engine=auto has no generative fallback yet; it errors instead.
D4  JSON formatting and key order differ. The object is the contract; the
    harness canonicalizes before comparing.
D5  argmax tie-break: Python uses dict insertion order, Rust uses sorted
    keys. Only reachable with tied probabilities and no explicit choice.
D6  round-half ties: Python uses banker's rounding, Rust multiplies and
    rounds. Only reachable at exact .00005 boundaries.
A1  --version was added (Python has no such flag). Harmless addition.

## Evidence

- PARITY 22/22 against goldens captured from the untouched Python CLI.
- Python determinism: 22/22 across two consecutive runs.
- Mutation-tested: flipping the consensus direction check to accept any
  direction turns the harness red (consensus-reject vs review-conflict).
- The first harness draft was vacuous: the stub bound an ephemeral port but
  the config pointed at a pre-picked one, so every request failed and the
  goldens recorded the failure path. The mutation test caught it. Fixed:
  the stub's actual port is used.
