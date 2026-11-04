# Rust core - parked (2026-11-04)

Status: **kept, tabled, not maintained.** Python is the only implementation.
Do not reopen this work until one of the conditions in [Reopen criteria](#reopen-criteria)
is actually true. Until then, treat `rust/` as a snapshot, not a port that
tracks `main`.

## What is here

`rust/` is a Rust clone of the decision core only - config + guards, HTTP eyes,
`decide_gate`, `ask` (typed / generative / auto), `serve`, MCP stdio. Roughly
1350 LOC. `PORT.md` is the port card; `parity/` is its oracle.

Not ported: supervisor and tray (no cheap oracle), TLS (`serve` refuses
`--cert`/`--key` with exit 2 rather than silently serving plain HTTP).

## Why it is parked

Side by side it does the same thing as Python - same prompts, same thresholds,
same math, byte-identical output on 34/34 parity cases. It never produces a
better verdict, so it improves nothing until the delivery story changes.

Measured 2026-11-04 (process startup, median of 7):

| | Python | Rust |
| --- | --- | --- |
| CLI startup | 122 ms | 4 ms |
| decision output | golden source | identical, 34/34 |

A real gate spends its time in the HTTP calls to the decision models
(hundreds of ms to seconds), so that ~120 ms is invisible. As a resident
`serve` process the difference is zero.

What the port did deliver: while being written it exposed #25 (deep-health path
match) and #26 (token on the command line) on the Python side. That value is
already banked; keeping the code does not re-earn it.

Cost of keeping it live: every Python behaviour change needs a Rust mirror or
the port silently lies. That drift already started (#8 MCP `levels`, crate
pinned at 0.4.0) and is why this file exists.

## Reopen criteria

Reopen only if at least one becomes true:

1. **Distribution** - eyewright must run on machines where installing
   Python/uv is a real cost, and a single binary is the product requirement.
2. **Tight-loop invocation** - the core is called per keystroke / per prompt by
   an external harness where ~120 ms per call is too much.
3. **Non-Python host** - the core must be embedded in a native application.

"It would be faster" is not one of these. Neither is "Rust is nicer".

## If you reopen it

1. Rebase `rust/` on the current `main` and diff it against the Python core
   file by file. Assume drift; do not trust `PORT.md`'s parity numbers.
2. Fix the two known gaps first:
   - MCP `eyewright_ask` hardcodes `levels: None` and its schema does not
     expose `levels` (Python has it since #8).
   - `NO_SIGNAL` still lists `error-primary`, dead since #27 (the path returns
     `Err` first). Harmless, but it is a stale mirror.
3. Re-capture the goldens, then re-run the oracle. `parity/serve.py` goldens
   carry `"version":"0.0.0.dev0"` from a dev install, so 5 of 16 cases "fail"
   on the version string alone; behaviour matches 16/16. Regenerate or
   normalise the version field before trusting that harness.
4. Add `parity/run.py --side rs` to CI. It is not there - CI only runs the two
   routing unit tests in `rust/src/server.rs`.
5. Bump `rust/Cargo.toml` version in step with the project version.

## Verifying the snapshot as it stands

    cargo test --manifest-path rust/Cargo.toml          # 2/2
    cargo build --release --manifest-path rust/Cargo.toml
    python parity/run.py --side rs                      # 34/34
    python parity/serve.py                              # 11/16, version field only
    python parity/mcp_parity.py                         # needs the mcp extra installed

`parity/golden/` is captured from Python and is still useful on its own as a
Python regression net, independent of whether the Rust side ever ships.
