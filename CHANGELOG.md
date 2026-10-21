# Changelog

Notable changes to eyewright. Versions are the distribution version.

## Unreleased

- Project env: new default `runtime` dependency group (`mcp`, `pystray`, `pillow`).
  `uv sync` is exact and prunes extras, so the venv kept losing the MCP package
  that harnesses launch `.venv/Scripts/eyewright.exe` against — every sync now
  installs it. Published installs still opt in (`eyewright[mcp]`, `eyewright[tray]`).
- `eyewright mcp`: one-line, actionable message instead of a traceback when the
  `mcp` package is missing.
- `tests/mcp_smoke.py`: exercises the same bare `uv run eyewright mcp` launch path
  the harnesses use, and asserts the tool set.
- `supervisor/install.ps1`: the non-tray autostart branch wrote to an undefined
  `$launcher` (never installed).

## 0.4.0 — 2026-10-12

- `__version__` single-sourced from package metadata (no more drift).
- `serve`: bearer token (constant-time), 1 MB body cap, generic errors, refuses
  off-loopback without a token, optional TLS (`--cert`/`--key`), and drains the
  request body before a `401`/`413` so the client can read the response.
- `ask --engine auto`: falls back to the generative engine on any no-signal typed
  decision *or* an error, not only `decision:none`.
- **`attempts`** is the config key for total attempts (default 1); `retries` is a
  legacy alias meaning attempts *beyond* the first (behavior change).
- Configurable per-eye `timeout_s` (default 120 s), replacing the hardcoded values.
- generative engine: robust first-object JSON extraction; canonical `yes`/`no`
  normalization (handles `true`/`false`, `1`/`0`).
- tests: `test_generative`, `test_auto_fallback`, `test_version`.

## 0.3.1

- Scope the source distribution (exclude `bench/`): ~1.2 MB → 66 KB.

## 0.3.0

- Generative engine behind `ask` (`--engine generative` / `auto`), uncalibrated.
- Resilience: gate `retries` + `on_primary_unavailable`, `GET /health/deep`, and
  the service supervisor (`supervisor/`).

## 0.2.0

- One-call `ask`, HTTP `/v1/ask`, and the MCP adapter
  (`eyewright_gate` / `eyewright_ask`).

## 0.1.0

- Initial three-eye gate policy + validation bench (shipped as "oracle"; renamed
  to `eyewright` on 2026-10-09 — see `PROVENANCE.md`).
