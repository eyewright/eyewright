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
    .venv/Scripts/python.exe parity/run.py      # CLI: 34 cases
    .venv/Scripts/python.exe parity/serve.py    # HTTP: 11 requests

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
- Generative cases run the real ask_generative. Python's transport is
  redirected by patching _post_json in parity/py_gen_entry.py; the prompt,
  JSON extraction, normalization and auto-fallback are untouched code.
  The Rust side redirects via EYEWRIGHT_OLLAMA_URL (D7).

## Slice plan

1. DONE  config + guards + HTTP eyes + decide_gate + ask (typed path)
2. DONE  generative engine + engine=auto fallback
3. DONE  serve: /health, /health/deep, /v1/gate, /v1/ask, token,
         body cap (TLS deferred to 3b)
4.       mcp stdio
5.       supervisor/tray - not planned; platform UI with no cheap oracle

## Deviations

D1  mcp and the supervisor are absent. TLS (--cert/--key) is deferred:
    the Rust server refuses those flags with exit 2 rather than silently
    serving plain HTTP.
D2  Uncaught errors: Python prints a traceback, Rust prints
    "eyewright: <msg>". Exit code 1 in both.
D3  CLOSED in slice 2: engine=auto now falls back to the generative engine.
D4  JSON formatting and key order differ. The object is the contract; the
    harness canonicalizes before comparing.
D5  CLOSED in slice 2: serde_json preserve_order matches Python insertion
    order, so argmax tie-breaks now agree.
D6  round-half ties: Python uses banker's rounding, Rust multiplies and
    rounds. Only reachable at exact .00005 boundaries.
D7  The generative transport reads EYEWRIGHT_OLLAMA_URL (default
    http://localhost:11434) so the harness can redirect it to the stub.
    Python hardcodes the URL. Payload construction and everything above the
    transport are unchanged and compared.
A1  --version was added (Python has no such flag). Harmless addition.

## Evidence

- PARITY 22/22 against goldens captured from the untouched Python CLI.
- Python determinism: 22/22 across two consecutive runs.
- Mutation-tested three times: flipping the consensus direction check to
  accept any direction turns the CLI harness red; changing the normalization
  flag for "no" turns gen-prose red; making the server ignore the token turns
  two serve cases red (9/11).
- serve.py starts both HTTP servers against their own stub, replays the same
  11 requests, and compares status, canonical body and Content-Type. It
  covers health, deep health, both auth paths, gate, ask, invalid JSON, the
  body cap and 404s.
- The first harness draft was vacuous: the stub bound an ephemeral port but
  the config pointed at a pre-picked one, so every request failed and the
  goldens recorded the failure path. The mutation test caught it. Fixed:
  the stub's actual port is used.
